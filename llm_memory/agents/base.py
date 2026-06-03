"""Abstract agent adapter interface."""

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
