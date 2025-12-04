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
#   "sourcetypes3~=0.1.0",
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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
import os
import re
import subprocess
import sys
import argparse
from typing import Any, List

from github import Github
import github
import git
import re

import colorlog
from github.AuthenticatedUser import AuthenticatedUser
from github.PullRequest import PullRequest
from github.Repository import Repository

from requests_cache import install_cache
from tqdm import tqdm

from sourcetypes import graphql

from colorama import Fore

R = Fore.RED
G = Fore.GREEN
B = Fore.BLUE
Y = Fore.YELLOW
W = Fore.WHITE
RESET = Fore.RESET

REPLACE_URL = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)$")

from github.GithubObject import (
    Attribute,
    GraphQlObject,
    NotSet,
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
    '${message}', style='$'))  # secondary_log_colors=secondary_log_colors
log_handler.setLevel(level=logging.DEBUG)
log_handler.addFilter(lambda record: record.levelno < logging.WARNING)

logger.addHandler(error_handler)
logger.addHandler(log_handler)
logger.propagate = False


class CommitGQL(GraphQlObject, NonCompletableGithubObject):
    """
    Represents a Git commit.
    Attributes:
        abbreviated_oid (str): The abbreviated object ID of the commit.
        id (str): The unique identifier of the commit.
        oid (str): The full object ID of the commit.
        committed_date (datetime): The date when the commit was made.
        authored_date (datetime): The date when the commit was authored.
    """

    def _initAttributes(self) -> None:
        # super()._initAttributes()
        self._abbreviated_oid: Attribute[str] = NotSet
        self._id: Attribute[str] = NotSet
        self._oid: Attribute[str] = NotSet
        self._committed_date: Attribute[datetime] = NotSet
        self._authored_date: Attribute[datetime] = NotSet

    @property
    def abbreviated_oid(self) -> str:
        return self._abbreviated_oid.value

    @property
    def id(self) -> str:
        return self._id.value

    @property
    def oid(self) -> str:
        return self._oid.value

    @property
    def committed_date(self) -> datetime:
        """
        The commit date gets changed every time the commit is being modified, 
        for example when rebasing the branch where the commit is in on another branch.
        
        :param self: Description
        :return: Description
        :rtype: datetime
        """
        return self._committed_date.value

    @property
    def authored_date(self) -> datetime:
        """
        The author date notes when this commit was originally made (i.e. when you finished the git commit). 
        According to the docs of git commit, the author date could be overridden using the --date switch.

        :param self: Description
        :return: Description
        :rtype: datetime
        """
        return self._authored_date.value

    def _useAttributes(self, attributes: dict[str, Any]) -> None:
        # super class is a REST API GithubObject, attributes are coming from GraphQL
        # super()._useAttributes(as_rest_api_attributes(attributes))
        if "abbreviatedOid" in attributes:
            self._abbreviated_oid = self._makeStringAttribute(attributes["abbreviatedOid"])
        if "id" in attributes:
            self._id = self._makeStringAttribute(attributes["id"])
        if "oid" in attributes:
            self._oid = self._makeStringAttribute(attributes["oid"])
        if "committedDate" in attributes:
            self._committed_date = self._makeDatetimeAttribute(attributes["committedDate"])
        if "authoredDate" in attributes:
            self._authored_date = self._makeDatetimeAttribute(attributes["authoredDate"])


class PullRequestCommit(GraphQlObject, NonCompletableGithubObject):
    def _initAttributes(self) -> None:
        self._commit: Attribute[CommitGQL] = NotSet

    @property
    def commit(self) -> CommitGQL:
        return self._commit.value

    def _useAttributes(self, attributes: dict[str, Any]) -> None:
        if "commit" in attributes:
            self._commit = self._makeClassAttribute(CommitGQL, attributes["commit"])


class CommitsHolderGQL(GraphQlObject, NonCompletableGithubObject):
    def _initAttributes(self) -> None:
        self._total_count: Attribute[int] = NotSet
        self._nodes: Attribute[List[PullRequestCommit]] = NotSet

    @property
    def total_count(self) -> int:
        return self._total_count.value

    @property
    def nodes(self) -> List[PullRequestCommit]:
        return self._nodes.value

    def _useAttributes(self, attributes: dict[str, Any]) -> None:
        if "totalCount" in attributes:
            self._total_count = self._makeIntAttribute(attributes["totalCount"])
        if "nodes" in attributes:
            self._nodes = self._makeListOfClassesAttribute(PullRequestCommit, attributes["nodes"])


