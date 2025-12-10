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
#   "blessed~=1.25.0",
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
from datetime import datetime, timedelta, timezone
import logging
import os
import re
import subprocess
import sys
import argparse
from typing import Any, List

from blessed import Terminal

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

from colorama import Fore, Back, Style

term : Terminal = Terminal()

R = term.red
G = term.green
B = term.blue
Y = term.yellow
W = term.white
RESET = term.normal

R_BG = Back.RED
Y_BG = Back.YELLOW
RESET_BG = Back.RESET

R_ALL = Style.RESET_ALL

VERBOSE = False
VERY_VERBOSE = False

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
        if "html_url" in attributes:
            api_url = REPLACE_URL.sub(lambda m: f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}/pulls/{m.group(3)}",
                attributes["html_url"])
            super()._useAttributes({"url": api_url})

        if "headRefName" in attributes:
            self._headref_name = self._makeStringAttribute(attributes["headRefName"])

        if "mergeCommit" in attributes:
            self._merge_commit = self._makeClassAttribute(CommitGQL, attributes["mergeCommit"])

        if "viewerCanDeleteHeadRef" in attributes:
            self._viewer_can_delete_headref = self._makeBoolAttribute(attributes["viewerCanDeleteHeadRef"])

        if "last_commits" in attributes:
            self._last_commits = self._makeClassAttribute(CommitsHolderGQL, attributes["last_commits"])


def __check_if_branch_pr_safe_to_delete(pr: PullRequestGQL, minimum_age: int | None = None) -> bool:
    if not pr.viewer_can_delete_head_ref:
        return False

    if pr.merged:
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
            return False
        if merge_date >= last_commit_date:
            if minimum_age and minimum_age > 0:
                if merge_date <= datetime.now(tz=timezone.utc) - timedelta(days=minimum_age):
                    return True
                else:
                    if VERBOSE:
                        logger.debug(
                            f"{RESET}Skipping PR {Y}#{pr.number:<6}{W} {B}'{pr.title}{W} because it is not older than {Y}{minimum_age}{W} days ")
            else:
                return True
        else:
            pr_link = f"{RESET}\t#{Y}{term.link(pr.html_url, f"{pr.number}")}{RESET}"
            logger.warning(
                f"{RESET}Suspicious commit - Skipping PR {pr_link}{R} {B}'{pr.title}{W}: "
                f"merge commit date {Y}{merge_date}{W} is before last commit date {Y}{last_commit_date}{W}.")
    else:
        if VERY_VERBOSE:
            logger.info(
                f"Skipping merged PR{W}: {Y}#{pr.number:<6}{W} {B}'{pr.title}{W}': "
                f"merged={Y}{pr.merged}{W}, "
                f"viewerCanDeleteHeadRef={Y}{pr.viewer_can_delete_head_ref}{W}, "
                f"mergeCommit={Y}{'present' if pr.merge_commit else 'absent'}{W}, "
                f"commits_count={Y}{pr.last_commits.total_count if pr.last_commits else 'N/A'}{W}")
    return False


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
                                     html_url : permalink
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
        if VERBOSE:
            logger.info(f"Found git repository at {repo.working_tree_dir}")
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
                    if VERBOSE:
                        logger.info("Using GitHub token from `gh auth token`.")
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


def __ask_question(question: str, default_answer: bool = None) -> bool:
    """
    Asks a yes/no question via input() and returns True for 'yes' and False for 'no'.
    :param question: The question to ask the user.
    :return: True if the user answered 'yes', False if 'no'.
    :rtype: bool
    """
    print()
    str_template = f"{Y}{question}{RESET} {Y}[{G}Y{Y}/{R}N{Y}]{RESET}: "
    if default_answer is not None:
        if default_answer:
            print(str_template + f"{G}y{RESET}")
        else:
            print(str_template + f"{R}n{RESET}")
        return default_answer
    while True:
        answer = input(str_template).strip().lower()
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


def __delete_branch(pr: PullRequestGQL, force: bool = False) -> PullRequestGQL:
    try:
        pr.delete_branch(force)
        logger.info(f"{G}Deleted remote branch for PR {Y}#{pr.number:<6}{RESET}: {B}{pr.headref_name}{RESET}")
        return pr
    except Exception as e:
        logger.warning(f"Failed to delete remote branch for PR #{pr.number}", e)
    return pr

def log_run(pr: PullRequestGQL) -> None:
    # pr_link = term.link(pr.html_url, f"{RESET}\t#{Y}{pr.number:<6}{RESET}")
    # pr_link = term.link(pr.html_url, f"{RESET}\t#{Y}{pr.number:<6}{RESET}")
    pr_link = f"{RESET}\t#{Y}{term.link(pr.html_url, f"{pr.number:<6}")}{RESET}"

    pr_log = f"{pr_link} {B}'{pr.title}'{RESET} " \
    f"on branch {Y}{pr.headref_name}{RESET} " \
    f"merged via commit {Y}{pr.merge_commit.abbreviated_oid if pr.merge_commit else 'N/A'}{RESET} " \
    f"from {Y}{pr.last_commits.nodes[0].commit.abbreviated_oid}{RESET} " \
    f"on {Y}{pr.merge_commit.committed_date if pr.merge_commit else 'N/A'}{RESET}"
    logger.info(pr_log)


