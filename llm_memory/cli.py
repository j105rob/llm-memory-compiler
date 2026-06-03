"""CLI entry point for llm-memory-compiler."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import click


# ── Helpers ───────────────────────────────────────────────────────────

def _write_config(project_root: Path, data: dict) -> Path:
    config_dir = project_root / ".llm-memory"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return config_file


def _migrate_state(project_root: Path) -> None:
    """Copy scripts/state.json to .llm-memory/state.json if migrating."""
    old_state = project_root / "scripts" / "state.json"
    new_state = project_root / ".llm-memory" / "state.json"
    if old_state.exists() and not new_state.exists():
        shutil.copy2(old_state, new_state)
        click.echo(f"  Migrated state: scripts/state.json → .llm-memory/state.json")


# ── CLI group ─────────────────────────────────────────────────────────

@click.group()
def main() -> None:
    """LLM Memory Compiler — agent-agnostic personal knowledge base."""
    pass


# ── init ──────────────────────────────────────────────────────────────

_AGENTS = {
    "1":  ("claude-code", "Claude Code",    "session hooks (SessionEnd, PreCompact)"),
    "2":  ("cursor",      "Cursor",         "session hooks (stop event)"),
    "3":  ("windsurf",    "Windsurf",       "session hooks (post_cascade_response_with_transcript)"),
    "4":  ("gemini",      "Gemini CLI",     "session hooks (SessionEnd)"),
    "5":  ("codex",       "OpenAI Codex",   "session hooks (Stop)"),
    "6":  ("tabnine",     "Tabnine CLI",    "session hooks (SessionEnd)"),
    "7":  ("continue",    "Continue.dev",   "session hooks (SessionEnd)"),
    "8":  ("qwen",        "Qwen Code",      "session hooks (SessionEnd)"),
    "9":  ("devin",       "Devin CLI",      "session hooks (SessionEnd)"),
    "10": ("copilot",     "GitHub Copilot", "context injection only (no session hooks)"),
}

_PROVIDERS = {
    "1": ("claude-agent-sdk", "uses ~/.claude/.credentials.json"),
    "2": ("anthropic-api",    "uses ANTHROPIC_API_KEY env var"),
}


@main.command()
@click.option("--agent", type=click.Choice([a[0] for a in _AGENTS.values()]), default=None,
              help="Skip interactive agent selection.")
@click.option("--provider", type=click.Choice([p[0] for p in _PROVIDERS.values()]), default=None,
              help="Skip interactive provider selection.")
@click.option("--knowledge-dir", default=None, help="Knowledge base directory (default: knowledge)")
@click.option("--daily-dir", default=None, help="Daily logs directory (default: daily)")
def init(agent: str | None, provider: str | None, knowledge_dir: str | None, daily_dir: str | None) -> None:
    """Interactive setup wizard. Installs hooks for the chosen AI agent."""
    project_root = Path.cwd()
    is_tty = sys.stdin.isatty()

    # Detect existing setup for migration messaging
    existing_config = project_root / ".llm-memory" / "config.json"
    if existing_config.exists():
        click.echo("Existing config detected — reconfiguring.")

    # ── Agent selection ──
    if agent is None:
        if is_tty:
            click.echo("\nSelect your AI coding agent:")
            for num, (key, name, desc) in _AGENTS.items():
                click.echo(f"  {num}. {name:16} [{desc}]")
            choice = click.prompt("Agent", default="1")
            agent_entry = _AGENTS.get(choice)
            if agent_entry is None:
                raise click.BadParameter(f"Choose 1-{len(_AGENTS)}")
            agent = agent_entry[0]
        else:
            agent = "claude-code"

    # ── Provider selection ──
    if provider is None:
        if is_tty:
            click.echo("\nSelect LLM provider for compile/query/flush:")
            for num, (key, desc) in _PROVIDERS.items():
                click.echo(f"  {num}. {key:20} [{desc}]")
            choice = click.prompt("Provider", default="1")
            provider_entry = _PROVIDERS.get(choice)
            if provider_entry is None:
                raise click.BadParameter(f"Choose 1-{len(_PROVIDERS)}")
            provider = provider_entry[0]
        else:
            provider = "claude-agent-sdk"

    # ── Directories ──
    if knowledge_dir is None and is_tty:
        knowledge_dir = click.prompt("Knowledge directory", default="knowledge")
    if daily_dir is None and is_tty:
        daily_dir = click.prompt("Daily log directory", default="daily")

    knowledge_dir = knowledge_dir or "knowledge"
    daily_dir = daily_dir or "daily"

    # ── Write config ──
    config_data = {
        "agent": agent,
        "api_provider": provider,
        "knowledge_dir": knowledge_dir,
        "daily_dir": daily_dir,
    }
    config_file = _write_config(project_root, config_data)
    click.echo(f"\n  Wrote {config_file.relative_to(project_root)}")

    # Migrate existing state if present
    _migrate_state(project_root)

    # ── Install agent hooks/config ──
    from llm_memory.agents import get_agent
    adapter = get_agent(agent)
    result = adapter.install(project_root)

    for f in result.files_written:
        try:
            label = f.relative_to(project_root)
        except ValueError:
            label = f  # outside project root (e.g. global ~/.codeium/ config)
        click.echo(f"  Wrote {label}")

    # ── Sync dependencies ──
    import subprocess
    try:
        subprocess.run(["uv", "sync"], cwd=str(project_root), check=True, capture_output=True)
        click.echo("  Ran uv sync")
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo("  Note: run 'uv sync' to install dependencies")

    click.echo("\nSetup complete.")
    for step in result.manual_steps:
        click.echo(f"  • {step}")


# ── compile ───────────────────────────────────────────────────────────

@main.command()
@click.option("--all", "force_all", is_flag=True, help="Force recompile all logs.")
@click.option("--file", "target_file", default=None, help="Compile a specific daily log.")
@click.option("--dry-run", is_flag=True, help="Show what would be compiled without running.")
def compile(force_all: bool, target_file: str | None, dry_run: bool) -> None:
    """Compile daily logs into knowledge articles."""
    import sys as _sys
    argv_backup = _sys.argv
    args = ["compile"]
    if force_all:
        args.append("--all")
    if target_file:
        args.extend(["--file", target_file])
    if dry_run:
        args.append("--dry-run")
    _sys.argv = args

    from llm_memory.compile import main as _main
    try:
        _main()
    finally:
        _sys.argv = argv_backup


# ── query ─────────────────────────────────────────────────────────────

@main.command()
@click.argument("question")
@click.option("--file-back", is_flag=True, help="File the answer as a Q&A article.")
def query(question: str, file_back: bool) -> None:
    """Query the knowledge base."""
    import sys as _sys
    argv_backup = _sys.argv
    args = ["query", question]
    if file_back:
        args.append("--file-back")
    _sys.argv = args

    from llm_memory.query import main as _main
    try:
        _main()
    finally:
        _sys.argv = argv_backup


# ── lint ──────────────────────────────────────────────────────────────

@main.command()
@click.option("--structural-only", is_flag=True, help="Skip LLM checks (free, faster).")
def lint(structural_only: bool) -> None:
    """Run health checks on the knowledge base."""
    import sys as _sys
    argv_backup = _sys.argv
    args = ["lint"]
    if structural_only:
        args.append("--structural-only")
    _sys.argv = args

    from llm_memory.lint import main as _main
    try:
        raise SystemExit(_main())
    finally:
        _sys.argv = argv_backup


# ── flush ─────────────────────────────────────────────────────────────

@main.command()
@click.argument("context_file")
@click.argument("session_id")
def flush(context_file: str, session_id: str) -> None:
    """Extract and save knowledge from a conversation context file."""
    import sys as _sys
    argv_backup = _sys.argv
    _sys.argv = ["flush", context_file, session_id]

    from llm_memory.flush import main as _main
    try:
        _main()
    finally:
        _sys.argv = argv_backup


# ── inject-context ────────────────────────────────────────────────────

@main.command("inject-context")
def inject_context() -> None:
    """Write the knowledge index to the configured agent's context file."""
    from llm_memory.config import CONFIGURED_AGENT, DAILY_DIR, KNOWLEDGE_DIR
    from llm_memory.session_start import build_context
    from llm_memory.agents import get_agent

    project_root = Path.cwd()
    context = build_context(KNOWLEDGE_DIR, DAILY_DIR)

    try:
        adapter = get_agent(CONFIGURED_AGENT)
    except ValueError as e:
        raise click.ClickException(str(e))

    if adapter.supports_session_hooks:
        click.echo(
            f"{adapter.display_name} uses session hooks for context injection — "
            "inject-context is not needed."
        )
        return

    target = adapter.write_context_file(project_root, context)
    rel = target.relative_to(project_root) if target.is_absolute() else target
    click.echo(f"Injected {len(context):,} chars → {rel}")


if __name__ == "__main__":
    main()
