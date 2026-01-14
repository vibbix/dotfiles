#!/usr/bin/env bash
SCRIPT_ROOT=$(dirname "$0")
#repos=("DTMX/primary-user-documentation" "DTMX/flow" "DTMX/primary-core" "DTMX/infrastructure")
GITHUB_TOKEN=$(gh auth token)
repos=($(gh repo list dtmx --json "nameWithOwner" | jq '.[].["nameWithOwner"]' | tr -d '"' | sort))
for repo in "${repos[@]}"; do
    # if repo starts with "marx" skip it
    if [[ $repo == DTMX/marx* ]]; then
        echo "Skipping repository: $repo"
        continue
    fi
    echo "==============================="
    echo "Cleaning repository: $repo"
    GITHUB_TOKEN=$GITHUB_TOKEN uv run "$SCRIPT_ROOT"/git-branch-cleanup.py -v --nocache --yes --min_age_days 30 "$repo"
done