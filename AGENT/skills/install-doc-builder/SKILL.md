---
name: install-doc-builder
description: >
  Install and wire up the markdown doc-index builder (update_doc_index.py) into a
  repository. Use when the user wants to set up, install, or configure the doc index,
  the 00-index.md generator, the "doc builder", auto-generated documentation indexes,
  or hooks that keep a docs index up to date on edit and at commit time.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# install-doc-builder

Sets up `update_doc_index.py` in the **current repo** so a `00-index.md` table is
generated from the docs' frontmatter and kept current automatically:

- a **PostToolUse** hook rebuilds the index whenever Claude writes a `.md` file;
- a **pre-commit** hook rebuilds and verifies it at commit time;
- `00-index.md` is locked by a native `permissions.deny` rule, so only the script writes it.

Keep the install minimal. Only create files the repo actually needs:

- the docs root defaults to **`docs/claude`**, so write `.docbuild.config.yaml` only when
  the root differs;
- `.indexbuilderignore` and `.indexbuilderinclude.yaml` are optional. Create them only when
  they hold real content. Don't drop empty templates.

The skill's templates live in `assets/` (relative to this file). See
[references/usage.md](references/usage.md) for the ignore, include, and config formats.

## Install procedure

Run these from the target repo. `$SKILL` is this skill's directory.

1. **Locate the repo and create dirs.**
   ```bash
   repo="$(git rev-parse --show-toplevel)"
   mkdir -p "$repo/.claude/hooks" "$repo/.claude/scripts"
   ```

2. **Make the script resolvable.** `run-doc-index.sh` looks for the script in dotfiles
   first, then a vendored copy, then the public URL. Always vendor a copy so the repo
   works offline and on machines without dotfiles:
   ```bash
   src="$HOME/git/dotfiles/scripts/python/scripts/update_doc_index.py"
   [ -f "$src" ] && cp "$src" "$repo/.claude/scripts/update_doc_index.py"
   ```
   If dotfiles isn't present the URL fallback still works (`vibbix/dotfiles` is public),
   but vendor anyway so the repo is self-contained.

3. **Install the hook script.**
   ```bash
   cp "$SKILL/assets/run-doc-index.sh" "$repo/.claude/hooks/"
   chmod +x "$repo/.claude/hooks/run-doc-index.sh"
   ```

4. **Merge `assets/settings.snippet.json` into `$repo/.claude/settings.json`.**
   Create the file if it's absent. If it exists, append the `permissions.deny` entries
   and the `hooks.PostToolUse` matcher without clobbering existing keys. The deny rules
   are the only thing locking `00-index.md`: native settings, no guard script.

5. **Config, only if the docs root is non-default.** The script defaults to `docs/claude`
   under the git root. If the repo's docs live elsewhere, create `.docbuild.config.yaml`
   from `assets/docbuild.config.example.yaml` and set `root`. If the root is `docs/claude`,
   don't create a config file. Ask the user if the root is ambiguous.

6. **Ignore and include files, only if non-empty.** Create
   `<docs-root>/.indexbuilderignore` only when you have real exclusion patterns, and
   `<docs-root>/.indexbuilderinclude.yaml` only when there's a vendored doc to register
   (see `assets/*.example*` for the formats). Submodules and `.gitignore` are excluded
   without either file. Step 8's agent-file note tells future sessions how to add them.

7. **Wire up pre-commit.** Merge `assets/pre-commit-config.snippet.yaml` into
   `$repo/.pre-commit-config.yaml` (create it with a top-level `repos:` list if absent).

8. **Document it in the repo's agent file.** Append the `assets/claude-md.snippet.md`
   block (delimited by `<!-- doc-index:guide:start -->` and `<!-- doc-index:guide:end -->`)
   to the repo's agent file: `CLAUDE.md`, or the repo's existing `AGENT.md`/`AGENTS.md`.
   On re-install, replace the content between the markers instead of appending a copy.

9. **Generate the index once and verify:**
   ```bash
   "$repo/.claude/hooks/run-doc-index.sh"
   "$repo/.claude/hooks/run-doc-index.sh" --check   # should exit 0
   ```

10. **Tell the user** to run `pre-commit install` (installing the `pre-commit` tool first
    if needed) so the commit-time hook is active.

## Using the ignore and include files

Full reference: [references/usage.md](references/usage.md).

- **Authored docs** carry frontmatter (`title`, `summary`, `read_if`, `created`).
- **Submodules and `.gitignore`** are excluded automatically. Don't list them again.
- **`.indexbuilderignore`** (gitignore syntax) adds extra exclusions at the docs root.
- **`.indexbuilderinclude.yaml`** registers docs that **cannot carry frontmatter**
  (vendored, generated, or read-only). When you find such a doc worth surfacing, add a
  `{path, title, summary, read_if, created?}` entry here instead of editing the doc. Docs
  you control should get frontmatter instead.

## Rules

- **Never** hand-edit any `00-index.md`. It is regenerated, and edits are blocked by the
  `permissions.deny` rule. Change the source `.md` frontmatter or the include file, then
  let the script rebuild it.
