"""LLM client for code generation using Ollama."""

from typing import Optional, Dict, Any
import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class LLMClient:
    """Client for interacting with LLM providers (Ollama)."""
    
    def __init__(
        self,
        provider: str = "ollama",
        model: str = "codellama",
        base_url: Optional[str] = None
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
        
        # HTTP client with timeouts
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0),
            follow_redirects=True
        )
    
    async def generate_plan(
        self,
        context: str,
        issue_data: Dict[str, Any]
    ) -> str:
        """
        Generate implementation plan for an issue.
        
        Args:
            context: Full context (issue + code)
            issue_data: Issue metadata
            
        Returns:
            Generated plan as markdown
        """
        prompt = self._build_plan_prompt(context, issue_data)
        
        self.log.info(
            "generating_plan",
            msg="Requesting plan from LLM",
            issue_id=issue_data.get('number')
        )
        
        response = await self._call_ollama(prompt)
        
        self.log.info("plan_generated", msg="LLM plan received")
        return response
    
    async def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama API.
        
        Args:
            prompt: Prompt text
            
        Returns:
            Generated response
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("response", "")
            
        except httpx.HTTPError as e:
            self.log.error("ollama_error", msg="Ollama API error", error=str(e))
            raise
    
    def _build_plan_prompt(
        self,
        context: str,
        issue_data: Dict[str, Any]
    ) -> str:
        """Build prompt for plan generation."""
        return f"""You are an expert software engineer. Analyze the following issue and codebase, then create a detailed implementation plan.

{context}

## Your Task

Create a detailed implementation plan for issue #{issue_data.get('number')}: {issue_data.get('title')}

Your plan should include:
1. **Summary**: Brief overview of what needs to be done
2. **Files to Modify**: List of files that need changes
3. **Implementation Steps**: Step-by-step approach
4. **Potential Risks**: Any concerns or edge cases
5. **Testing Strategy**: How to verify the changes work

Format your response as clear, structured markdown.
Be specific and actionable. Only propose changes to files you have seen in the context.

## Implementation Plan
"""
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

