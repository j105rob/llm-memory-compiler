"""Tests for agent adapter install() methods.

Adapters take an explicit project_root: Path argument, so no config module
side effects. These tests verify correct file structure and hook command content.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestClaudeCodeAdapter:
    def test_creates_settings_file(self, tmp_path):
        from llm_memory.agents.claude_code import ClaudeCodeAdapter
        ClaudeCodeAdapter().install(tmp_path)
        assert (tmp_path / ".claude" / "settings.json").exists()

    def test_all_three_hook_events_present(self, tmp_path):
        from llm_memory.agents.claude_code import ClaudeCodeAdapter
        ClaudeCodeAdapter().install(tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        hooks = settings["hooks"]
        assert "SessionStart" in hooks
        assert "SessionEnd" in hooks
        assert "PreCompact" in hooks

    def test_hook_commands_contain_kb_root(self, tmp_path):
        from llm_memory.agents.claude_code import ClaudeCodeAdapter
        ClaudeCodeAdapter().install(tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        for event, entries in settings["hooks"].items():
            cmd = entries[0]["hooks"][0]["command"]
            assert "--kb-root" in cmd, f"{event} hook missing --kb-root"
            assert str(tmp_path) in cmd, f"{event} hook has wrong --kb-root path"

    def test_merges_with_existing_settings(self, tmp_path):
        from llm_memory.agents.claude_code import ClaudeCodeAdapter
        settings_file = tmp_path / ".claude" / "settings.json"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text(json.dumps({"model": "claude-opus-4-8"}))
        ClaudeCodeAdapter().install(tmp_path)
        result = json.loads(settings_file.read_text())
        assert result["model"] == "claude-opus-4-8"
        assert "hooks" in result

    def test_idempotent_second_install(self, tmp_path):
        from llm_memory.agents.claude_code import ClaudeCodeAdapter
        adapter = ClaudeCodeAdapter()
        adapter.install(tmp_path)
        adapter.install(tmp_path)
        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        # Should not duplicate hook entries
        assert len(settings["hooks"]["SessionEnd"]) == 1


class TestCursorAdapter:
    def test_creates_hooks_file(self, tmp_path):
        from llm_memory.agents.cursor import CursorAdapter
        CursorAdapter().install(tmp_path)
        assert (tmp_path / ".cursor" / "hooks.json").exists()

    def test_version_field_set(self, tmp_path):
        from llm_memory.agents.cursor import CursorAdapter
        CursorAdapter().install(tmp_path)
        config = json.loads((tmp_path / ".cursor" / "hooks.json").read_text())
        assert config["version"] == 1

    def test_all_three_hook_events_present(self, tmp_path):
        from llm_memory.agents.cursor import CursorAdapter
        CursorAdapter().install(tmp_path)
        config = json.loads((tmp_path / ".cursor" / "hooks.json").read_text())
        assert "sessionStart" in config["hooks"]
        assert "sessionEnd" in config["hooks"]
        assert "preCompact" in config["hooks"]

    def test_hook_commands_contain_kb_root(self, tmp_path):
        from llm_memory.agents.cursor import CursorAdapter
        CursorAdapter().install(tmp_path)
        config = json.loads((tmp_path / ".cursor" / "hooks.json").read_text())
        for event, entries in config["hooks"].items():
            cmd = entries[0]["command"]
            assert "--kb-root" in cmd, f"{event} hook missing --kb-root"
            assert str(tmp_path) in cmd

    def test_removes_legacy_stop_hook(self, tmp_path):
        from llm_memory.agents.cursor import CursorAdapter
        hooks_file = tmp_path / ".cursor" / "hooks.json"
        hooks_file.parent.mkdir(parents=True)
        hooks_file.write_text(json.dumps({"version": 1, "hooks": {"stop": [{"command": "old"}]}}))
        CursorAdapter().install(tmp_path)
        config = json.loads(hooks_file.read_text())
        assert "stop" not in config["hooks"]


class TestStandardHookAdapters:
    """Gemini, Codex, Tabnine, Continue, Qwen all use StandardHookAdapter."""

    @pytest.mark.parametrize("adapter_path,expected_config_dir", [
        ("llm_memory.agents.gemini:GeminiAdapter", "~/.gemini"),
        ("llm_memory.agents.codex:CodexAdapter", "~/.codex"),
        ("llm_memory.agents.tabnine:TabnineAdapter", "~/.tabnine/agent"),
        ("llm_memory.agents.continue_dev:ContinueAdapter", "~/.continue"),
        ("llm_memory.agents.qwen:QwenAdapter", "~/.qwen"),
    ])
    def test_global_hook_command_contains_kb_root(self, tmp_path, adapter_path, expected_config_dir):
        module_path, class_name = adapter_path.split(":")
        import importlib
        mod = importlib.import_module(module_path)
        adapter = getattr(mod, class_name)()
        cmd = adapter._hook_command(tmp_path)
        assert "--kb-root" in cmd
        assert str(tmp_path) in cmd

    def test_gemini_creates_settings_file(self, tmp_path):
        from llm_memory.agents.gemini import GeminiAdapter
        result = GeminiAdapter().install(tmp_path)
        assert len(result.files_written) == 1
        config_file = result.files_written[0]
        assert config_file.exists()
        config = json.loads(config_file.read_text())
        assert "hooks" in config


class TestDevinAdapter:
    def test_creates_project_level_hooks_file(self, tmp_path):
        from llm_memory.agents.devin import DevinAdapter
        DevinAdapter().install(tmp_path)
        assert (tmp_path / ".devin" / "hooks.v1.json").exists()

    def test_no_hooks_wrapper_key(self, tmp_path):
        from llm_memory.agents.devin import DevinAdapter
        DevinAdapter().install(tmp_path)
        config = json.loads((tmp_path / ".devin" / "hooks.v1.json").read_text())
        # Devin schema: event names are top-level keys, no "hooks" wrapper
        assert "SessionEnd" in config
        assert "hooks" not in config

    def test_hook_command_contains_kb_root(self, tmp_path):
        from llm_memory.agents.devin import DevinAdapter
        adapter = DevinAdapter()
        cmd = adapter._hook_command(tmp_path)
        assert "--kb-root" in cmd
        assert str(tmp_path) in cmd
