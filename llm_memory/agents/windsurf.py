"""Windsurf agent adapter - context injection via .windsurf/rules/."""

from __future__ import annotations

from pathlib import Path

from llm_memory.agents.base import AgentAdapter, InstallResult


class WindsurfAdapter(AgentAdapter):
    key = "windsurf"
    display_name = "Windsurf"
    supports_session_hooks = False

    def install(self, project_root: Path) -> InstallResult:
        rules_dir = project_root / ".windsurf" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        return InstallResult(
            files_written=[],
            manual_steps=[
                "Run 'llm-memory-compiler inject-context' to populate .windsurf/rules/llm-memory.md.",
                "Re-run inject-context periodically (or add it to a cron job) to keep context fresh.",
                "Windsurf does not support session hooks; memory capture is not automatic.",
            ],
        )

    def write_context_file(self, project_root: Path, context: str) -> Path:
        target = self.context_file_path(project_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(context, encoding="utf-8")
        return target

    def context_file_path(self, project_root: Path) -> Path:
        return project_root / ".windsurf" / "rules" / "llm-memory.md"
