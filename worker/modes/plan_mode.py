"""Plan Mode implementation - Human-in-the-loop workflow."""

from pathlib import Path
from typing import Dict, Any
import structlog

from models import TaskMessage
from git_handler import GitHandler
from github_client import GitHubClient
from context_builder import ContextBuilder
from llm_client import LLMClient
from config import settings

logger = structlog.get_logger()


class PlanMode:
    """Orchestrate Plan Mode workflow."""
    
    def __init__(self):
        """Initialize Plan Mode handler."""
        self.log = logger.bind(mode="plan")
        self.git_handler = GitHandler()
        self.github_client = GitHubClient()
        self.context_builder = ContextBuilder()
        self.llm_client = LLMClient(
            provider=settings.llm_provider,
            model=settings.llm_model
        )
    
    async def execute(self, task: TaskMessage) -> None:
        """
        Execute Plan Mode workflow.
        
        Args:
            task: Task message from queue
        """
        repo_url = str(task.repo_url)
        issue_id = task.issue_id
        
        self.log.info(
            "plan_mode_start",
            msg="Starting Plan Mode",
            repo=repo_url,
            issue=issue_id
        )
        
        repo_name = None
        
        try:
            # Clone repository
            repo_name = f"repo-{issue_id}"
            repo_path = self.git_handler.shallow_clone(
                repo_url=repo_url,
                target_dir=repo_name,
                token=settings.github_token
            )
            
            # Fetch issue from GitHub
            repo_obj = self.github_client.get_repository(repo_url)
            issue = self.github_client.get_issue(repo_obj, issue_id)
            issue_data = self.github_client.get_issue_data(issue)
            
            self.log.info("issue_fetched", msg="Issue data retrieved", title=issue_data['title'])
            
            # Build context
            file_tree = self.git_handler.get_file_tree(repo_path)
            relevant_files = self.context_builder.identify_relevant_files(
                repo_path, issue_data, max_files=10
            )
            file_contents = self.context_builder.read_file_contents(relevant_files)
            full_context = self.context_builder.build_full_context(
                issue_data, file_tree, file_contents
            )
            
            self.log.info(
                "context_built",
                msg="Context prepared",
                relevant_files=len(relevant_files)
            )
            
            # Generate plan with LLM
            plan = await self.llm_client.generate_plan(full_context, issue_data)
            
            self.log.info("plan_generated", msg="LLM plan generated")
            
            # Create branch and push to remote
            branch_name = f"ai-agent/issue-{issue_id}"
            self.git_handler.create_branch(repo_path, branch_name)
            
            # Create empty commit (GitHub requires at least one commit for PR)
            self.git_handler.commit_changes(
                repo_path,
                f"[AI Agent] Analyzing issue #{issue_id}\n\nThis branch will contain the implementation for the issue.",
                allow_empty=True
            )
            
            # Push branch to GitHub
            self.git_handler.push_branch(repo_path, branch_name)
            
            # Create draft PR
            pr_title = f"[AI Agent] Fix issue #{issue_id}: {issue_data['title']}"
            pr_body = f"""
## 🤖 AI Agent Proposal

This PR is created by the AI Coding Agent to address issue #{issue_id}.

**Status:** ⏳ Awaiting human approval

### Issue
{issue_data['title']}

### Proposed Plan

{plan}

---

**Next Steps:**
- Review the plan above
- If approved, comment `/approve` to proceed with implementation
- If changes needed, provide feedback in comments

**Related Issue:** #{issue_id}
"""
            
            try:
                pr = self.github_client.create_pull_request(
                    repo=repo_obj,
                    title=pr_title,
                    body=pr_body,
                    head=branch_name,
                    base="main",
                    draft=True
                )
                
                self.log.info("pr_created", msg="Draft PR created", pr_number=pr.number)
                
                # Add comment to issue
                issue_comment = f"""
🤖 **AI Agent Plan Generated**

I've analyzed this issue and created a draft PR with a proposed implementation plan.

**Draft PR:** #{pr.number}

Please review the plan and comment `/approve` on the PR to proceed with implementation.
"""
                
                self.github_client.add_issue_comment(issue, issue_comment)
                
                # Add labels
                self.github_client.add_labels(issue, ["ai-agent", "plan-pending"])
                
                self.log.info(
                    "plan_mode_complete",
                    msg="Plan Mode completed successfully",
                    pr_number=pr.number
                )
                
            except Exception as e:
                self.log.error("pr_failed", msg="Failed to create PR", error=str(e))
                raise
            
        finally:
            # Cleanup
            if repo_name:
                self.git_handler.cleanup(repo_name)
            await self.llm_client.close()
        
        self.log.info("plan_mode_done", msg="Plan Mode execution finished")

