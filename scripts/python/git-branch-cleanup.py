#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gitpython~=3.1.45",
#   "PyGithub~=2.8.1",
#   "tqdm~=4.67.1",
#   "requests-cache~=1.2.1",
#   "colorlog~=6.10.1",
#   "colorama~=0.4.6",
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
from datetime import datetime
import logging
import os
import re
import subprocess
import sys
import argparse
from typing import Any, List

from typing import Optional
from github import Github
import github
import git

import colorlog

from requests_cache import DO_NOT_CACHE, install_cacheß
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map

from colorama import Fore, Back, Style

from github.GithubObject import (
    Attribute,
    GraphQlObject,
    NotSet,
    as_rest_api_attributes,
    as_rest_api_attributes_list,
    is_undefined,
    CompletableGithubObject,
    NonCompletableGithubObject
)
from github.PaginatedList import PaginatedList

logger = logging.getLogger(__name__)

error_handler = colorlog.StreamHandler()
error_handler.setFormatter(colorlog.ColoredFormatter(
	'${log_color}[${levelname}] ${message}', style='$'))
error_handler.setLevel(level=logging.WARNING)

log_handler = colorlog.StreamHandler()
log_handler.setFormatter(colorlog.ColoredFormatter(
	'${message}', style='$'))# secondary_log_colors=secondary_log_colors
log_handler.setLevel(level=logging.DEBUG)
log_handler.addFilter(lambda record: record.levelno < logging.WARNING)

logger.addHandler(error_handler)
logger.addHandler(log_handler)
logger.propagate = False

class MergeCommitGQL(GraphQlObject, NonCompletableGithubObject):
    def _initAttributes(self) -> None:
        # super()._initAttributes()
        self._abbreviatedoid: Attribute[str] = NotSet
        self._id: Attribute[str] = NotSet
        self._oid: Attribute[str] = NotSet
        self._committeddate: Attribute[datetime] = NotSet
        self._authoreddate: Attribute[datetime] = NotSet

    @property
    def abbreviatedOid(self) -> str:
        return self._abbreviatedoid.value
    
    @property
    def id(self) -> str:
        return self._id.value
    @property
    def oid(self) -> str:
        return self._oid.value
    
    @property
    def committedDate(self) -> datetime:
        """
        The commit date gets changed every time the commit is being modified, 
        for example when rebasing the branch where the commit is in on another branch.
        
        :param self: Description
        :return: Description
        :rtype: datetime
        """
        return self._committeddate.value
    
    @property
    def authoredDate(self) -> datetime:
        """
        The author date notes when this commit was originally made (i.e. when you finished the git commit). 
        According to the docs of git commit, the author date could be overridden using the --date switch.

        :param self: Description
        :return: Description
        :rtype: datetime
        """
        return self._authoreddate.value
    
    def _useAttributes(self, attributes: dict[str, Any]) -> None:
        # super class is a REST API GithubObject, attributes are coming from GraphQL
        # super()._useAttributes(as_rest_api_attributes(attributes))
        if "abbreviatedOid" in attributes:
            self._abbreviatedoid = self._makeStringAttribute(attributes["abbreviatedOid"])
        if "id" in attributes:
            self._id = self._makeStringAttribute(attributes["id"])
        if "oid" in attributes:
            self._oid = self._makeStringAttribute(attributes["oid"])
        if "committedDate" in attributes:
            self._committeddate = self._makeDatetimeAttribute(attributes["committedDate"])
        if "authoredDate" in attributes:
            self._authoreddate = self._makeDatetimeAttribute(attributes["authoredDate"])

class CommitsHolderGQL(GraphQlObject, NonCompletableGithubObject):
    def _initAttributes(self) -> None:
        # super()._initAttributes()
        self._totalcount: Attribute[int] = NotSet
        self._nodes: Attribute[List[MergeCommitGQL]] = NotSet

    @property
    def totalCount(self) -> int:
        return self._totalcount.value
    
    @property
    def nodes(self) -> List[MergeCommitGQL]:
        return self._nodes.value
    
    def _useAttributes(self, attributes: dict[str, Any]) -> None:
        if "totalCount" in attributes:
            self._totalcount = self._makeIntAttribute(attributes["totalCount"])
        if "nodes" in attributes:
            self._nodes = self._makeListOfClassesAttribute(MergeCommitGQL, attributes["nodes"])

