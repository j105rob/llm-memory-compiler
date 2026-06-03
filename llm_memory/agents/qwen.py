"""Qwen Code agent adapter."""

from pathlib import Path

from llm_memory.agents.base import StandardHookAdapter


class QwenAdapter(StandardHookAdapter):
    key = "qwen"
    display_name = "Qwen Code"
    hook_event = "SessionEnd"

    def _config_file(self, project_root: Path) -> Path:
        # Global user config — fires for all Qwen Code sessions
        return Path.home() / ".qwen" / "settings.json"
