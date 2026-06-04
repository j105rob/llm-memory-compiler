"""LLM provider using the Anthropic SDK directly via ANTHROPIC_API_KEY."""

import asyncio
import os

from llm_memory.providers.base import LLMProvider

class AnthropicAPIProvider(LLMProvider):
    def __init__(self) -> None:
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Export it or switch to api_provider=claude-agent-sdk."
            )

    async def call(
        self,
        prompt: str,
        *,
        allowed_tools: list[str],
        max_turns: int,
        cwd: str,
        use_code_preset: bool = False,
    ) -> tuple[str, float]:
        if allowed_tools:
            raise RuntimeError(
                "compile and query --file-back require file tools only available via "
                "claude-agent-sdk. Set api_provider=claude-agent-sdk in your config."
            )

        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic package not installed. "
                "Run: uv add 'llm-memory-compiler[anthropic]'"
            ) from e

        def _sync_call() -> tuple[str, float]:
            from llm_memory.config import MODEL
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=MODEL,
                max_tokens=8096,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            return text, 0.0

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_call)
