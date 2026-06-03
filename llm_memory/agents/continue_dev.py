"""Continue.dev agent adapter."""

from pathlib import Path

from llm_memory.agents.base import StandardHookAdapter


class ContinueAdapter(StandardHookAdapter):
    key = "continue"
    display_name = "Continue.dev"
    hook_event = "SessionEnd"

    def _config_file(self, project_root: Path) -> Path:
        # Global user config — fires for all Continue sessions
        return Path.home() / ".continue" / "settings.json"
