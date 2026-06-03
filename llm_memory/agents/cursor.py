"""Cursor agent adapter - context injection via .cursor/rules/."""

from __future__ import annotations

from pathlib import Path

from llm_memory.agents.base import AgentAdapter, InstallResult


class CursorAdapter(AgentAdapter):
    key = "cursor"
    display_name = "Cursor"
    supports_session_hooks = False

    def install(self, project_root: Path) -> InstallResult:
        rules_dir = project_root / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        return InstallResult(
            files_written=[],
            manual_steps=[
                "Run 'llm-memory-compiler inject-context' to populate .cursor/rules/llm-memory.md.",
                "Re-run inject-context periodically (or add it to a cron job) to keep context fresh.",
                "Cursor does not support session hooks; memory capture is not automatic.",
            ],
        )

    def write_context_file(self, project_root: Path, context: str) -> Path:
        target = self.context_file_path(project_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(context, encoding="utf-8")
        return target

    def context_file_path(self, project_root: Path) -> Path:
        return project_root / ".cursor" / "rules" / "llm-memory.md"
