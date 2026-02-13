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

    issue_id: int = Field(..., description="GitHub issue number", gt=0)

    mode: TaskMode = Field(..., description="Execution mode for the task")

    trigger_user: str = Field(..., description="User who triggered the task", min_length=1)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/example/test-repo",
                "issue_id": 42,
                "mode": "plan",
                "trigger_user": "dev1",
            }
        }
