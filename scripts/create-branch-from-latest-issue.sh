#!/usr/bin/env bash
# TODO:
# - shellcheck stuff
# - usage guide
# - replace perl
# - consider replacing jq?
# - make it VCS/Issue tracker independent?
# - Add better mapping support for feature types
# - Add better ticket formatting support
# - add usage guide
# - add a "re-open" flag
# - For Jira CLI, add support for finding exisiting branch names, and switching to them?
#  - i.e. support github CLI, gitlab CLI, linear.app?
# - maybe rewrite this in like Python or GoLang
# - write some test
# - add a check that makes sure that ticket doesn't have a local branch already
# - Add a JQL override
# - Add options to stash/view/stash-and-restore changes if uncommited changes are on branch
# - silence Git pull output
# - add color output to some parts
# - Paste ticket name and summary into clipboard (for ease of use)
# - handle remote branches in _does_branch_exist
# Done:
# - replaced FZF with jira-cli native selection
# - Have dialog for uncommited changes
# - Add colors
# - Added colon to santize branch name

# CHANGELOG
# [V0.1.8] - 11/20/2024
# - Updated query to sort tickets by status
# [v0.1.7] - 11/02/2024
# - Added Additonal colors to map
# - localized some functions
# - Improved handle changes in current branch 
# - changes check now occurs after ticket selection
# - Added check for existing branches

set -f
# split at newlines only
IFS='
'

RED=$(tput setaf 1)
GREEN="$(tput setaf 2)"
BLUE=$(tput setaf 4)
NC="$(tput sgr0)"
VERSION="v0.1.8"

# IFS=$'\n'
# requires see's if the utility is installed
requires() {
  if ! [ -x "$(command -v $1)" ]; then
    echo Error: "$1" is not installed. >&2
    if [ -n "$2" ]; then
      echo "Install with $2" >&2
      fi
    exit 1
  fi
}

# this is broken
to_lower() {
  awk '{print tolower($1)}'
}

# depreated
kebab_case() {
  # TODO: don't use perl?
  # source: https://stackoverflow.com/questions/69273290/converting-pascalcase-string-to-kebab-case-in-bash-without-sed
  perl -ne 'print lc s/[[:lower:]\d]\K[[:upper:]]/-$&/rg' <<< $(sed 's/ /-/g' <<< $1)
}

_trim()
{
    local trimmed="$1"
    # Strip leading spaces.
    while [[ $trimmed == ' '* ]]; do
       trimmed="${trimmed## }"
    done
    # Strip trailing spaces.
    while [[ $trimmed == *' ' ]]; do
        trimmed="${trimmed%% }"
    done
    echo "$trimmed"
}

sanitize_branch_name() 
{
  _trim "$1" | \
    tr -d '\r' | \
    tr -d '\n' | \
    tr -d '\t' | \
    sed -E -e 's/(^|[\/.])([\/.]|$)|:|#|\||^@$|@{|[\x00-\x20\x7f~^?*;"'"'"'`&|$()!\][\\]|\.lock(\/|$)|\S/-/g' -e 's/-{2,}/-/g'
}

# Convert the Task-type to a good prefix for the branch name
# TODO: have this be disaable with a param
get_type_name() {
  local ticket_type="$1"
  if [ $ticket_type == "Task" ]; then
    echo "feature"
  elif [ $ticket_type == "Sub-Task" ]; then
    echo "feature"
  elif [ $ticket_type == "Bug" ]; then
    echo "bugfix"
  else
    echo "$ticket_type" | tr "[:upper:]" "[:lower:]"
  fi
}

function _handle_changes_in_existing_branch() {
  local changes="$1"
  printf "${RED}%d${NC} Changes detected in current branch. What would you like to do?\n" "$changes"
  printf "${RED}1)$NC Do nothing and continue\n"
  printf "${RED}2)$NC Stash changes and continue\n"
  printf "${RED}3)$NC View changes and repeat dialog\n"
  printf "${RED}4)$NC Exit script\n"
  read -r -p "Please select an option: " choice
  case $choice in
    1)
      #continue
      ;;
    2)
      git stash
      ;;
    3)
      git diff
      _handle_changes_in_existing_branch "$changes"
      ;;
    4)
      exit 1
      ;;
    *)
      echo "Invalid choice"
      _handle_changes_in_existing_branch "$changes"
      ;;
  esac
}