class PullRequestGQL(GraphQlObject, NonCompletableGithubObject):
    def _initAttributes(self) -> None:
        # super()._initAttributes()
        self._number: Attribute[int] = NotSet
        self._title: Attribute[str] = NotSet
        self._headrefname: Attribute[str] = NotSet
        self._mergecommit: Attribute[MergeCommitGQL] = NotSet
        self._merged: Attribute[bool] = NotSet
        self._viewercandeleteheadref: Attribute[bool] = NotSet
        self._commits: Attribute[CommitsHolderGQL] = NotSet
    
    @property
    def number(self) -> int:
        return self._number.value

    @property
    def title(self) -> str:
        return self._title.value

    @property
    def headRefName(self) -> str:
        return self._headrefname.value

    @property
    def viewerCanDeleteHeadRef(self) -> bool:
        return self._viewercandeleteheadref.value

    @property
    def mergeCommit(self) -> MergeCommitGQL | None:
        return self._mergecommit.value

    @property
    def merged(self) -> bool:
        return self._merged.value

    @property
    def commits(self) -> CommitsHolderGQL | None:
        return self._commits.value
    

    @property
    def canDeleteBranch(self) -> bool:
        """
        Determines if the branch associated with this pull request can be deleted.
        The branch can be deleted if:
        - The pull request has been merged.
        - The viewer has permission to delete the head reference.
        - There is a merge commit associated with the pull request.
        - The head reference is still present.
        
        :return: True if the branch can be deleted, False otherwise.
        :rtype: bool
        """
        return (
            self.merged
            and self.viewerCanDeleteHeadRef
            and self.mergeCommit is not None
            and self.commits is not None
            and self.commits.totalCount > 0
            and len(self.commits.nodes) > 0
        )

    def _useAttributes(self, attributes: dict[str, Any]) -> None:
        if "number" in attributes:
            self._number = self._makeIntAttribute(attributes["number"])

        if "title" in attributes:
            self._title = self._makeStringAttribute(attributes["title"])
        
        if "headRefName" in attributes:
            self._headrefname = self._makeStringAttribute(attributes["headRefName"])
        
        if "mergeCommit" in attributes:
            self._mergecommit = self._makeClassAttribute(MergeCommitGQL, attributes["mergeCommit"])

        if "merged" in attributes:
            self._merged = self._makeBoolAttribute(attributes["merged"])

        if "viewerCanDeleteHeadRef" in attributes:
            self._viewercandeleteheadref = self._makeBoolAttribute(attributes["viewerCanDeleteHeadRef"])

        if "commits" in attributes:
            self._commits = self._makeClassAttribute(CommitsHolderGQL, attributes["commits"])

def __get_pull_request_gql(gh: github.Github, repo: str) -> PaginatedList[PullRequestGQL]:
    query = """
fragment inner_commit on Commit {
    abbreviatedOid
    id
    oid
    committedDate
    authoredDate
}

query Q(
    $repo: String!
    $owner: String!
    $first: Int
    $last: Int
    $before: String
    $after: String
) {
    repository(name: $repo, owner: $owner) {
        pullRequests(
            first: $first
            last: $last
            before: $before
            after: $after
            orderBy: { direction: DESC, field: UPDATED_AT }
            states: [CLOSED, MERGED]
        ) {
            totalCount
            pageInfo {
                startCursor
                endCursor
                hasNextPage
                hasPreviousPage
            }
            nodes {
                number
                title
                headRefName
                mergeCommit {
                    ...inner_commit
                }
                commits(last: 1) {
                    totalCount
                    nodes {
                        commit {
                            ...inner_commit
                        }
                    }
                }
                merged
                viewerCanDeleteHeadRef
            }
        }
    }
}

"""
    repo_split = repo.split("/")
    variables = {
        "owner": repo_split[0],
        "repo": repo_split[1],
        
    }
    return PaginatedList(
        PullRequestGQL,
        gh.requester,
        graphql_query=query,
        graphql_variables=variables,
        list_item=["repository", "pullRequests"],
    )

