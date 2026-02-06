"""GitHub API client for issue and PR management."""

from typing import Optional, Dict, Any, List
from github import Github, GithubException
from github.Repository import Repository
from github.Issue import Issue
from github.PullRequest import PullRequest
import structlog

from config import settings

logger = structlog.get_logger()


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token. Uses settings if not provided.
        """
        self.token = token or settings.github_token
        self.client = Github(self.token)
        self.log = logger.bind(service="github")

    def get_repository(self, repo_url: str) -> Repository:
        """
        Get repository object from URL.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Repository object
        """
        # Extract owner/repo from URL
        # Remove trailing slash and .git suffix properly
        clean_url = repo_url.rstrip("/")
        if clean_url.endswith(".git"):
            clean_url = clean_url[:-4]

        parts = clean_url.split("/")
        owner, repo = parts[-2], parts[-1]

        full_name = f"{owner}/{repo}"
        self.log.info("get_repo", msg="Fetching repository", repo=full_name)

        try:
            return self.client.get_repo(full_name)
        except GithubException as e:
            self.log.error(
                "repo_fetch_failed", msg="Failed to fetch repo", error=str(e)
            )
            raise

    def get_issue(self, repo: Repository, issue_id: int) -> Issue:
        """
        Get issue by ID.

        Args:
            repo: Repository object
            issue_id: Issue number

        Returns:
            Issue object
        """
        self.log.info("get_issue", msg="Fetching issue", issue_id=issue_id)

        try:
            return repo.get_issue(issue_id)
        except GithubException as e:
            self.log.error(
                "issue_fetch_failed", msg="Failed to fetch issue", error=str(e)
            )
            raise

    def get_issue_data(self, issue: Issue) -> Dict[str, Any]:
        """
        Extract relevant data from issue.

        Args:
            issue: GitHub Issue object

        Returns:
            Dictionary with issue data
        """
        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "state": issue.state,
            "labels": [label.name for label in issue.labels],
            "author": issue.user.login,
            "created_at": issue.created_at.isoformat(),
            "updated_at": issue.updated_at.isoformat(),
            "comments_count": issue.comments,
            "url": issue.html_url,
        }

    def create_pull_request(
        self,
        repo: Repository,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False,
    ) -> PullRequest:
        """
        Create a pull request.

        Args:
            repo: Repository object
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch (default: main)
            draft: Create as draft PR

        Returns:
            PullRequest object
        """
        self.log.info(
            "creating_pr",
            msg="Creating pull request",
            title=title,
            head=head,
            base=base,
            draft=draft,
        )

        try:
            pr = repo.create_pull(
                title=title, body=body, head=head, base=base, draft=draft
            )

            self.log.info("pr_created", msg="Pull request created", pr_number=pr.number)
            return pr

        except GithubException as e:
            self.log.error(
                "pr_creation_failed", msg="Failed to create PR", error=str(e)
            )
            raise

    def add_pr_comment(self, pr: PullRequest, comment: str) -> None:
        """
        Add comment to pull request.

        Args:
            pr: PullRequest object
            comment: Comment text
        """
        self.log.info("adding_comment", msg="Adding comment to PR", pr_number=pr.number)

        try:
            pr.create_issue_comment(comment)
            self.log.info("comment_added", msg="Comment added")
        except GithubException as e:
            self.log.error("comment_failed", msg="Failed to add comment", error=str(e))
            raise

    def add_issue_comment(self, issue: Issue, comment: str) -> None:
        """
        Add comment to issue.

        Args:
            issue: Issue object
            comment: Comment text
        """
        self.log.info(
            "adding_comment", msg="Adding comment to issue", issue_number=issue.number
        )

        try:
            issue.create_comment(comment)
            self.log.info("comment_added", msg="Comment added")
        except GithubException as e:
            self.log.error("comment_failed", msg="Failed to add comment", error=str(e))
            raise

    def add_labels(self, issue: Issue, labels: List[str]) -> None:
        """
        Add labels to issue or PR.

        Args:
            issue: Issue or PullRequest object
            labels: List of label names
        """
        self.log.info("adding_labels", msg="Adding labels", labels=labels)

        try:
            issue.add_to_labels(*labels)
            self.log.info("labels_added", msg="Labels added")
        except GithubException as e:
            self.log.error("labels_failed", msg="Failed to add labels", error=str(e))
            raise
