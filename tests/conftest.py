"""Shared fixtures for lmc tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent


def run_lmc(args: list[str], kb_root: Path, lmc_home: Path | None = None) -> subprocess.CompletedProcess:
    """Run lmc in an isolated environment with the given KB root.

    Uses 'uv run lmc' directly so tests work without a globally installed lmc binary.
    LMC_KB_ROOT tells config.py which directory to treat as the KB root.
    """
    env = {
        **os.environ,
        "LMC_KB_ROOT": str(kb_root),
    }
    if lmc_home is not None:
        env["HOME"] = str(lmc_home)
    return subprocess.run(
        ["uv", "run", "--directory", str(REPO_ROOT), "lmc", *args],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def kb(tmp_path):
    """Empty KB root directory."""
    return tmp_path / "kb"


@pytest.fixture
def lmc_home(tmp_path):
    """Fake HOME with ~/.lmc/templates pre-seeded from the real repo."""
    home = tmp_path / "home"
    templates = home / ".lmc" / "templates"
    templates.mkdir(parents=True)
    for fname in ("AGENTS.md", "README.md"):
        src = REPO_ROOT / fname
        if src.exists():
            import shutil
            shutil.copy2(src, templates / fname)
    return home


@pytest.fixture
def initialized_kb(tmp_path, lmc_home):
    """KB that has been through lmc init (claude-code agent)."""
    kb = tmp_path / "kb"
    kb.mkdir()
    result = run_lmc(
        ["init", "--agent", "claude-code", "--provider", "claude-agent-sdk"],
        kb_root=kb,
        lmc_home=lmc_home,
    )
    assert result.returncode == 0, result.stderr
    return kb