function _does_branch_exist() {
  local ticket_id="$1"
  # TODO: verify that no preceding charcater breaks this (i.e. ENG vs RENG)
  local matched_tickets
  #TODO - handle remote branches
  if matched_tickets="$(git branch --list --remote | grep -E ".*${ticket_id}[^0-9]+.*")"; then
    #echo "Branch already exists for ticket: ${RED}${ticket_id}${NC}"
    local _count="$(wc -l <<< "$matched_tickets")"
    if [ $_count -lt 2 ]; then 
      printf "Found branch: ${RED}%s${NC}\n" "$matched_tickets"
      read -r -p "Would you like to swap?(${GREEN}Y{$NC}/${RED}N${NC}): " choice
      case $choice in
        y) 
          git switch "$matched_tickets"
          printf "Switched to branch: ${GREEN}%s${NC}\n" "$matched_tickets"
          exit 1
          ;;
        n)
          ;;
        *)
          printf "Invalid choice - ${RED}quitting${NC}\n"
          exit 1
          ;;
      esac
    else
      echo "$_count branches found for ticket: ${ticket_id}"
      echo "quitting"
      exit 1
    fi
  fi
}

# Unsure why macOS has such a prehistoric version of bash
# this is only needed because of the use of `read -i` not working on macOS
if (($BASH_VERSINFO < 4)); then 
  echo "Update your bash version to 4.x or higher" >&2
  exit 1
fi

requires git
requires jira "https://github.com/ankitpokhrel/jira-cli/wiki/Installation"
requires jq
requires perl

# default query - All open tickets either assigned to user, or created by user but unnasigned, sorted by latest
QUERY='((assignee = currentUser()) OR (creator = currentUser() && assignee = EMPTY)) AND (statusCategory != "Done") ORDER BY status DESC' #formerly = In Progress

if ! _GIT_STATUS=$(git status --porcelain); then
  echo "Not a git repository" >&2
  exit 1 
fi

LOCAL_TRUNK_NAME=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')

# perform a git pull?
# me=$(jira me)
# used if patch isn't installed
#SELECTED_ISSUE=$(ccjira issue list -a$me --paginate 10 -sopen -s"In Progress" --plain | fzf --header-lines=1)
# TODO: add custom JQL here? IO want to see all issues assigned to me, or created by me but unassigned
SELECTED_ISSUE=$(JIRA_FORCE_INTERACTIVE=1 jira issue list -q "$QUERY" --order-by created --json --select-on-enter)
if [ -z "$SELECTED_ISSUE" ]; then
  echo "No issue selected" >&2
  exit 1
fi
#check for changes
if [ -n "$_GIT_STATUS" ]; then
  _changes=$(_trim "$(wc -l <<< $_GIT_STATUS)")
  if [ $_changes -gt 0 ]; then
    _handle_changes_in_existing_branch "$_changes"
  fi
fi

#TODO: assert array is one
for s in $(echo "$SELECTED_ISSUE" | jq -r ".[0]|to_entries|map(\"\(.key)=\(.value|tostring)\").[]"); do
  # TODO: o i need export here?
  export _$s
done
_does_branch_exist "$_key"

default_branch_name=$(sanitize_branch_name $(printf "%s/%s-%s" $(get_type_name $_type) $_key $(kebab_case $_summary)))

echo "What would you like your branch name to be? (default: '$default_branch_name'):"
read -r -e -i "$default_branch_name" chosen_branch_name

#TODO: santize branch name
printf "Creating branch: ${GREEN}%s${NC}\n" "$chosen_branch_name"

_CURRENT_BRANCH=$(git branch --show-current)

if [ "$LOCAL_TRUNK_NAME" != "$_CURRENT_BRANCH" ]; then
  printf "Currently on ${RED}%s${NC}. Switching to ${GREEN}%s${NC}\n" "$_CURRENT_BRANCH" "$LOCAL_TRUNK_NAME"
  git switch "$LOCAL_TRUNK_NAME"
fi

#Prevent auto GC form running
#TODO: optional check for this
#TODO: have git GC write to stderr, or just dropped entirely
git -c gc.auto=0 pull
git switch -c "$chosen_branch_name"