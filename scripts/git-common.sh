#!/bin/env bash

# TODO: verify "common.sh" is imported

function gettrunkname() {
  git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'
}

# Rebase branch on trunk, while moving trunk to the latest from origin
function rebasebranch() {
  local no_push=false
  if [[ "$1" == "--no-push" || "$1" == "-n" ]]; then
    no_push=true
  fi

  TRUNKNAME=$(gettrunkname)
  git fetch origin "$TRUNKNAME:$TRUNKNAME" && git rebase origin/"$TRUNKNAME"

  if ! $no_push; then
    git push --force-with-lease
  fi
}

alias switchmain="git checkout -B main origin/main"

#git switch main/master
# shellcheck disable=SC2120
function gsm() {
  local branch
  branch=${1:-$(gettrunkname)}
  git switch "$branch"
}

# Git switch main/master and pull
function gsmp() {
  gsm && git pull
}

# Check if a branch has an upstream remote branch
function has_upstream_remote() {
  local branch="$1"
  git rev-parse --verify --quiet "$branch@{upstream}" &>/dev/null
}

# Check if a branch has been merged into the current branch
function is_merged() {
  local branch="$1"
  git branch --merged | grep -qE "^\s*${branch}$"
}

# Check if a branch either has an upstream remote or has been merged
function has_no_upstream_or_merged() {
  local branch="$1"
  if ! has_upstream_remote "$branch" || is_merged "$branch"; then
    return 0
  else
    return 1
  fi
}

function branch_is_merged() {
  local branch="$1"

  # Check if the branch is merged locally
  if is_merged "$branch"; then
    return 0
  fi

  # Check if the branch is merged on GitHub using the GitHub CLI
  local pr_state
  pr_state=$(gh pr view "$branch" --json state --jq '.state' 2>/dev/null)

  if [[ "$pr_state" == "MERGED" ]]; then
    return 0
  fi

  # If neither check passes, the branch is not merged
  return 1
}