def run_script(repo_name: str | None, path: str,
               min_age_days: int = -1,
               everyone: bool = False,
               dryrun: bool = False,
               default_answer: bool = None) -> None:
    gh = __get_github()
    try:
        repo = __load_repo(gh, path, repo_name)
    except Exception as e:
        logger.critical(e)
        sys.exit(1)
    logger.info(f"Loading data for repository: {Y}{repo.full_name}")
    open_prs = term.link(repo.html_url + "/pulls?q=is%3Apr+is%3Aopen", f"{repo.get_pulls(state='open').totalCount:>3}")

    logger.info(f" There are currently {Y}{open_prs}{RESET} open pull requests.")
    logger.info(f" There are currently {Y}{repo.get_branches().totalCount:>3}{RESET} branches open.")
    # fix for "store_true"
    default_answer = default_answer if default_answer is True else None
    clean_repo(gh, repo, min_age_days, dryrun, default_answer)

def clean_repo(gh: Github,
               repo: Repository,
               min_age_days: int,
               dryrun: bool = False,
               default_answer: bool = None) -> None:
    """
    Cleans up merged pull requests by deleting their remote branches if possible.
    :param gh: The GitHub API instance.
    :type gh: Github
    :param repo: The GitHub repository to clean up.
    :type repo: Repository
    :param min_age_days: Minimum age in days of merged PRs to consider for branch deletion.
    :type min_age_days: int
    :param dryrun: If True, performs a dry run without making changes.
    :type dryrun: bool
    :param default_answer: If True, automatically answers 'yes' to all prompts.
    :type default_answer: bool
    :return: None
    :rtype: None
    """
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
                        if min_age_days > 0:
                            if merge_date <= datetime.now(tz=timezone.utc) - timedelta(days=min_age_days):
                                can_delete.append(pr)
                            else:
                                if VERBOSE:
                                    logger.debug(f"{RESET}Skipping PR {Y}#{pr.number:<6}{W} {B}'{pr.title}{W} because it is not older than {Y}{min_age_days}{W} days ")
                        else:
                            can_delete.append(pr)
                    else:
                        pr_link = f"{RESET}\t#{Y}{term.link(pr.html_url, f"{pr.number}")}{RESET}"
                        logger.warning(
                            f"{RESET}Suspicious commit - Skipping PR {pr_link}{R} {B}'{pr.title}{W}: "
                            f"merge commit date {Y}{merge_date}{W} is before last commit date {Y}{last_commit_date}{W}.")
                else:
                    if VERY_VERBOSE:
                        logger.info(
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
    can_delete.sort(key=lambda r: r.merge_commit.committed_date, reverse=True)
    if len(can_delete) == 0:
        logger.info(f"{G}No merged PRs found that can be deleted.{RESET}")
        return
    logger.info(f"Found {G}{len(can_delete)}{RESET} applicable merged PR(s):")
    list_pr = dryrun or VERY_VERBOSE or __ask_question("Would you like to list all the PR's?", default_answer)
    if list_pr:
        for pr in can_delete:
            log_run(pr)
            # logger.info(f"{RESET}\t#{Y}{pr.number:<6}{RESET} {B}'{pr.title}'{RESET} "
            #             f"on branch {Y}{pr.headref_name}{RESET} "
            #             f"merged via commit {Y}{pr.merge_commit.abbreviated_oid if pr.merge_commit else 'N/A'}{RESET} "
            #             f"from {Y}{pr.last_commits.nodes[0].commit.abbreviated_oid}{RESET} "
            #             f"on {Y}{pr.merge_commit.committed_date if pr.merge_commit else 'N/A'}{RESET} ")
    delete_pr = __ask_question("Would you like to delete the remote branches for these PR's?", default_answer)
    if delete_pr and not dryrun:
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
        help="the repository in the format 'owner/repo' (default: detected from git remote origin).\n"
             "If none provided, the script will attempt to auto-detect the repository from the git remote."
    )
    parser.add_argument(
        "--path",
        nargs="?",
        default=os.getcwd(),
        help="Path to the workspace (default: current directory). Used for auto-detecting the git repo.",
    )
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help='Increase verbosity level'
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Forces update check even if not needed",
    )
    parser.add_argument(
        "--nocache",
        action="store_true",
        help="Disable HTTP caching for GitHub API requests",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Response with yes to everything",
    )
    parser.add_argument(
        "--min_age_days", "--min-age-days",
        type=int,
        default=-1,
        help="Minimum age in days of the merged PRs to consider for branch deletion",
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Perform a trial run with no changes made",
    )

    args = parser.parse_args()

    if args.verbose >= 1:
        VERBOSE = True
    if args.verbose >= 2:
        VERY_VERBOSE = True
    logging.basicConfig(
        level=logging.DEBUG if args.verbose >= 3 else logging.INFO,
        format="%(message)s",
    )
    if not args.nocache:
        if VERBOSE:
            logger.debug("Enabling HTTP caching for GitHub API requests...")
        install_cache(
            cache_control=True,
        )
    args = parser.parse_args()
    run_script(args.repo, args.path, args.min_age_days, dryrun=args.dryrun, default_answer=args.yes)
