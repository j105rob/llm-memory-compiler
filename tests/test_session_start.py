"""Tests for session start context building."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from llm_memory.session_start import build_context


@pytest.fixture
def dirs(tmp_path):
    knowledge = tmp_path / "knowledge"
    daily = tmp_path / "daily"
    knowledge.mkdir()
    daily.mkdir()
    return knowledge, daily


class TestBuildContext:
    def test_includes_today_date(self, dirs):
        knowledge, daily = dirs
        context = build_context(knowledge, daily)
        today = datetime.now(timezone.utc).astimezone()
        assert today.strftime("%Y") in context

    def test_empty_kb_placeholder(self, dirs):
        knowledge, daily = dirs
        context = build_context(knowledge, daily)
        assert "empty" in context.lower()
        assert "no articles" in context.lower()

    def test_shows_index_when_present(self, dirs):
        knowledge, daily = dirs
        (knowledge / "index.md").write_text("| [[python-tips]] | Python tips | 2026-06-04 |")
        context = build_context(knowledge, daily)
        assert "python-tips" in context

    def test_shows_recent_daily_log(self, dirs):
        knowledge, daily = dirs
        today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
        (daily / f"{today}.md").write_text("# Daily Log\n\n## Sessions\n\n- Worked on tests")
        context = build_context(knowledge, daily)
        assert "Worked on tests" in context

    def test_no_log_shows_placeholder(self, dirs):
        knowledge, daily = dirs
        context = build_context(knowledge, daily)
        assert "no recent daily log" in context.lower()

    def test_context_has_three_sections(self, dirs):
        knowledge, daily = dirs
        context = build_context(knowledge, daily)
        assert "## Today" in context
        assert "## Knowledge Base Index" in context
        assert "## Recent Daily Log" in context

    def test_context_within_char_limit(self, dirs):
        from llm_memory.session_start import MAX_CONTEXT_CHARS
        knowledge, daily = dirs
        # Write an enormous index and log
        (knowledge / "index.md").write_text("x" * 30_000)
        today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
        (daily / f"{today}.md").write_text("y" * 30_000)
        context = build_context(knowledge, daily)
        assert len(context) <= MAX_CONTEXT_CHARS + 20  # small slack for truncation suffix

    def test_log_capped_at_max_lines(self, dirs):
        from llm_memory.session_start import MAX_LOG_LINES
        knowledge, daily = dirs
        today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
        (daily / f"{today}.md").write_text("\n".join(f"line {i}" for i in range(MAX_LOG_LINES + 50)))
        context = build_context(knowledge, daily)
        # The last line should be present but not the first (it was trimmed)
        assert f"line {MAX_LOG_LINES + 49}" in context
        assert "line 0" not in context
