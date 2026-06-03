from llm_memory.config import API_PROVIDER
from llm_memory.providers.base import LLMProvider


def get_provider() -> LLMProvider:
    if API_PROVIDER == "anthropic-api":
        from llm_memory.providers.anthropic_api import AnthropicAPIProvider
        return AnthropicAPIProvider()
    from llm_memory.providers.claude_agent import ClaudeAgentProvider
    return ClaudeAgentProvider()