class PullRequestGQL(GraphQlObject, PullRequest):
    """
    Represents a GitHub Pull Request with additional GraphQL attributes.
    Extends the standard PullRequest class from PyGithub.
    Attributes:
        headref_name (str): The name of the head reference (branch) for the pull
        request.
        merge_commit (CommitGQL | None): The commit that merged the pull request,
        if available.
        viewer_can_delete_head_ref (bool): Indicates if the viewer can delete the
        head reference.
        last_commits (CommitsHolderGQL | None): The last commits associated with
        the pull request.
    """
    def _initAttributes(self) -> None:
        super()._initAttributes()
        self._headref_name: Attribute[str] = NotSet
        self._merge_commit: Attribute[CommitGQL] = NotSet
        self._viewer_can_delete_headref: Attribute[bool] = NotSet
        self._commits: Attribute[CommitsHolderGQL] = NotSet

    @property
    def headref_name(self) -> str:
        return self._headref_name.value

    @property
    def viewer_can_delete_head_ref(self) -> bool:
        return self._viewer_can_delete_headref.value

    @property
    def merge_commit(self) -> CommitGQL | None:
        return self._merge_commit.value


    @property
    def last_commits(self) -> CommitsHolderGQL | None:
        return self._last_commits.value


    @property
    def can_delete_branch(self) -> bool:
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
                and self.viewer_can_delete_head_ref
                and self.merge_commit is not None
                and self.last_commits is not None
                and self.last_commits.total_count > 0
                and len(self.last_commits.nodes) > 0
        )

    def _useAttributes(self, attributes: dict[str, Any]) -> None:
        super()._useAttributes(attributes)
        if "http_url" in attributes:
            # replace "https://github.com/DTMX/infrastructure/pull/1690"
            # with 'https://api.github.com/repos/DTMX/infrastructure/pulls/1146'
            api_url = REPLACE_URL.sub(lambda m: f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}/pulls/{m.group(3)}",
                attributes["http_url"])
            super()._useAttributes({"url": api_url})

        if "headRefName" in attributes:
            self._headref_name = self._makeStringAttribute(attributes["headRefName"])

        if "mergeCommit" in attributes:
            self._merge_commit = self._makeClassAttribute(CommitGQL, attributes["mergeCommit"])

        if "viewerCanDeleteHeadRef" in attributes:
            self._viewer_can_delete_headref = self._makeBoolAttribute(attributes["viewerCanDeleteHeadRef"])

        if "last_commits" in attributes:
            self._last_commits = self._makeClassAttribute(CommitsHolderGQL, attributes["last_commits"])


