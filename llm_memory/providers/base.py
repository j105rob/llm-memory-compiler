"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def call(
        self,
        prompt: str,
        *,
        allowed_tools: list[str],
        max_turns: int,
        cwd: str,
        use_code_preset: bool = False,
    ) -> tuple[str, float]:
        """Run the LLM. Returns (response_text, cost_usd).

        For compile/query with file tools, the LLM writes files directly and
        response_text may be empty; cost_usd is the total API cost.
        """
        ...
