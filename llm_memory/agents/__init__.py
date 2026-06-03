from llm_memory.agents.base import AgentAdapter, InstallResult
from llm_memory.agents.claude_code import ClaudeCodeAdapter
from llm_memory.agents.copilot import CopilotAdapter
from llm_memory.agents.cursor import CursorAdapter
from llm_memory.agents.windsurf import WindsurfAdapter

REGISTRY: dict[str, type[AgentAdapter]] = {
    "claude-code": ClaudeCodeAdapter,
    "cursor": CursorAdapter,
    "windsurf": WindsurfAdapter,
    "copilot": CopilotAdapter,
}


def get_agent(key: str) -> AgentAdapter:
    if key not in REGISTRY:
        valid = ", ".join(REGISTRY)
        raise ValueError(f"Unknown agent '{key}'. Choose from: {valid}")
    return REGISTRY[key]()
