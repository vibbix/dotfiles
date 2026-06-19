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
- a **pre-commit** hook rebuilds/verifies it at commit time;
- `00-index.md` is **locked** (deny rule + PreToolUse guard) so only the script writes it;
- a `.docbuild.config.yaml` sets the docs root per repo.

The skill's templates live in `assets/` (relative to this file). Read
[references/usage.md](references/usage.md) for the ignore/include/config formats.

## Install procedure

Run these from the target repo. `$SKILL` = this skill's directory.

1. **Locate the repo and create dirs.**
   ```bash
   repo="$(git rev-parse --show-toplevel)"
   mkdir -p "$repo/.claude/hooks" "$repo/.claude/scripts"
   ```

2. **Make the script resolvable.** The hooks find the script via `run-doc-index.sh`
   (dotfiles → vendored copy → remote URL). Always vendor a copy so the repo works on
   machines without dotfiles and offline:
   ```bash
   src="$HOME/git/dotfiles/scripts/python/scripts/update_doc_index.py"
   [ -f "$src" ] && cp "$src" "$repo/.claude/scripts/update_doc_index.py"
   ```
   If dotfiles isn't present, the URL fallback in `run-doc-index.sh` works
   (`vibbix/dotfiles` is public), but vendoring still keeps the repo self-contained
   and offline-capable, so prefer it.

3. **Install the hook scripts.**
   ```bash
   cp "$SKILL/assets/run-doc-index.sh"   "$repo/.claude/hooks/"
   cp "$SKILL/assets/block-index-write.sh" "$repo/.claude/hooks/"
   chmod +x "$repo/.claude/hooks/"*.sh
   ```

4. **Merge `assets/settings.snippet.json` into `$repo/.claude/settings.json`.**
   Create the file if absent. If it exists, merge: append the `permissions.deny`
   entries and the `hooks.PreToolUse` / `hooks.PostToolUse` matchers (don't clobber
   existing keys). The snippet adds the 00-index deny rules and both hooks.

5. **Create `.docbuild.config.yaml`** at the repo root from
   `assets/docbuild.config.example.yaml`. Set `root` to the repo's docs directory
   (default `docs`; ask the user if it's ambiguous).

6. **Seed the ignore/include files** at the docs root if missing:
   ```bash
   cp -n "$SKILL/assets/indexbuilderignore.example"        "<docs-root>/.indexbuilderignore"
   cp -n "$SKILL/assets/indexbuilderinclude.example.yaml"  "<docs-root>/.indexbuilderinclude.yaml"
   ```
   These are optional — submodules and `.gitignore` are excluded without them.

7. **Wire up pre-commit.** Merge `assets/pre-commit-config.snippet.yaml` into
   `$repo/.pre-commit-config.yaml` (create with a top-level `repos:` list if absent).

8. **Document it in the repo's agent-instructions file.** Append the
   `assets/claude-md.snippet.md` block (delimited by `<!-- doc-index:guide:start -->` /
   `<!-- doc-index:guide:end -->`) to the repo's agent file — `CLAUDE.md`, or the
   repo's existing `AGENT.md`/`AGENTS.md` if that's what it uses. On re-install, replace
   the content between the markers rather than appending a duplicate.

9. **Generate the index once and verify:**
   ```bash
   "$repo/.claude/hooks/run-doc-index.sh"
   "$repo/.claude/hooks/run-doc-index.sh" --check   # should exit 0
   ```

10. **Tell the user** to run `pre-commit install` (installing the `pre-commit` tool
    first if needed) so the commit-time hook is active.

## Using the ignore & include files

Full reference: [references/usage.md](references/usage.md). In short:

- **Authored docs** carry frontmatter (`title`, `summary`, `read_if`, `created`).
- **Submodules and `.gitignore`** are excluded automatically — never list them again.
- **`.indexbuilderignore`** (gitignore syntax) adds *extra* exclusions at the docs root.
- **`.indexbuilderinclude.yaml`** registers docs that **cannot carry frontmatter**
  (vendored / generated / read-only). When you find such a doc worth surfacing in the
  index, add a `{path, title, summary, read_if, created?}` entry here instead of
  editing the doc. Authored docs you control should get frontmatter instead.

## Rules

- **Never** hand-edit any `00-index.md`. It is regenerated; edits are blocked by the
  deny rule and PreToolUse guard. Change the source `.md` frontmatter or the include
  file, then let the script rebuild it.
