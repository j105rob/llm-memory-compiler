"""CLI entry point for llm-memory-compiler."""

from __future__ import annotations

import json
import shutil
import sys
from importlib.metadata import version as _pkg_version
from pathlib import Path

import click
from rich.align import Align
from rich.console import Console
from rich.rule import Rule
from rich.text import Text

_console = Console()

# Block-letter ASCII art for "LMC" (L · M · C)
_BANNER_LINES = [
    "██╗     ███╗   ███╗  ██████╗",
    "██║     ████╗ ████║ ██╔════╝",
    "██║     ██╔████╔██║ ██║     ",
    "██║     ██║╚██╔╝██║ ██║     ",
    "███████╗██║ ╚═╝ ██║ ╚██████╗",
    "╚══════╝╚═╝     ╚═╝  ╚═════╝",
]

# Purple → blue → cyan gradient, mirrored top-to-bottom
_GRADIENT = [
    "bold bright_magenta",
    "bold magenta",
    "bold bright_blue",
    "bold bright_blue",
    "bold cyan",
    "bold bright_cyan",
]


def _print_banner() -> None:
    try:
        ver = _pkg_version("llm-memory-compiler")
    except Exception:
        ver = "0.2.0"

    _console.print()
    for line, style in zip(_BANNER_LINES, _GRADIENT):
        _console.print(Align.center(Text(line, style=style)))
    _console.print()
    title = Text.assemble(
        ("LLM Memory Compiler", "bold white"),
        ("  ·  ", "dim"),
        (f"v{ver}", "dim cyan"),
    )
    _console.print(Align.center(title))
    _console.print(Align.center(Text("Your AI conversations, compiled.", style="italic dim")))
    _console.print()
    _console.print(Rule(style="dim"))
    _console.print()


# ── Helpers ───────────────────────────────────────────────────────────

