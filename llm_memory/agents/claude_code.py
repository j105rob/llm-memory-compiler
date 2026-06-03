"""Claude Code agent adapter - full session hooks support."""

from __future__ import annotations

import json
from pathlib import Path

from llm_memory.agents.base import AgentAdapter, InstallResult

_SETTINGS_TEMPLATE = {
    "hooks": {
        "SessionStart": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "uv run python hooks/session-start.py",
                        "timeout": 15,
                    }
                ],
            }
        ],
        "PreCompact": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "uv run python hooks/pre-compact.py",
                        "timeout": 10,
                    }
                ],
            }
        ],
        "SessionEnd": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "uv run python hooks/session-end.py",
                        "timeout": 10,
                    }
                ],
            }
        ],
    }
}


class ClaudeCodeAdapter(AgentAdapter):
    key = "claude-code"
    display_name = "Claude Code"
    supports_session_hooks = True

    def install(self, project_root: Path) -> InstallResult:
        settings_dir = project_root / ".claude"
        settings_file = settings_dir / "settings.json"

        if settings_file.exists():
            try:
                existing = json.loads(settings_file.read_text(encoding="utf-8"))
                existing.setdefault("hooks", {}).update(_SETTINGS_TEMPLATE["hooks"])
                merged = existing
            except (json.JSONDecodeError, OSError):
                merged = _SETTINGS_TEMPLATE
        else:
            settings_dir.mkdir(parents=True, exist_ok=True)
            merged = _SETTINGS_TEMPLATE

        settings_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")

        return InstallResult(
            files_written=[settings_file],
            manual_steps=["Open this project in Claude Code to activate session hooks."],
        )

    def write_context_file(self, project_root: Path, context: str) -> Path:
        # Context injection is handled automatically via the SessionStart hook.
        # This is a no-op for Claude Code.
        return project_root / ".claude" / "settings.json"

    def context_file_path(self, project_root: Path) -> Path:
        return project_root / ".claude" / "settings.json"
