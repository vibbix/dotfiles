#!/usr/bin/env bash
# Symlink every skill under this directory into ~/.claude/skills/ so it can be
# invoked as /<skill-name> from any repo. Idempotent: re-running only refreshes
# the links. Each skill is a subdir containing a SKILL.md.
set -euo pipefail

skills_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="${CLAUDE_HOME:-$HOME/.claude}/skills"
mkdir -p "$dest"

linked=0
for skill in "$skills_dir"/*/; do
  [ -f "${skill}SKILL.md" ] || continue   # skip non-skill dirs (no SKILL.md)
  name="$(basename "$skill")"
  target="$dest/$name"
  src="${skill%/}"

  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "skip $name: $target exists and is not a symlink" >&2
    continue
  fi

  ln -sfn "$src" "$target"
  echo "linked $name -> $src"
  linked=$((linked + 1))
done

echo "done: $linked skill(s) linked into $dest"
