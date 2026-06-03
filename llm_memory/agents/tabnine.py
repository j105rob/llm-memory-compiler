"""Tabnine CLI agent adapter."""

from pathlib import Path

from llm_memory.agents.base import StandardHookAdapter


class TabnineAdapter(StandardHookAdapter):
    key = "tabnine"
    display_name = "Tabnine CLI"
    hook_event = "SessionEnd"

    def _config_file(self, project_root: Path) -> Path:
        # Global user config — fires for all Tabnine CLI sessions
        return Path.home() / ".tabnine" / "agent" / "settings.json"
