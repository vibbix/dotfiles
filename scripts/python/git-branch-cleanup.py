#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gitpython~=3.1.45",
#   "PyGithub~=2.8.1",
#   "tqdm~=4.67.1",
#   "requests-cache~=1.2.1",
#   "colorlog~=6.10.1",
# ]
# ///
"""
List merged PRs for the current repository using PyGithub.

Usage:
  - Ensure `PyGithub` is installed: `pip install PyGithub`
  - Provide a GitHub token in the env var `GITHUB_TOKEN` (recommended):
      export GITHUB_TOKEN=ghp_...
  - Run:
      ./scripts/python/list_merged_prs.py

The script detects the repo owner/name from `git remote get-url origin`.
It prints each merged PR number, title, branch, and commit SHA.
"""
import logging
import os
import re
import subprocess
import sys
import argparse


from typing import Optional
from github import Github
import github
import colorlog

from requests_cache import DO_NOT_CACHE, install_cache
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map


logger = logging.getLogger("git_branch_cleanup")

def get_origin_url(cwd: str) -> Optional[str]:
    try:
        out = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], stderr=subprocess.DEVNULL, cwd=cwd)
        return out.decode().strip()
    except subprocess.CalledProcessError:
        return None


def parse_owner_repo(url: str) -> Optional[str]:
    # support formats like:
    # git@github.com:owner/repo.git
    # https://github.com/owner/repo.git
    # https://github.com/owner/repo
    url = url.strip()
    m = re.match(r"git@[^:]+:([^/]+)/([^.]+)(\.git)?$", url)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    m = re.match(r"https?://[^/]+/([^/]+)/([^.]+)(\.git)?$", url)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return None

def __get_github() -> Github:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        # Try to use the `gh` CLI token if the user is authenticated there.
        try:
            # `gh auth status -t` exits 0 when authenticated with a token
            subprocess.check_call(["gh", "auth", "status", "-t"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                out = subprocess.check_output(["gh", "auth", "token"], stderr=subprocess.DEVNULL)
                gh_cli_token = out.decode().strip()
                if gh_cli_token:
                    token = gh_cli_token
                    logger.debug("Using GitHub token from `gh auth token`.")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # could not get token from gh; fall through to unauthenticated
                pass
        except (subprocess.CalledProcessError, FileNotFoundError):
            # gh not installed or not authenticated; fall through
            pass

    if token:
        gh = Github(auth=github.Auth.Token(token))
    else:
        logger.warning("Warning: no GITHUB_TOKEN found — unauthenticated requests are rate-limited.")
        gh = Github()
    return gh


def main(directory: str):
    url = get_origin_url(directory)
    if not url:
        logger.fatal("Could not find git remote origin URL. Run this inside a git repo with origin remote.")
        sys.exit(1)

    owner_repo = parse_owner_repo(url)
    if not owner_repo:
        logger.fatal(f"Unsupported remote URL format: {url}")
        sys.exit(1)

    gh = __get_github()

    try:
        repo = gh.get_repo(owner_repo)
    except Exception as e:
        logger.fatal(f"Failed to access repository {owner_repo}: {e}")
        sys.exit(1)

    logger.info(f"Repository: {owner_repo}")

    # Fetch closed PRs and filter for merged
    logger.info("Fetching closed pull requests and filtering merged ones...")
    merged = []
    try:
        pulls = repo.get_pulls(state='closed', sort='updated', direction='desc')
        for pr in tqdm(pulls, total=pulls.totalCount, desc="Processing PRs"):
            try:
                if pr.merged:
                    merged.append(pr)
            except Exception:
                # fallback: check merge_commit_sha
                if getattr(pr, 'merge_commit_sha', None):
                    merged.append(pr)
    except Exception as e:
        logger.fatal(f"Error fetching PRs: {e}")
        sys.exit(1)

    if not merged:
        logger.info("No merged PRs found.")
        return

    logger.info(f"Found {len(merged)} merged PR(s):")
    for pr in merged:
        # head.ref is the branch name; head.sha is the last commit SHA on the head
        head_ref = getattr(pr.head, 'ref', None)
        head_sha = getattr(pr.head, 'sha', None)
        merged_at = getattr(pr, 'merged_at', None)
        logger.info(f"- PR #{pr.number}: {pr.title}\n    branch: {head_ref}\n    commit: {head_sha}\n    merged_at: {merged_at}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Clean up local git branches for merged PRs.")
    parser.add_argument(
        "path",
        nargs="?",
        default="/Users/vibbix/git/dtmx/infrastructure",#$os.getcwd(),
        help="Path to the workspace (default: current directory)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Forces update check even if not needed",
    )
    # parser.add_argument(
    #     "--everyone",
    #     action="store_true",
    #     help="Get for everyone",
    # )
    parser.add_argument(
        "--nocache",
        action="store_true",
        help="Disable HTTP caching for GitHub API requests",
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    if not args.nocache:
        logger.info("Enabling HTTP caching for GitHub API requests...")
        install_cache(
            cache_control=True,
            # urls_expire_after={
            #     '*.github.com': 360,  # Placeholder expiration; should be overridden by Cache-Control
            #     '*': DO_NOT_CACHE,    # Don't cache anything other than GitHub requests
            # },
        )
    # parser.add_argument("--color_main", help="Node name to trace and color path to (default: main)", default="main")
    args = parser.parse_args()
    main(args.path)