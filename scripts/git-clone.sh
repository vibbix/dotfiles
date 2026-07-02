#!/usr/bin/env sh
#
# Clone a repo into ~/git/<owner>/<repo> from any of these forms:
#   git@github.com:owner/repo.git   https://github.com/owner/repo[.git]
#   github.com/owner/repo           owner/repo
#
# Prints the destination path on stdout so you can:  cd "$(git-clone.sh <uri>)"

uri="$1"
if [ -z "$uri" ]; then
  echo "usage: git-clone.sh <uri|owner/repo>" >&2
  exit 1
fi

# Strip trailing .git / slash, then peel the last two path segments.
clean="${uri%.git}"
clean="${clean%/}"
case "$clean" in
  */*) ;;   # need at least one slash to hold owner/repo
  *) echo "git-clone.sh: could not parse owner/repo from '$uri'" >&2; exit 1 ;;
esac
repo="${clean##*/}"          # last segment
rest="${clean%/*}"           # everything before it
org="${rest##*[/:@]}"        # segment after the last / : or @

if [ -z "$org" ] || [ -z "$repo" ]; then
  echo "git-clone.sh: could not parse owner/repo from '$uri'" >&2
  exit 1
fi

# Full ssh/https URLs clone as-given; bare forms default to ssh github.
case "$uri" in
  git@*|*://*) clone_url="$uri" ;;
  *)           clone_url="git@github.com:${org}/${repo}.git" ;;
esac

dest="$HOME/git/${org}/${repo}"
if [ -d "$dest" ]; then
  echo "git-clone.sh: '$dest' already exists" >&2
  exit 1
fi

git clone "$clone_url" "$dest" >&2 || exit 1
echo "$dest"
