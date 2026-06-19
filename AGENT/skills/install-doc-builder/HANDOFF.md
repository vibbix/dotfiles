# Handoff: install the doc-index builder in another repo

This skill lives inside the dotfiles repo, so it isn't globally registered. To run
it in a different repository, open a Claude Code session in that repo and paste the
prompt below. It points Claude at this skill's `SKILL.md` by path and tells it to
execute the install procedure against the current working directory.

## Prerequisites

- `dotfiles` checked out at `~/git/dotfiles` (otherwise adjust the path in the prompt,
  or first `git clone https://github.com/vibbix/dotfiles ~/git/dotfiles`).
- `uv` available on PATH.
- For the URL fallback / fresh installs to pick up the `.docbuild.config`,
  `.gitignore`, and submodule features, those changes must be pushed to `master`.

## Prompt

```
Set up the markdown doc-index builder in this repository.

Read the skill instructions at
  ~/git/dotfiles/AGENT/skills/install-doc-builder/SKILL.md
(its templates are in that skill's assets/ and references/ folders) and follow the
install procedure exactly, applying it to THIS repo (the current working directory).

Specifics for this run:
- Vendor a copy of update_doc_index.py into .claude/scripts/ so the repo is
  self-contained; the resolver also falls back to ~/git/dotfiles and the public
  raw URL (github.com/vibbix/dotfiles).
- Install both hooks: the Claude PostToolUse + PreToolUse hooks (via
  .claude/settings.json) and the pre-commit-framework local hook.
- Add the 00-index.md deny rule to .claude/settings.json.
- Create .docbuild.config.yaml. Ask me which folder is the docs root if it's not
  obvious (default: docs/).
- Seed .indexbuilderignore / .indexbuilderinclude.yaml at the docs root.
- Append the doc-index guide block to this repo's agent file (CLAUDE.md, or the
  existing AGENT.md/AGENTS.md), using the doc-index:guide markers idempotently.
- Generate the index once and verify `.claude/hooks/run-doc-index.sh --check`
  exits 0.

When done, summarize what was created and remind me to run `pre-commit install`.
Do not hand-edit any 00-index.md — it's generated only by the script.
```
