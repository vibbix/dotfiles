#!/usr/bin/env bash
# Locate update_doc_index.py and run it for the current repo.
# Used as both the Claude PostToolUse hook and the pre-commit entry point.
#
# Resolution order (first hit wins):
#   1. $DOC_INDEX_SCRIPT                                  (explicit override)
#   2. $HOME/git/dotfiles/scripts/python/scripts/...      (source of truth)
#   3. ./.claude/scripts/update_doc_index.py              (vendored copy)
#   4. $DOC_INDEX_URL / pinned raw URL via `uv run <url>` (needs network + a
#      reachable URL; the dotfiles remote is private, so this may 404)
#
# Flags:
#   --check   forward to the script (pre-commit: fail if the index is stale)
#   --hook    read the PostToolUse JSON on stdin and only run when an `.md`
#             file was written; non-md edits are a no-op
set -euo pipefail

DOTFILES_DEFAULT="$HOME/git/dotfiles/scripts/python/scripts/update_doc_index.py"
URL_DEFAULT="https://raw.githubusercontent.com/vibbix/dotfiles/master/scripts/python/scripts/update_doc_index.py"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

hook_mode=0
forward=()
for arg in "$@"; do
  case "$arg" in
    --hook) hook_mode=1 ;;
    *) forward+=("$arg") ;;
  esac
done

if [[ "$hook_mode" -eq 1 ]]; then
  payload="$(cat || true)"
  file_path="$(printf '%s' "$payload" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//; s/"$//')"
  case "$file_path" in
    *.md) ;;            # markdown was touched -> rebuild
    *) exit 0 ;;        # anything else -> nothing to do
  esac
fi

if [[ -n "${DOC_INDEX_SCRIPT:-}" && -f "$DOC_INDEX_SCRIPT" ]]; then
  exec uv run "$DOC_INDEX_SCRIPT" "${forward[@]}"
elif [[ -f "$DOTFILES_DEFAULT" ]]; then
  exec uv run "$DOTFILES_DEFAULT" "${forward[@]}"
elif [[ -f "$repo_root/.claude/scripts/update_doc_index.py" ]]; then
  exec uv run "$repo_root/.claude/scripts/update_doc_index.py" "${forward[@]}"
else
  exec uv run "${DOC_INDEX_URL:-$URL_DEFAULT}" "${forward[@]}"
fi
