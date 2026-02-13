"""LLM client for code generation using Ollama."""

import asyncio
import os
import subprocess
from typing import Optional, Dict, Any
import httpx
import structlog

from worker.config import settings

logger = structlog.get_logger()


class LLMClient:
    """Client for interacting with LLM providers (Ollama)."""

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen2.5-coder:14b",
        base_url: Optional[str] = None,
    ):
        """
        Initialize LLM client.

        Args:
            provider: LLM provider ("ollama")
            model: Model name to use
            base_url: Base URL for API
        """
        self.provider = provider
        self.model = model
        self.base_url = base_url or settings.ollama_base_url
        self.log = logger.bind(provider=provider, model=model)

        # HTTP client with extended timeouts for LLM generation
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(900, connect=10), follow_redirects=True
        )

    async def _call_aider(self, prompt: str, repo_path: str, allow_commits: bool = False):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"  # Force Python to flush logs immediately

        model_cmd = f"openai/{settings.llm_model}"

        self._configure_git_identity(repo_path)

        cmd = [
            "aider",
            "--model",
            model_cmd,
            "--yes",
            "--no-detect-urls",
            "--message",
            prompt,
        ]

        self.log.info(f"[ASYNC] Starting Aider at: {repo_path}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_path,
            env=env,
        )

        await process.wait()

        if process.returncode != 0:
            self.log.error(f"Aider finished with error code: {process.returncode}")
            raise Exception(f"Aider finished with error code: {process.returncode}")

        self.log.info("Aider finished successfully")

    def _configure_git_identity(self, repo_path: str):
        """Configure a dummy git user to allow Aider create commits"""
        try:
            subprocess.run(["git", "config", "user.name", "AI Agent"], cwd=repo_path, check=True)
            subprocess.run(
                ["git", "config", "user.email", "agent@bot.local"], cwd=repo_path, check=True
            )
        except subprocess.CalledProcessError as e:
            self.log.error(f"Failed to configure git: {e}")
            raise

    async def generate_code(self, issue_data: Dict[str, Any], repo_path: str):
        """
        Generate code implementation for an issue.

        Args:
            context: Full context (issue + code)
            issue_data: Issue metadata

        Returns:
            Generated code as formatted string
        """
        prompt = self._build_code_prompt(issue_data)

        self.log.info(
            "generating_code",
            msg="Requesting code from LLM",
            issue_id=issue_data.get("number"),
        )

        await self._call_aider(prompt, repo_path, allow_commits=True)

        self.log.info("code_generated", msg="LLM code received")

    def _build_code_prompt(self, issue_data: Dict[str, Any]) -> str:
        """Build prompt for code generation."""
        return f"""You are an expert software engineer. Implement a complete solution for this issue.

## Your Task

Implement a solution for issue #{issue_data.get("number")}: {issue_data.get("title")}

{issue_data.get("body")}

**Guidelines:**
- Only modify files you have seen in the context above
- Ensure code follows existing style and conventions
- Add appropriate comments where needed
- Handle edge cases
- Keep changes minimal and focused
- Make sure the code is syntactically correct
"""

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
