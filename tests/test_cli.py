"""Integration tests for lmc CLI commands.

These tests invoke `lmc` via subprocess with LMC_KB_ROOT set, so each
test gets a genuinely isolated environment with a fresh config import.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.conftest import run_lmc


class TestInit:
    def test_exit_code_zero(self, tmp_path, lmc_home):
        kb = tmp_path / "kb"
        kb.mkdir()
        result = run_lmc(
            ["init", "--agent", "claude-code", "--provider", "claude-agent-sdk"],
            kb_root=kb,
            lmc_home=lmc_home,
        )
        assert result.returncode == 0, result.stderr

    def test_creates_config_file(self, initialized_kb):
        config_file = initialized_kb / ".llm-memory" / "config.json"
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        assert config["agent"] == "claude-code"
        assert config["api_provider"] == "claude-agent-sdk"

    def test_config_uses_llm_memory_prefix(self, initialized_kb):
        config = json.loads((initialized_kb / ".llm-memory" / "config.json").read_text())
        assert config["knowledge_dir"].startswith("llm-memory/")
        assert config["daily_dir"].startswith("llm-memory/")

    def test_creates_daily_directory(self, initialized_kb):
        assert (initialized_kb / "llm-memory" / "daily").is_dir()

    def test_creates_knowledge_subdirs(self, initialized_kb):
        base = initialized_kb / "llm-memory" / "knowledge"
        assert (base / "concepts").is_dir()
        assert (base / "connections").is_dir()
        assert (base / "qa").is_dir()

    def test_copies_agents_md(self, initialized_kb):
        agents_file = initialized_kb / "llm-memory" / "AGENTS.md"
        assert agents_file.exists()
        assert agents_file.stat().st_size > 0

    def test_copies_readme_md(self, initialized_kb):
        assert (initialized_kb / "llm-memory" / "README.md").exists()

    def test_creates_agent_hook_config(self, initialized_kb):
        assert (initialized_kb / ".claude" / "settings.json").exists()

    def test_hook_config_has_correct_kb_root(self, initialized_kb):
        settings = json.loads((initialized_kb / ".claude" / "settings.json").read_text())
        for event in ("SessionStart", "SessionEnd", "PreCompact"):
            cmd = settings["hooks"][event][0]["hooks"][0]["command"]
            assert str(initialized_kb) in cmd, f"{event} hook has wrong KB root"

    def test_output_shows_absolute_paths(self, tmp_path, lmc_home):
        kb = tmp_path / "kb"
        kb.mkdir()
        result = run_lmc(
            ["init", "--agent", "claude-code", "--provider", "claude-agent-sdk"],
            kb_root=kb,
            lmc_home=lmc_home,
        )
        assert str(kb) in result.stdout, "Output should show absolute paths"

    def test_idempotent_reinit(self, initialized_kb, lmc_home):
        result = run_lmc(
            ["init", "--agent", "claude-code", "--provider", "claude-agent-sdk"],
            kb_root=initialized_kb,
            lmc_home=lmc_home,
        )
        assert result.returncode == 0

    def test_cursor_agent_creates_cursor_hooks(self, tmp_path, lmc_home):
        kb = tmp_path / "kb"
        kb.mkdir()
        run_lmc(
            ["init", "--agent", "cursor", "--provider", "claude-agent-sdk"],
            kb_root=kb,
            lmc_home=lmc_home,
        )
        hooks_file = kb / ".cursor" / "hooks.json"
        assert hooks_file.exists()
        config = json.loads(hooks_file.read_text())
        assert "sessionStart" in config["hooks"]
        assert "sessionEnd" in config["hooks"]
        assert "preCompact" in config["hooks"]


class TestHookSessionStart:
    """lmc hook --kb-root X session-start should return valid JSON context."""

    def test_returns_json(self, initialized_kb):
        result = run_lmc(
            ["hook", "--kb-root", str(initialized_kb), "session-start"],
            kb_root=initialized_kb,
        )
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert isinstance(output, dict)

    def test_output_has_additional_context_key(self, initialized_kb):
        # Claude Code format: hookSpecificOutput.additionalContext
        result = run_lmc(
            ["hook", "--kb-root", str(initialized_kb), "session-start"],
            kb_root=initialized_kb,
        )
        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_context_contains_today_section(self, initialized_kb):
        result = run_lmc(
            ["hook", "--kb-root", str(initialized_kb), "session-start"],
            kb_root=initialized_kb,
        )
        ctx = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "Today" in ctx

    def test_context_contains_kb_index_section(self, initialized_kb):
        result = run_lmc(
            ["hook", "--kb-root", str(initialized_kb), "session-start"],
            kb_root=initialized_kb,
        )
        ctx = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "Knowledge Base Index" in ctx

    def test_kb_root_respected(self, tmp_path, lmc_home):
        """Two separate KBs should return independent context."""
        kb_a = tmp_path / "kb_a"
        kb_b = tmp_path / "kb_b"
        for kb in (kb_a, kb_b):
            kb.mkdir()
            run_lmc(
                ["init", "--agent", "claude-code", "--provider", "claude-agent-sdk"],
                kb_root=kb, lmc_home=lmc_home,
            )

        import datetime
        today = datetime.date.today().isoformat()
        (kb_a / "llm-memory" / "daily" / f"{today}.md").write_text("KB-A unique content")

        result_a = run_lmc(["hook", "--kb-root", str(kb_a), "session-start"], kb_root=kb_a)
        result_b = run_lmc(["hook", "--kb-root", str(kb_b), "session-start"], kb_root=kb_b)

        ctx_a = json.loads(result_a.stdout)["hookSpecificOutput"]["additionalContext"]
        ctx_b = json.loads(result_b.stdout)["hookSpecificOutput"]["additionalContext"]

        assert "KB-A unique content" in ctx_a
        assert "KB-A unique content" not in ctx_b


class TestHookCursorSessionStart:
    """Cursor sessionStart uses a different output schema."""

    def test_returns_additional_context_at_top_level(self, tmp_path, lmc_home):
        kb = tmp_path / "kb"
        kb.mkdir()
        run_lmc(
            ["init", "--agent", "cursor", "--provider", "claude-agent-sdk"],
            kb_root=kb, lmc_home=lmc_home,
        )
        result = run_lmc(
            ["hook", "--kb-root", str(kb), "cursor-session-start"],
            kb_root=kb,
        )
        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        # Cursor format: {"additional_context": "..."}  (top-level, snake_case)
        assert "additional_context" in output
        assert "hookSpecificOutput" not in output
