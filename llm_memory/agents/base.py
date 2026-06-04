"""Abstract agent adapter interface."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InstallResult:
    files_written: list[Path] = field(default_factory=list)
    manual_steps: list[str] = field(default_factory=list)


class AgentAdapter(ABC):
    key: str
    display_name: str
    supports_session_hooks: bool

    @abstractmethod
    def install(self, project_root: Path) -> InstallResult:
        """Write agent config files. Returns written paths and any manual steps."""
        ...

    @abstractmethod
    def write_context_file(self, project_root: Path, context: str) -> Path:
        """Write knowledge context to the agent's context injection location."""
        ...

    def context_file_path(self, project_root: Path) -> Path:
        """Return the path where context is injected for this agent."""
        raise NotImplementedError


class StandardHookAdapter(AgentAdapter):
    """Base for agents that share Claude Code's JSON hooks protocol.

    These agents all:
    - Accept hook commands that receive JSON on stdin
    - Provide session_id and transcript_path in that payload
    - Store transcripts as JSONL compatible with extract_conversation_context()

    Subclasses set: key, display_name, hook_event, and implement _config_file().
    Override _build_hooks_entry() for agents with non-standard config schemas.
    """

    supports_session_hooks = True
    hook_event: str = "SessionEnd"

    def _hook_command(self, project_root: Path) -> str:
        # Use the absolute lmc path + --kb-root so this works from any CWD.
        # Global hooks (Gemini, Codex, etc.) fire from the user's project dir,
        # not the KB root, so --kb-root must be explicit.
        lmc = project_root / "lmc"
        return f"{lmc} hook --kb-root {project_root} generic-session-end"

    def _config_file(self, project_root: Path) -> Path:
        raise NotImplementedError

    def _build_hooks_entry(self, project_root: Path) -> dict:
        """Return the dict to merge into the agent's config file."""
        return {
            "hooks": {
                self.hook_event: [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": self._hook_command(project_root),
                            }
                        ]
                    }
                ]
            }
        }

    def _merge(self, existing: dict, entry: dict) -> dict:
        """Merge our hook entry into an existing config dict."""
        existing.setdefault("hooks", {})[self.hook_event] = entry["hooks"][self.hook_event]
        return existing

    def install(self, project_root: Path) -> InstallResult:
        config_file = self._config_file(project_root)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        entry = self._build_hooks_entry(project_root)

        if config_file.exists():
            try:
                existing = json.loads(config_file.read_text(encoding="utf-8"))
                merged = self._merge(existing, entry)
            except (json.JSONDecodeError, OSError):
                merged = entry
        else:
            merged = entry

        config_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")

        return InstallResult(
            files_written=[config_file],
            manual_steps=[
                f"{self.display_name} will now auto-capture conversations via "
                f"{self.hook_event} hook.",
            ],
        )

    def write_context_file(self, project_root: Path, context: str) -> Path:
        # Context injection is handled automatically by the hook pipeline.
        return self._config_file(project_root)

    def context_file_path(self, project_root: Path) -> Path:
        return self._config_file(project_root)
