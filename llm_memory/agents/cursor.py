"""Cursor agent adapter - full session lifecycle hooks.

Cursor supports the same three hook points as Claude Code:
  sessionStart  → inject knowledge context (returns additional_context)
  sessionEnd    → capture transcript when session ends
  preCompact    → capture transcript before context compaction

Note: Cursor's sessionStart output format differs from Claude Code's.
  Cursor:      { "additional_context": "..." }
  Claude Code: { "hookSpecificOutput": { "hookEventName": "...", "additionalContext": "..." } }
"""

from __future__ import annotations

import json
from pathlib import Path

from llm_memory.agents.base import AgentAdapter, InstallResult

def _hooks_for(kb_root: Path) -> dict:
    r = str(kb_root)
    return {
        "sessionStart": [{"command": f"lmc hook --kb-root {r} cursor-session-start", "timeout": 15}],
        "sessionEnd":   [{"command": f"lmc hook --kb-root {r} cursor-session-end",   "timeout": 10}],
        "preCompact":   [{"command": f"lmc hook --kb-root {r} cursor-pre-compact",   "timeout": 10}],
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
                config = json.loads(hooks_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                config = {}
        else:
            config = {}

        config["version"] = 1
        config.setdefault("hooks", {}).update(_hooks_for(project_root))
        # Remove the old stop hook if present from a previous install
        config["hooks"].pop("stop", None)

        hooks_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

        return InstallResult(
            files_written=[hooks_file],
            manual_steps=["Open this project in Cursor to activate sessionStart, sessionEnd, and preCompact hooks."],
        )

    def write_context_file(self, project_root: Path, context: str) -> Path:
        return self.context_file_path(project_root)

    def context_file_path(self, project_root: Path) -> Path:
        return project_root / ".cursor" / "hooks.json"
