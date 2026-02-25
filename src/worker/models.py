"""Pydantic models for message validation."""

from enum import Enum
from pydantic import BaseModel, HttpUrl, Field


class TaskMode(str, Enum):
    """Execution modes for the AI agent."""

    QUICKFIX = "quickfix"
    REFINE = "refine"


class TaskMessage(BaseModel):
    """Message structure for tasks consumed from RabbitMQ."""

    repo_url: HttpUrl = Field(
        ..., description="GitHub repository URL to clone", examples=["https://github.com/user/repo"]
    )

    mode: TaskMode = Field(..., description="Execution mode for the task")

    trigger_user: str = Field(..., description="User who triggered the task", min_length=1)

    # QuickFix mode fields
    issue_id: int | None = Field(None, description="GitHub issue number (for quickfix mode)", gt=0)

    # Refine mode fields
    pr_number: int | None = Field(None, description="Pull request number (for refine mode)", gt=0)
    pr_branch: str | None = Field(None, description="PR branch name (for refine mode)")
    pr_title: str | None = Field(None, description="PR title (for refine mode)")
    base_branch: str | None = Field(None, description="Base branch name (for refine mode)")
    refine_request: str | None = Field(
        None, description="Refinement request from /refine command (for refine mode)"
    )
    comment_id: int | None = Field(None, description="GitHub comment ID (for refine mode)")
    comment_url: str | None = Field(None, description="GitHub comment URL (for refine mode)")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/example/test-repo",
                "issue_id": 42,
                "mode": "quickfix",
                "trigger_user": "dev1",
            }
        }
