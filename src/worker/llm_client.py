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

    async def _call_aider(self, prompt: str, repo_path: str):
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"  # Force Python to flush logs immediately

        # Configure OpenAI-compatible endpoint pointing to Ollama
        env["OPENAI_API_KEY"] = settings.llm_api_key
        env["OPENAI_API_BASE"] = f"{settings.ollama_base_url}/v1"

        model_cmd = f"openai/{settings.llm_model}"

        self._configure_git_identity(repo_path)

        cmd = [
            "aider",
            "--model",
            model_cmd,
            "--yes",
            "--no-detect-urls",
            "--no-check-update",
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
            issue_data: Issue metadata (number, title, body)
            repo_path: Path to the repository

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

    async def refine_code(self, refine_request: str, repo_path: str):
        """
        Refine existing code based on user feedback.

        Args:
            refine_request: User's refinement request describing desired changes
            repo_path: Path to the repository

        Returns:
            None (changes are made directly to the repository)
        """
        prompt = self._build_refine_prompt(refine_request)

        self.log.info(
            "refining_code",
            msg="Requesting code refinement from LLM",
            request_preview=refine_request[:100],
        )

        await self._call_aider(prompt, repo_path)

        self.log.info("code_refined", msg="LLM refinement completed")

    def _build_code_prompt(self, issue_data: Dict[str, Any]) -> str:
        """Build prompt for code generation from an issue."""
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

    def _build_refine_prompt(self, refine_request: str) -> str:
        """Build prompt for code refinement based on user feedback."""
        return f"""You are an expert software engineer. A reviewer has requested changes to this pull request.

## Refinement Request

{refine_request}

## Your Task

Make the necessary changes to satisfy the reviewer's request. Analyze the existing code and apply the requested modifications.

**Guidelines:**
- Understand the intent behind the refinement request
- Only modify files relevant to the requested changes
- Ensure code follows existing style and conventions
- Keep changes focused on addressing the specific feedback
- Make sure the code is syntactically correct
- Preserve existing functionality unless explicitly asked to change it
"""

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