def __get_git_repo(path: str) -> git.Repo:

    try:
        repo = git.Repo(path, search_parent_directories=True)
        logger.debug(f"Found git repository at {repo.working_tree_dir}")
        return repo
    except git.exc.InvalidGitRepositoryError as e:
        logger.critical(e, exc_info=True)
        sys.exit(1)

def __get_origin_url_from_repo(repo: git.Repo) -> str:
    try:
        url = repo.remotes.origin.url
        if url is None:
            raise ValueError("Remote 'origin' has no URL.")
        return url
    except Exception:
        logger.critical("Could not find git remote origin URL. Run this inside a git repo with origin remote.")
        sys.exit(1)


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

def __parse_github_owner_repo(url: str) -> str:
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
    logger.critical(f"Unsupported remote URL format: {url}")
    sys.exit(1)

def __get_github() -> Github:
    """
    Get's the Github API instance, using a token from the environment or `gh` CLI if available.
    
    :return: Instance of the Github API
    :rtype: Github
    """
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
        gh = Github(per_page=100)
    return gh

def main(directory: str):
    git_repo = __get_git_repo(directory)
    url = __get_origin_url_from_repo(git_repo)
    owner_repo = __parse_github_owner_repo(url)
    gh = __get_github()

    try:
        repo = gh.get_repo(owner_repo)
    except Exception as e:
        logger.critical(f"Failed to access repository {Fore.YELLOW}{owner_repo}: {e}")
        sys.exit(1)
    logger.info(f"Loading data for repository: {Fore.YELLOW}{owner_repo}")

    # Fetch closed PRs and filter for merged
    logger.info("Fetching closed pull requests and filtering merged ones...")
    all_prs = []
    can_delete = []
    try:
        pulls = __get_pull_request_gql(gh, owner_repo) #repo.get_pulls(state='closed', sort='updated', direction='desc')
        for pr in tqdm(pulls, total=pulls.totalCount, desc="Processing PRs"):
            all_prs.append(pr)
            # Required: merged, can delete ref, and merge commit
            if pr.merged and pr.viewerCanDeleteHeadRef and pr.mergeCommit and pr.commits and pr.commits.totalCount > 0:
                # verify that the merge commit is AFTER the last commit on the branch
                merge_date = min(pr.mergeCommit.authoredDate, pr.mergeCommit.committedDate) if pr.mergeCommit else None
                commit_date = max(pr.commits.nodes[0].authoredDate, pr.commits.nodes[0].committedDate) if pr.commits and pr.commits.totalCount > 0 else None
                if merge_date is None or commit_date is None:
                    logger.warning(f"{Fore.RESET}Missing dates - Skipping PR {Fore.RED}#{pr.number}{Fore.RESET} '{pr.title}': merge_date={merge_date}, commit_date={commit_date}.")
                    continue
                if merge_date <= commit_date:
                    can_delete.append(pr)
                else:
                    logger.warning(f"{Fore.RESET}Suspicious commit - Skipping PR {Fore.RED}#{pr.number}{Fore.RESET} '{pr.title}': merge commit date {merge_date} is before last commit date {commit_date}.")
            else:
                logger.info(f"Skipping merged PR: {Fore.RED}#{pr.number}{Fore.RESET} '{pr.title}': merged={pr.merged}, viewerCanDeleteHeadRef={pr.viewerCanDeleteHeadRef}, mergeCommit={'present' if pr.mergeCommit else 'absent'}, commits_count={pr.commits.totalCount if pr.commits else 'N/A'}")
    except Exception as e:
        logger.critical(e)
        sys.exit(1)

    logger.info(f"Found {Fore.GREEN}{len(can_delete)}{Fore.RESET} merged PR(s):")

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