"""Refine Mode implementation - Iterative code refinement from PR review comments.

This mode allows users to request changes on an existing pull request by
commenting with a /refine command. The workflow clones the PR branch, applies
the requested modifications using an LLM, pushes the changes, and reacts to
the original comment to confirm completion.
"""

import structlog

from worker.config import settings
from worker.git.git_client import GitClient
from worker.git.git_handler import GitHandler
from worker.llm_client import LLMClient
from worker.models import TaskMessage

logger = structlog.get_logger()


class RefineMode:
    """Orchestrate Refine Mode workflow.

    Handles iterative code refinement based on PR review feedback.
    Clones the PR branch, applies LLM-driven changes, and pushes
    the result back to the same branch.
    """

    def __init__(
        self,
        git_handler: GitHandler,
        git_client: GitClient,
        llm_client: LLMClient,
    ):
        """
        Initialize Refine Mode handler.

        Args:
            git_handler: Handler for git operations (clone, push, cleanup).
            git_client: Client for GitHub API interactions.
            llm_client: Client for LLM-powered code generation.
        """
        self.log = logger.bind(mode="refine")
        self.git_handler = git_handler
        self.git = git_client
        self.llm_client = llm_client

    async def execute(self, task: TaskMessage) -> None:
        """
        Execute Refine Mode workflow.

        Performs the following steps:
            1. Clones the repository on the PR branch.
            2. Applies code refinements using the LLM based on the user's request.
            3. Pushes the updated code to the PR branch.
            4. Adds a rocket reaction to the triggering comment.

        Args:
            task: Task message containing repo_url, pr_number, pr_branch,
                  refine_request, and comment_id.

        Raises:
            ValueError: If required fields (pr_number, pr_branch, comment_id)
                        are missing from the task.
            Exception: If any step in the workflow fails.
        """
        # Validate required fields
        if not task.pr_number:
            raise ValueError("pr_number is required for Refine mode")
        if not task.pr_branch:
            raise ValueError("pr_branch is required for Refine mode")
        if not task.comment_id:
            raise ValueError("comment_id is required for Refine mode")

        repo_url = str(task.repo_url)
        pr_number = task.pr_number
        pr_branch = task.pr_branch
        refine_request = task.refine_request or ""
        comment_id = task.comment_id

        self.log.info(
            "refine_mode_start",
            msg="Starting Refine Mode",
            repo=repo_url,
            pr_number=pr_number,
            branch=pr_branch,
        )

        repo_name = None

        try:
            # Get repository object
            repo_obj = self.git.client.get_repository(repo_url)

            # Clone repository directly on the PR branch
            repo_name = f"repo-pr-{pr_number}"
            repo_path = self.git_handler.shallow_clone(
                repo_url=repo_url, target_dir=repo_name, branch=pr_branch, token=settings.github_token
            )

            # Apply refinements using LLM
            self.log.info("applying_refinements", msg="Applying code refinements")
            await self.llm_client.refine_code(refine_request, str(repo_path))

            # Push changes
            self.log.info("pushing_changes", msg="Pushing refined code")
            self.git_handler.push_branch(repo_path, pr_branch)

            # Add rocket reaction to the refine comment
            self.log.info("adding_reaction", msg="Adding rocket reaction to refine comment")
            issue = repo_obj.get_issue(pr_number)
            self.git.client.add_comment_reaction(issue, comment_id, reaction="rocket")

            self.log.info("refine_complete", msg="Refine mode completed successfully", pr_number=pr_number)

        except Exception as e:
            self.log.error("refine_failed", msg="Refine mode failed", error=str(e), exc_info=True)
            raise

        finally:
            if repo_name:
                self.git_handler.cleanup(repo_name)
            await self.llm_client.close()
