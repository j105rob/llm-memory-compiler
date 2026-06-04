"""Tests for JSONL transcript extraction logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_memory.transcript import (
    MAX_CONTEXT_CHARS,
    MAX_TURNS,
    extract_conversation_context,
    extract_windsurf_context,
)


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")


class TestExtractConversationContext:
    def test_basic_turns(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        _write_transcript(t, [
            {"message": {"role": "user", "content": "What is Python?"}},
            {"message": {"role": "assistant", "content": "A programming language."}},
        ])
        context, count = extract_conversation_context(t)
        assert "User" in context
        assert "What is Python?" in context
        assert "programming language" in context
        assert count == 2

    def test_ignores_non_user_assistant_roles(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        _write_transcript(t, [
            {"message": {"role": "system", "content": "You are helpful."}},
            {"message": {"role": "user", "content": "Hello"}},
            {"message": {"role": "tool", "content": "tool result"}},
        ])
        context, count = extract_conversation_context(t)
        assert "Hello" in context
        assert "system" not in context.lower()
        assert "tool result" not in context
        assert count == 1

    def test_handles_list_content_blocks(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        _write_transcript(t, [
            {"message": {"role": "user", "content": [
                {"type": "text", "text": "Block one."},
                {"type": "text", "text": "Block two."},
            ]}},
        ])
        context, count = extract_conversation_context(t)
        assert "Block one" in context
        assert "Block two" in context

    def test_skips_blank_lines(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        t.write_text(
            json.dumps({"message": {"role": "user", "content": "Hi"}}) + "\n\n\n"
        )
        context, count = extract_conversation_context(t)
        assert count == 1

    def test_skips_invalid_json_lines(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        t.write_text(
            "not json\n"
            + json.dumps({"message": {"role": "user", "content": "Valid"}}) + "\n"
        )
        context, count = extract_conversation_context(t)
        assert "Valid" in context
        assert count == 1

    def test_caps_at_max_turns(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        entries = [
            {"message": {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}}
            for i in range(MAX_TURNS + 10)
        ]
        _write_transcript(t, entries)
        _, count = extract_conversation_context(t)
        assert count <= MAX_TURNS

    def test_empty_transcript(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        t.write_text("")
        context, count = extract_conversation_context(t)
        assert count == 0
        assert context == ""

    def test_flat_role_content_format(self, tmp_path):
        """Supports transcripts where role/content are at the top level (not under 'message')."""
        t = tmp_path / "transcript.jsonl"
        _write_transcript(t, [
            {"role": "user", "content": "Flat format question"},
            {"role": "assistant", "content": "Flat format answer"},
        ])
        context, count = extract_conversation_context(t)
        assert "Flat format question" in context
        assert count == 2


class TestExtractWindsurfContext:
    def test_basic_windsurf_turns(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        _write_transcript(t, [
            {"type": "user_input", "user_input": {"user_response": "How does X work?"}},
            {"type": "planner_response", "planner_response": {"response": "X works by..."}},
        ])
        context, count = extract_windsurf_context(t)
        assert "How does X work?" in context
        assert "X works by" in context
        assert count == 2

    def test_ignores_other_entry_types(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        _write_transcript(t, [
            {"type": "tool_call", "data": "irrelevant"},
            {"type": "user_input", "user_input": {"user_response": "Real question"}},
        ])
        context, count = extract_windsurf_context(t)
        assert "Real question" in context
        assert "irrelevant" not in context
        assert count == 1

    def test_skips_empty_responses(self, tmp_path):
        t = tmp_path / "transcript.jsonl"
        _write_transcript(t, [
            {"type": "user_input", "user_input": {"user_response": "   "}},
            {"type": "user_input", "user_input": {"user_response": "Real"}},
        ])
        context, count = extract_windsurf_context(t)
        assert count == 1