def _write_lmc_script(project_root: Path, bin_dir: Path) -> Path:
    """Write the lmc launcher script into bin_dir. Returns the script path."""
    import stat

    bin_dir.mkdir(parents=True, exist_ok=True)
    lmc_script = bin_dir / "lmc"
    lmc_script.write_text(
        f"#!/usr/bin/env bash\n"
        f"# lmc — LLM Memory Compiler\n"
        f"# LMC_KB_ROOT captures the caller's cwd so commands run in the right directory.\n"
        f"export LMC_KB_ROOT=\"${{LMC_KB_ROOT:-$(pwd)}}\"\n"
        f"exec uv run --directory {project_root} lmc \"$@\"\n",
        encoding="utf-8",
    )
    lmc_script.chmod(lmc_script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return lmc_script


def _bin_dir_on_path(bin_dir: Path) -> bool:
    import os
    return str(bin_dir) in os.environ.get("PATH", "").split(os.pathsep)


def _kb_root() -> Path:
    """Return the knowledge base root: LMC_KB_ROOT env var if set, else cwd."""
    import os
    r = os.environ.get("LMC_KB_ROOT")
    return Path(r).resolve() if r else Path.cwd()


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
        _console.print("  [green]✓[/green] Migrated state: scripts/state.json → .llm-memory/state.json")


# ── CLI group ─────────────────────────────────────────────────────────

@click.group()
def main() -> None:
    """LLM Memory Compiler — agent-agnostic personal knowledge base."""
    pass


# ── install ───────────────────────────────────────────────────────────

@main.command()
@click.option(
    "--bin-dir",
    default=None,
    help="Directory to install lmc into (default: ~/.local/bin).",
)
def install(bin_dir: str | None) -> None:
    """Install lmc globally so it's available from any directory.

    Run this once after cloning the repository. It writes a small launcher
    script into your PATH, then use `lmc init` to configure each project.
    """
    import shutil
    import subprocess

    project_root = Path.cwd()
    is_tty = sys.stdin.isatty()

    if is_tty:
        _print_banner()

    _console.print("[bold]Installing LMC — LLM Memory Compiler[/bold]")
    _console.print()

    # ── Verify uv is available ──
    uv_path = shutil.which("uv")
    if not uv_path:
        _console.print(
            "  [red]✗[/red] uv not found — install it from [cyan]https://docs.astral.sh/uv/[/cyan]"
        )
        raise SystemExit(1)
    _console.print(f"  [green]✓[/green] uv found at [dim]{uv_path}[/dim]")

    # ── Sync dependencies ──
    try:
        subprocess.run(["uv", "sync"], cwd=str(project_root), check=True, capture_output=True)
        _console.print("  [green]✓[/green] Dependencies synced")
    except subprocess.CalledProcessError:
        _console.print("  [yellow]![/yellow] uv sync failed — run it manually before continuing")

    # ── Resolve install directory ──
    if bin_dir:
        target_dir = Path(bin_dir).expanduser()
    elif is_tty:
        default = str(Path.home() / ".local" / "bin")
        entered = click.prompt("\nInstall lmc to", default=default)
        target_dir = Path(entered).expanduser()
    else:
        target_dir = Path.home() / ".local" / "bin"

    # ── Write the launcher script ──
    lmc_script = _write_lmc_script(project_root, target_dir)
    _console.print(f"  [green]✓[/green] Wrote [cyan]{lmc_script}[/cyan]")

    # ── Create ~/.lmc home directory and cache templates ──
    from llm_memory.config import LMC_HOME
    import datetime as _dt
    LMC_HOME.mkdir(parents=True, exist_ok=True)
    receipt = {
        "version": "0.2.0",
        "installed_from": str(project_root),
        "installed_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }
    (LMC_HOME / "install.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    _console.print(f"  [green]✓[/green] Created [cyan]{LMC_HOME}[/cyan]")

    templates_dir = LMC_HOME / "templates"
    templates_dir.mkdir(exist_ok=True)
    for fname in ("AGENTS.md", "README.md"):
        src = project_root / fname
        if src.exists():
            shutil.copy2(src, templates_dir / fname)
    _console.print(f"  [green]✓[/green] Cached templates → [cyan]{templates_dir}[/cyan]")

    # ── PATH check ──
    if not _bin_dir_on_path(target_dir):
        _console.print(
            f"\n  [yellow]![/yellow] [cyan]{target_dir}[/cyan] is not on your PATH.\n"
            f"        Add this to your shell profile ([dim]~/.bashrc[/dim], [dim]~/.zshrc[/dim], etc.):\n"
            f"        [dim]export PATH=\"{target_dir}:$PATH\"[/dim]"
        )
    else:
        _console.print(f"  [green]✓[/green] [cyan]{target_dir}[/cyan] is on your PATH")

    _console.print()
    _console.print(Rule(style="dim"))
    _console.print()
    _console.print(Align.center(Text("Installation complete!", style="bold green")))
    _console.print()
    _console.print(
        "  Next: run [bold cyan]lmc init[/bold cyan] from your knowledge base directory\n"
        "        to configure agent hooks and select your LLM provider."
    )
    _console.print()


# ── init ──────────────────────────────────────────────────────────────

_AGENTS = {
    "1":  ("claude-code", "Claude Code",    "session hooks (SessionEnd, PreCompact)"),
    "2":  ("cursor",      "Cursor",         "session hooks (sessionStart, sessionEnd, preCompact)"),
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

_MODELS = {
    "1": ("claude-haiku-4-5",   "fastest, lowest cost — good for high-frequency flushes"),
    "2": ("claude-sonnet-4-6",  "balanced speed and quality (recommended)"),
    "3": ("claude-opus-4-8",    "highest quality, higher cost — best for compile/query"),
}


@main.command()
@click.option("--agent", type=click.Choice([a[0] for a in _AGENTS.values()]), default=None,
              help="Skip interactive agent selection.")
@click.option("--provider", type=click.Choice([p[0] for p in _PROVIDERS.values()]), default=None,
              help="Skip interactive provider selection.")
@click.option("--model", type=click.Choice([m[0] for m in _MODELS.values()]), default=None,
              help="LLM model for flush/compile/query.")
@click.option("--knowledge-dir", default=None, help="Knowledge base directory (default: knowledge)")
@click.option("--daily-dir", default=None, help="Daily logs directory (default: daily)")
def init(agent: str | None, provider: str | None, model: str | None, knowledge_dir: str | None, daily_dir: str | None) -> None:
    """Configure lmc for this project — select agent, write hook config.

    Run `lmc install` first to make lmc available system-wide, then run
    `lmc init` from your knowledge base directory to configure it.
    """
    project_root = _kb_root()
    is_tty = sys.stdin.isatty()

    if is_tty:
        _print_banner()

    # Detect existing setup for migration messaging
    existing_config = project_root / ".llm-memory" / "config.json"
    if existing_config.exists():
        _console.print("[dim]Existing config detected — reconfiguring.[/dim]")

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

    # ── Model selection ──
    if model is None:
        if is_tty:
            click.echo("\nSelect model for flush/compile/query:")
            for num, (key, desc) in _MODELS.items():
                click.echo(f"  {num}. {key:28} [{desc}]")
            choice = click.prompt("Model", default="2")
            model_entry = _MODELS.get(choice)
            if model_entry is None:
                raise click.BadParameter(f"Choose 1-{len(_MODELS)}")
            model = model_entry[0]
        else:
            model = "claude-sonnet-4-6"

    # ── Directories ──
    if knowledge_dir is None and is_tty:
        knowledge_dir = click.prompt("Knowledge directory", default="llm-memory/knowledge")
    if daily_dir is None and is_tty:
        daily_dir = click.prompt("Daily log directory", default="llm-memory/daily")

    knowledge_dir = knowledge_dir or "llm-memory/knowledge"
    daily_dir = daily_dir or "llm-memory/daily"

    # ── Write config ──
    config_data = {
        "agent": agent,
        "api_provider": provider,
        "model": model,
        "knowledge_dir": knowledge_dir,
        "daily_dir": daily_dir,
    }
    config_file = _write_config(project_root, config_data)
    _console.print(f"  [green]✓[/green] Wrote [cyan]{config_file}[/cyan]")

    # Migrate existing state if present
    _migrate_state(project_root)

    # ── Create content directories ──
    daily_path = project_root / daily_dir
    knowledge_path = project_root / knowledge_dir
    daily_path.mkdir(parents=True, exist_ok=True)
    _console.print(f"  [green]✓[/green] Created [cyan]{daily_path}/[/cyan]")
    for subdir in ("concepts", "connections", "qa"):
        (knowledge_path / subdir).mkdir(parents=True, exist_ok=True)
    _console.print(f"  [green]✓[/green] Created [cyan]{knowledge_path}/[/cyan]")

    # ── Copy AGENTS.md (required by lmc compile) ──
    from llm_memory.config import LMC_HOME
    lmc_content_dir = project_root / "llm-memory"
    lmc_content_dir.mkdir(exist_ok=True)
    for fname in ("AGENTS.md", "README.md"):
        src = LMC_HOME / "templates" / fname
        dest = lmc_content_dir / fname
        if src.exists() and not dest.exists():
            shutil.copy2(src, dest)
            _console.print(f"  [green]✓[/green] Copied  [cyan]{dest}[/cyan]")
        elif not src.exists() and fname == "AGENTS.md":
            _console.print(
                f"  [yellow]![/yellow] AGENTS.md template not found in [cyan]{LMC_HOME / 'templates'}[/cyan] — "
                "run [bold]lmc install[/bold] first"
            )

    # ── Install agent hooks/config ──
    from llm_memory.agents import get_agent
    adapter = get_agent(agent)
    result = adapter.install(project_root)

    for f in result.files_written:
        _console.print(f"  [green]✓[/green] Wrote  [cyan]{f}[/cyan]")

    _console.print()
    _console.print(Rule(style="dim"))
    _console.print()
    _console.print(Align.center(Text("Project configured!", style="bold green")))
    _console.print()
    for step in result.manual_steps:
        _console.print(f"  [cyan]→[/cyan] {step}")
    _console.print()


# ── hook (internal dispatcher for agent hook commands) ────────────────

@main.group(hidden=True)
@click.option(
    "--kb-root",
    default=None,
    help="Knowledge base root directory. Overrides the CWD-derived default.",
)
def hook(kb_root: str | None) -> None:
    """Internal dispatcher — called by agent hook commands (not for direct use)."""
    import os
    if kb_root:
        # Set before any hook module imports llm_memory.config (lazy import via _run_hook).
        os.environ["LMC_KB_ROOT"] = str(Path(kb_root).resolve())


def _run_hook(module_path: str) -> None:
    """Import and run a hook module's main() function."""
    import importlib
    mod = importlib.import_module(module_path)
    mod.main()


@hook.command("session-start")
def hook_session_start() -> None:
    _run_hook("llm_memory.session_start")

@hook.command("session-end")
def hook_session_end() -> None:
    _run_hook("llm_memory.session_end")

@hook.command("pre-compact")
def hook_pre_compact() -> None:
    _run_hook("llm_memory.pre_compact")

@hook.command("cursor-session-start")
def hook_cursor_session_start() -> None:
    _run_hook("llm_memory.cursor_session_start")

@hook.command("cursor-session-end")
def hook_cursor_session_end() -> None:
    _run_hook("llm_memory.cursor_session_end")

@hook.command("cursor-pre-compact")
def hook_cursor_pre_compact() -> None:
    _run_hook("llm_memory.cursor_pre_compact")

@hook.command("windsurf")
def hook_windsurf() -> None:
    _run_hook("llm_memory.windsurf_hook")

@hook.command("generic-session-end")
def hook_generic_session_end() -> None:
    _run_hook("llm_memory.generic_session_end")


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

    project_root = _kb_root()
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


# ── test ─────────────────────────────────────────────────────────────

_TEST_CONTEXT = """\
**User:** What's the best way to structure error handling in async Python?

**Assistant:** For async code I recommend three layers: use try/except around
individual awaits for recoverable errors, a top-level asyncio.run() wrapper
for fatal errors, and structured logging throughout so failures are traceable.
Key insight: never swallow exceptions silently in async callbacks.

**User:** Should I use contextlib.suppress?

**Assistant:** Only for genuinely ignorable errors — cancelled tasks, optional
cleanup — and always at the narrowest scope. If you find yourself suppressing
something and then checking a flag, that's a sign the error actually matters.
"""

@main.command("test")
@click.option("--no-write", is_flag=True, help="Test the provider without writing to the daily log.")
def test_pipeline(no_write: bool) -> None:
    """Run an end-to-end test of the lmc pipeline with real credentials.

    Checks prerequisites, calls the LLM provider, and (unless --no-write)
    flushes a sample conversation into the daily log so you can verify the
    full hook → flush → daily-log path is working.
    """
    import asyncio
    from llm_memory.config import (
        AGENTS_FILE, CONFIGURED_AGENT, DAILY_DIR, KNOWLEDGE_DIR,
        LMC_CONTENT_DIR, MODEL, ROOT_DIR, STATE_DIR,
    )

    _console.print()
    _console.print(Rule("[bold]lmc test[/bold]", style="cyan"))
    _console.print()

    ok = True

    # ── 1. Config ──
    config_file = ROOT_DIR / ".llm-memory" / "config.json"
    if config_file.exists():
        _console.print(f"  [green]✓[/green] Config        {config_file}")
        _console.print(f"           agent=[cyan]{CONFIGURED_AGENT}[/cyan]   model=[cyan]{MODEL}[/cyan]   kb={ROOT_DIR}")
    else:
        _console.print(f"  [red]✗[/red] No config at {config_file} — run [bold]lmc init[/bold] first")
        ok = False

    # ── 2. Directory structure ──
    for label, path in [("AGENTS.md", AGENTS_FILE), ("daily/", DAILY_DIR), ("knowledge/", KNOWLEDGE_DIR)]:
        if path.exists():
            _console.print(f"  [green]✓[/green] {label:<14}{path}")
        else:
            _console.print(f"  [red]✗[/red] Missing: {path}")
            ok = False

    if not ok:
        _console.print("\n  [red]Fix the issues above before testing the provider.[/red]\n")
        raise SystemExit(1)

    # ── 3. Provider call ──
    _console.print()
    _console.print("  Calling LLM provider…", end="")
    try:
        from llm_memory.providers import get_provider
        provider = get_provider()
        response, cost = asyncio.run(provider.call(
            "Respond with exactly: PROVIDER_OK",
            allowed_tools=[],
            max_turns=2,
            cwd=str(ROOT_DIR),
        ))
        if "PROVIDER_OK" in response:
            _console.print(f" [green]✓[/green]  (${cost:.4f})")
        else:
            _console.print(f" [yellow]![/yellow]  unexpected response: {response[:80]!r}")
    except Exception as e:
        _console.print(f"\n  [red]✗[/red] Provider error: {e}")
        raise SystemExit(1)

    if no_write:
        _console.print()
        _console.print("  [dim]--no-write: skipping flush.[/dim]")
        _console.print(Rule(style="dim"))
        _console.print(Align.center(Text("Provider OK", style="bold green")))
        _console.print()
        return

    # ── 4. Flush test ──
    _console.print("  Running flush with sample conversation…")
    from llm_memory.flush import run_flush, append_to_daily_log
    try:
        result = asyncio.run(run_flush(_TEST_CONTEXT, ROOT_DIR))
    except Exception as e:
        _console.print(f"  [red]✗[/red] Flush error: {e}")
        raise SystemExit(1)

    _console.print()
    _console.print("  [bold]Flush result:[/bold]")
    _console.print(Rule(style="dim"))
    _console.print(result)
    _console.print(Rule(style="dim"))

    if not no_write:
        if "FLUSH_OK" in result:
            append_to_daily_log(DAILY_DIR, "FLUSH_OK - test session (nothing to save)", "lmc test")
        else:
            append_to_daily_log(DAILY_DIR, result, "lmc test")
        daily_log = DAILY_DIR / f"{__import__('datetime').date.today()}.md"
        _console.print(f"\n  [green]✓[/green] Written to [cyan]{daily_log}[/cyan]")

    _console.print()
    _console.print(Rule(style="dim"))
    _console.print(Align.center(Text("All checks passed ✓", style="bold green")))
    _console.print()


if __name__ == "__main__":
    main()
