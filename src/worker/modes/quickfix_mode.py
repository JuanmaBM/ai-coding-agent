"""QuickFix Mode implementation - Fire and forget workflow."""

import structlog

from worker.models import TaskMessage
from worker.git.git_handler import GitHandler
from worker.git.git_client import GitClient
from worker.llm_client import LLMClient
from worker.config import settings

logger = structlog.get_logger()


class QuickFixMode:
    """Orchestrate QuickFix Mode workflow."""

    def __init__(
        self,
        git_handler: GitHandler,
        git_client: GitClient,
        llm_client: LLMClient,
    ):
        """Initialize QuickFix Mode handler."""
        self.log = logger.bind(mode="quickfix")
        self.git_handler = git_handler
        self.git = git_client
        self.llm_client = llm_client

    async def execute(self, task: TaskMessage) -> None:
        """Execute QuickFix Mode workflow."""
        repo_url = str(task.repo_url)
        issue_id = task.issue_id

        self.log.info(
            "quickfix_mode_start", msg="Starting QuickFix Mode", repo=repo_url, issue=issue_id
        )

        repo_name = None

        try:
            # Clone repository
            repo_name = f"repo-{issue_id}"
            repo_path = self.git_handler.shallow_clone(
                repo_url=repo_url, target_dir=repo_name, token=settings.github_token
            )

            # Fetch issue
            repo_obj = self.git.client.get_repository(repo_url)
            issue = self.git.client.get_issue(repo_obj, issue_id)
            issue_data = self.git.client.get_issue_data(issue)

            branch_name = f"ai-agent/quickfix-issue-{issue_id}"
            self.git_handler.create_branch(repo_path, branch_name)

            # Generate code
            await self.llm_client.generate_code(issue_data, str(repo_path))

            self.git_handler.push_branch(repo_path, branch_name)

            # Create PR
            pr = self.git.client.create_pull_request(
                repo=repo_obj,
                title=f"[AI Agent QuickFix] Fix issue #{issue_id}: {issue_data['title']}",
                body=f"🤖 Automated fix for issue #{issue_id}",
                head=branch_name,
                base="main",
                draft=False,
            )

            self.git.client.add_issue_comment(issue, f"🤖 QuickFix applied. PR: #{pr.number}")
            self.git.client.add_labels(issue, ["ai-agent", "quickfix"])

            self.log.info("quickfix_complete", pr_number=pr.number)

        finally:
            if repo_name:
                self.git_handler.cleanup(repo_name)
            await self.llm_client.close()
