"""Devin CLI agent adapter.

Devin CLI uses a different config schema: hooks.v1.json is a standalone file
where the top-level keys ARE the event names (no "hooks" wrapper).
"""

from __future__ import annotations

import json
from pathlib import Path

from llm_memory.agents.base import StandardHookAdapter, InstallResult


class DevinAdapter(StandardHookAdapter):
    key = "devin"
    display_name = "Devin CLI"
    hook_event = "SessionEnd"

    def _config_file(self, project_root: Path) -> Path:
        # Project-level config inside the knowledge base directory
        return project_root / ".devin" / "hooks.v1.json"

    def _hook_command(self, project_root: Path) -> str:
        return f"lmc hook --kb-root {project_root} generic-session-end"

    def _build_hooks_entry(self, project_root: Path) -> dict:
        # Devin's hooks.v1.json has NO "hooks" wrapper — event names are top-level
        return {
            self.hook_event: [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": self._hook_command(project_root),
                            "timeout": 30,
                        }
                    ]
                }
            ]
        }

    def _merge(self, existing: dict, entry: dict) -> dict:
        existing[self.hook_event] = entry[self.hook_event]
        return existing
