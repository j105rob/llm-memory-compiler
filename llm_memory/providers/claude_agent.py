"""LLM provider wrapping the claude-agent-sdk."""

from llm_memory.providers.base import LLMProvider


class ClaudeAgentProvider(LLMProvider):
    async def call(
        self,
        prompt: str,
        *,
        allowed_tools: list[str],
        max_turns: int,
        cwd: str,
        use_code_preset: bool = False,
    ) -> tuple[str, float]:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            TextBlock,
            query,
        )

        from llm_memory.config import MODEL
        opts: dict = {"cwd": cwd, "allowed_tools": allowed_tools, "max_turns": max_turns, "model": MODEL}
        if use_code_preset:
            opts["system_prompt"] = {"type": "preset", "preset": "claude_code"}
            opts["permission_mode"] = "acceptEdits"

        text = ""
        cost = 0.0

        async for message in query(prompt=prompt, options=ClaudeAgentOptions(**opts)):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text += block.text
            elif isinstance(message, ResultMessage):
                cost = message.total_cost_usd or 0.0

        return text, cost
