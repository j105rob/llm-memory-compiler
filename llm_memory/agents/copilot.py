"""GitHub Copilot adapter - context injection via .github/copilot-instructions.md."""

from __future__ import annotations

from pathlib import Path

from llm_memory.agents.base import AgentAdapter, InstallResult

_START_MARKER = "<!-- LLM-MEMORY START -->"
_END_MARKER = "<!-- LLM-MEMORY END -->"


class CopilotAdapter(AgentAdapter):
    key = "copilot"
    display_name = "GitHub Copilot"
    supports_session_hooks = False

    def install(self, project_root: Path) -> InstallResult:
        github_dir = project_root / ".github"
        github_dir.mkdir(parents=True, exist_ok=True)

        return InstallResult(
            files_written=[],
            manual_steps=[
                "Run 'llm-memory-compiler inject-context' to update .github/copilot-instructions.md.",
                "Re-run inject-context periodically to keep context fresh.",
                "GitHub Copilot does not support session hooks; memory capture is not automatic.",
            ],
        )

    def write_context_file(self, project_root: Path, context: str) -> Path:
        target = self.context_file_path(project_root)
        target.parent.mkdir(parents=True, exist_ok=True)

        managed_block = f"{_START_MARKER}\n{context}\n{_END_MARKER}"

        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if _START_MARKER in existing:
                # Replace existing managed section
                start = existing.index(_START_MARKER)
                end = existing.index(_END_MARKER) + len(_END_MARKER)
                updated = existing[:start] + managed_block + existing[end:]
            else:
                updated = existing.rstrip() + "\n\n" + managed_block + "\n"
        else:
            updated = managed_block + "\n"

        target.write_text(updated, encoding="utf-8")
        return target

    def context_file_path(self, project_root: Path) -> Path:
        return project_root / ".github" / "copilot-instructions.md"
