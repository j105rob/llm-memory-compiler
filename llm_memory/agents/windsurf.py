"""Windsurf agent adapter - session capture via post_cascade_response_with_transcript hook."""

from __future__ import annotations

import json
from pathlib import Path

from llm_memory.agents.base import AgentAdapter, InstallResult


class WindsurfAdapter(AgentAdapter):
    key = "windsurf"
    display_name = "Windsurf"
    supports_session_hooks = True

    def install(self, project_root: Path) -> InstallResult:
        # Windsurf hooks are configured globally at ~/.codeium/windsurf/hooks.json.
        # The working_directory field points to the knowledge base root so that
        # Path.cwd() resolves correctly when the hook script runs.
        hooks_dir = Path.home() / ".codeium" / "windsurf"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hooks_file = hooks_dir / "hooks.json"

        hook_entry = {
            "command": "uv run python hooks/windsurf-hook.py",
            "working_directory": str(project_root),
        }

        if hooks_file.exists():
            try:
                existing = json.loads(hooks_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = {"hooks": {}}
        else:
            existing = {"hooks": {}}

        existing.setdefault("hooks", {})["post_cascade_response_with_transcript"] = [hook_entry]
        hooks_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        return InstallResult(
            files_written=[hooks_file],
            manual_steps=[
                "Windsurf will now capture conversations via post_cascade_response_with_transcript hook.",
                "The hook fires after each response (not just session end); dedup prevents duplicate flushes.",
            ],
        )

    def write_context_file(self, project_root: Path, context: str) -> Path:
        # Windsurf also supports .windsurf/rules/ for context injection as a fallback.
        target = self.context_file_path(project_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(context, encoding="utf-8")
        return target

    def context_file_path(self, project_root: Path) -> Path:
        return project_root / ".windsurf" / "rules" / "llm-memory.md"
