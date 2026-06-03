"""Gemini CLI agent adapter."""

from pathlib import Path

from llm_memory.agents.base import StandardHookAdapter


class GeminiAdapter(StandardHookAdapter):
    key = "gemini"
    display_name = "Gemini CLI"
    hook_event = "SessionEnd"

    def _config_file(self, project_root: Path) -> Path:
        # Global user config — fires for all Gemini CLI sessions
        return Path.home() / ".gemini" / "settings.json"