def __get_pull_request_gql(gh: github.Github, repo: str) -> PaginatedList[PullRequestGQL]:
    query: graphql = """
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
                                     last_commits: commits(last: 1) {
                                         totalCount
                                         nodes {
                                             commit {
                                                 ...inner_commit
                                             }
                                         }
                                     }
                                     merged
                                     viewerCanDeleteHeadRef
                                     http_url : permalink
                                     user: author {
                                         login
                                     }
                                 }
                             }
                         }
                     } \
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
    except Exception as e:
        logger.critical(
            Exception("Could not find git remote origin URL. Run this inside a git repo with origin remote.", e),
            exc_info=True)
        sys.exit(1)


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
    Gets the GitHub API instance, using a token from the environment or `gh` CLI if available.
    
    :return: Instance of the GitHub API
    :rtype: GitHub
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
        gh = Github(auth=github.Auth.Token(token), per_page=100)
    else:
        logger.warning("no GITHUB_TOKEN found — unauthenticated requests are rate-limited.")
        gh = Github()
    return gh


def __get_me(gh: Github) -> AuthenticatedUser:
    try:
        me: AuthenticatedUser = gh.get_user()
        logger.debug(f"Authenticated as GitHub user: {Y}{me.login}")
        return me
    except Exception as e:
        logger.critical(f"Failed to get authenticated user: {e}")
        sys.exit(1)


def __ask_question(question: str) -> bool:
    """
    Asks a yes/no question via input() and returns True for 'yes' and False for 'no'.
    :param question: The question to ask the user.
    :return: True if the user answered 'yes', False if 'no'.
    :rtype: bool
    """
    while True:
        answer = input(f"{Y}{question}{RESET} "
                       f"{Y}[{G}y{Y}/{R}n{Y}]{RESET}: ").strip().lower()
        if answer in ("y", "yes", "Y", "YES"):
            return True
        elif answer in ("n", "no", "N", "NO"):
            return False
        else:
            print(f"Please enter '{G}y{RESET}' or '{R}n{RESET}'.")


def __load_repo(gh: Github, directory: str, repo: str | None) -> Repository:
    if repo is not None:
        try:
            return gh.get_repo(repo, lazy=False)
        except Exception as e:
            raise Exception(f"Failed to load repository {repo}: {e}") from e
    try:
        git_repo = __get_git_repo(directory)
        url = __get_origin_url_from_repo(git_repo)
        return gh.get_repo(url, lazy=False)
    except Exception as e:
        raise Exception(f"Failed to detect repository from git remote: {e}") from e


def __delete_branch(pr: PullRequestGQL) -> PullRequestGQL:
    try:
        logger.info(pr.head)
        # pr.delete_branch()
        # repo.delete_git_ref(f"heads/{pr.headref_name}")
        logger.info(f"{G}Deleted remote branch for PR #{pr.number:<6}: {pr.headref_name}{RESET}")
        return pr
    except Exception as e:
        logger.warning(f"Failed to delete remote branch for PR #{pr.number}", e)


def main(repo_name: str | None, path: str, everyone: bool = False) -> None:
    gh = __get_github()
    try:
        repo = __load_repo(gh, path, repo_name)
    except Exception as e:
        logger.critical(e)
        sys.exit(1)
    logger.info(f"Loading data for repository: {Y}{repo.full_name}")

    # Fetch closed PRs and filter for merged
    logger.debug("Fetching closed pull requests and filtering merged ones...")
    all_prs: List[PullRequestGQL] = []
    can_delete: List[PullRequestGQL] = []
    try:
        pulls: PaginatedList[PullRequestGQL] = __get_pull_request_gql(gh, repo.full_name)
        # repo.get_pulls(state='closed', sort='updated', direction='desc')
        pr: PullRequestGQL
        for pr in tqdm(pulls, total=pulls.totalCount, desc="Processing PRs"):
            all_prs.append(pr)
            # Required: merged, can delete ref, and merge commit
            try:
                if pr.can_delete_branch:
                    # verify that the merge commit is AFTER the last commit on the branch
                    merge_date = min(pr.merge_commit.authored_date,
                                     pr.merge_commit.committed_date) if pr.merge_commit else None
                    last_commit_date = max(pr.last_commits.nodes[0].commit.authored_date, pr.last_commits.nodes[
                        0].commit.committed_date) if pr.last_commits and pr.last_commits.total_count > 0 else None
                    if merge_date is None or last_commit_date is None:
                        logger.warning(
                            f"{RESET}Missing dates - Skipping PR {Y}#{pr.number:<6}{R} {B}'{pr.title}{W}: "
                            f"merge_date={Y}{merge_date}{W}, "
                            f"commit_date={Y}{last_commit_date}{W}.")
                        continue
                    if merge_date >= last_commit_date:
                        can_delete.append(pr)
                    else:
                        logger.warning(
                            f"{RESET}Suspicious commit - Skipping PR {Y}#{pr.number:<6}{R} {B}'{pr.title}{W}: "
                            f"merge commit date {Y}{merge_date}{W} is before last commit date {Y}{last_commit_date}{W}.")
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"Skipping merged PR{W}: {Y}#{pr.number:<6}{W} {B}'{pr.title}{W}': "
                            f"merged={Y}{pr.merged}{W}, "
                            f"viewerCanDeleteHeadRef={Y}{pr.viewer_can_delete_head_ref}{W}, "
                            f"mergeCommit={Y}{'present' if pr.merge_commit else 'absent'}{W}, "
                            f"commits_count={Y}{pr.last_commits.total_count if pr.last_commits else 'N/A'}{W}")
            except Exception as e:
                logger.error(
                    f"Error processing PR {Y}#{pr.number:<6}{W} {B}'{pr.title}{W}: {e}",
                    exc_info=True)
                continue
    except Exception as e:
        logger.critical(e)
        sys.exit(1)
    can_delete.sort(key=lambda r: r.merge_commit.committed_date)
    logger.info(f"Found {G}{len(can_delete)}{RESET} merged PR(s):")
    list_pr = __ask_question("Would you like to list all the PR's?")
    if list_pr:
        for pr in can_delete:
            logger.info(f"{RESET}\t#{Y}{pr.number:<6}{RESET} {B}'{pr.title}'{RESET} "
                        f"on branch {Y}{pr.headref_name}{RESET} "
                        f"merged via commit {Y}{pr.merge_commit.abbreviated_oid if pr.merge_commit else 'N/A'}{RESET}"
                        f"on {Y}{pr.merge_commit.committed_date if pr.merge_commit else 'N/A'}{RESET} ")

    delete_pr = __ask_question("Would you like to delete the remote branches for these PR's?")
    if delete_pr:
        with ThreadPoolExecutor(max_workers=8) as executor:
            #prs_to_delete_ops = {executor.submit(__delete_branch, pr): pr for pr in can_delete}
            # for pr in tqdm(can_delete):
            results = list(tqdm(executor.map(__delete_branch, can_delete), total=len(can_delete), desc="Deleting branches"))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Clean up local git branches for merged PRs.")
    parser.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="the repository in the format 'owner/repo' (default: detected from git remote origin)",
    )
    parser.add_argument(
        "--path",
        nargs="?",
        default=os.getcwd(),
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
        logger.debug("Enabling HTTP caching for GitHub API requests...")
        install_cache(
            cache_control=True,
        )
    args = parser.parse_args()
    main(args.repo, args.path)
