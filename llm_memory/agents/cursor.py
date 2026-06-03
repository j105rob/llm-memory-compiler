"""Cursor agent adapter - full session capture via stop hook."""

from __future__ import annotations

import json
from pathlib import Path

from llm_memory.agents.base import AgentAdapter, InstallResult

_HOOKS_CONFIG = {
    "version": 1,
    "hooks": {
        "stop": [
            {
                "command": "uv run python hooks/cursor-stop.py"
            }
        ]
    },
}


class CursorAdapter(AgentAdapter):
    key = "cursor"
    display_name = "Cursor"
    supports_session_hooks = True

    def install(self, project_root: Path) -> InstallResult:
        cursor_dir = project_root / ".cursor"
        cursor_dir.mkdir(parents=True, exist_ok=True)
        hooks_file = cursor_dir / "hooks.json"

        if hooks_file.exists():
            try:
                existing = json.loads(hooks_file.read_text(encoding="utf-8"))
                existing.setdefault("hooks", {})["stop"] = _HOOKS_CONFIG["hooks"]["stop"]
                merged = existing
                merged.setdefault("version", 1)
            except (json.JSONDecodeError, OSError):
                merged = _HOOKS_CONFIG
        else:
            merged = _HOOKS_CONFIG

        hooks_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")

        return InstallResult(
            files_written=[hooks_file],
            manual_steps=["Open this project in Cursor to activate the stop hook."],
        )

    def write_context_file(self, project_root: Path, context: str) -> Path:
        # Context injection is handled automatically via the stop hook's flush pipeline.
        # write_context_file is a no-op for Cursor.
        return self.context_file_path(project_root)

    def context_file_path(self, project_root: Path) -> Path:
        return project_root / ".cursor" / "hooks.json"
