---
name: install-doc-builder
version: 0.1.0
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

## Re-running / updating an existing install

This skill is safe to re-run; a second invocation in an already-set-up repo is an
**in-place update**, not a fresh install. It refreshes the vendored script and hook,
de-dupes the settings and pre-commit merges, replaces the guide block, and reports the
version delta. The preflight below detects a prior install and reads its stamped version;
each step notes how it stays idempotent, so a re-run never duplicates settings, hooks, or
the guide block.

## Install procedure

Run these from the target repo. `$SKILL` is this skill's directory.

0. **Preflight — detect a prior install and read versions.**
   ```bash
   repo="$(git rev-parse --show-toplevel)"
   current="$(sed -n 's/^version: *//p' "$SKILL/SKILL.md" | head -1)"
   agent=""
   for f in "$repo/CLAUDE.md" "$repo/AGENT.md" "$repo/AGENTS.md"; do
     [ -f "$f" ] && grep -q '<!-- doc-index:guide:start' "$f" && { agent="$f"; break; }
   done
   installed=""
   [ -n "$agent" ] && installed="$(sed -n 's/.*doc-index:guide:start v=\([^ ]*\).*/\1/p' "$agent" | head -1)"
   echo "doc-index builder: installed=${installed:-none} -> current=$current"
   ```
   A non-empty `installed` means this is an **update**: proceed through the steps (they
   are idempotent) and report `installed -> current` at the end. An empty `installed` —
   no guide block, or an old block with no `v=` — is a fresh install or a pre-version
   install being upgraded.

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
   but vendor anyway so the repo is self-contained. On a re-run this `cp` overwrites the
   vendored copy with the skill's current version — always refresh it.

3. **Install the hook script.**
   ```bash
   cp "$SKILL/assets/run-doc-index.sh" "$repo/.claude/hooks/"
   chmod +x "$repo/.claude/hooks/run-doc-index.sh"
   ```
   This `cp` likewise overwrites on re-run, so the hook always tracks the skill's copy.

4. **Merge `assets/settings.snippet.json` into `$repo/.claude/settings.json`.**
   Create the file if it's absent. If it exists, add the `permissions.deny` entries and
   the `hooks.PostToolUse` matcher without clobbering existing keys. The deny rules are
   the only thing locking `00-index.md`: native settings, no guard script.
   **Idempotent:** if a deny entry or the `run-doc-index.sh` `PostToolUse` matcher is
   already present, leave it — never append a duplicate. Only rewrite a snippet in place
   if its content differs from the current template.

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
   **Idempotent:** if a `repo: local` entry with a hook `id: doc-index` already exists,
   update that entry in place — don't add a second `doc-index` hook.

8. **Document it in the repo's agent file.** Add the `assets/claude-md.snippet.md` block
   (delimited by `<!-- doc-index:guide:start v=<version> -->` and
   `<!-- doc-index:guide:end -->`) to the repo's agent file: `CLAUDE.md`, or the repo's
   existing `AGENT.md`/`AGENTS.md`. Stamp the skill's current `version:` into the start
   marker's `v=`. Locate any existing block by the marker **prefix**
   (`<!-- doc-index:guide:start`, ignoring the version suffix) and replace everything
   through the end marker — including the stamped version — so a re-run upgrades the block
   without appending a copy. Append only when no prior block exists.

9. **Generate the index once and verify:**
   ```bash
   "$repo/.claude/hooks/run-doc-index.sh"
   "$repo/.claude/hooks/run-doc-index.sh" --check   # should exit 0
   ```

10. **Tell the user** to run `pre-commit install` (installing the `pre-commit` tool first
    if needed) so the commit-time hook is active. **On a re-run**, close by summarizing
    what was refreshed (script, hook, settings, pre-commit, guide block) and report the
    `installed -> current` version delta from the preflight.

## Using the ignore and include files

Full reference: [references/usage.md](references/usage.md).

- **Authored docs** carry frontmatter (`title`, `summary`, `read_if`, `created`).
- **Submodules and `.gitignore`** are excluded automatically. Don't list them again.
- **`.indexbuilderignore`** (gitignore syntax) adds extra exclusions at the docs root.
- **`.indexbuilderinclude.yaml`** registers docs that **cannot carry frontmatter**
  (vendored, generated, or read-only). When you find such a doc worth surfacing, add a
  `{path, title, summary, read_if, created?}` entry here instead of editing the doc. Docs
  you control should get frontmatter instead.

## Versioning (maintainers)

This skill carries a SemVer `version:` in its frontmatter (same convention as the
`humanizer` skill).

- **patch** (`0.1.0 -> 0.1.1`): doc wording or template tweaks with no behavior change.
- **minor** (`0.1.0 -> 0.2.0`): new install behavior, added files, or new options.
- **major** (`0.1.0 -> 1.0.0`): breaking changes to the install layout or interface.

**Any change to this skill MUST bump `version:`.** Step 8 stamps the same version into
each install's guide-block start marker, so the preflight can detect an upgrade and report
the `installed -> current` delta on re-run.

## Rules

- **Never** hand-edit any `00-index.md`. It is regenerated, and edits are blocked by the
  `permissions.deny` rule. Change the source `.md` frontmatter or the include file, then
  let the script rebuild it.
