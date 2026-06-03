from llm_memory.agents.base import AgentAdapter, InstallResult, StandardHookAdapter
from llm_memory.agents.claude_code import ClaudeCodeAdapter
from llm_memory.agents.codex import CodexAdapter
from llm_memory.agents.continue_dev import ContinueAdapter
from llm_memory.agents.copilot import CopilotAdapter
from llm_memory.agents.cursor import CursorAdapter
from llm_memory.agents.devin import DevinAdapter
from llm_memory.agents.gemini import GeminiAdapter
from llm_memory.agents.qwen import QwenAdapter
from llm_memory.agents.tabnine import TabnineAdapter
from llm_memory.agents.windsurf import WindsurfAdapter

REGISTRY: dict[str, type[AgentAdapter]] = {
    "claude-code": ClaudeCodeAdapter,
    "cursor":      CursorAdapter,
    "windsurf":    WindsurfAdapter,
    "gemini":      GeminiAdapter,
    "codex":       CodexAdapter,
    "tabnine":     TabnineAdapter,
    "continue":    ContinueAdapter,
    "qwen":        QwenAdapter,
    "devin":       DevinAdapter,
    "copilot":     CopilotAdapter,
}


def get_agent(key: str) -> AgentAdapter:
    if key not in REGISTRY:
        valid = ", ".join(REGISTRY)
        raise ValueError(f"Unknown agent '{key}'. Choose from: {valid}")
    return REGISTRY[key]()
