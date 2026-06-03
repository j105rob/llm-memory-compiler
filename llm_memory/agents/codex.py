"""OpenAI Codex CLI agent adapter."""

from pathlib import Path

from llm_memory.agents.base import StandardHookAdapter


class CodexAdapter(StandardHookAdapter):
    key = "codex"
    display_name = "OpenAI Codex"
    # Codex uses "Stop" rather than "SessionEnd"
    hook_event = "Stop"

    def _config_file(self, project_root: Path) -> Path:
        # Global user config — fires for all Codex sessions
        return Path.home() / ".codex" / "hooks.json"
