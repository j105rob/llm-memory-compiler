"""Path constants and configuration for the llm-memory-compiler."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# LMC_KB_ROOT is set by the lmc wrapper scripts so the KB root is always the
# directory the user invoked lmc from, not the repo directory uv runs in.
_KB_ROOT_ENV = os.environ.get("LMC_KB_ROOT")
_CWD = Path(_KB_ROOT_ENV).resolve() if _KB_ROOT_ENV else Path.cwd()
_CONFIG_FILE = _CWD / ".llm-memory" / "config.json"


def _load_project_config() -> dict:
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


_cfg = _load_project_config()
_config_exists = _CONFIG_FILE.exists()

# ── Paths ──────────────────────────────────────────────────────────────
ROOT_DIR = _CWD
LMC_CONTENT_DIR = ROOT_DIR / "llm-memory"   # project-level content root
DAILY_DIR = ROOT_DIR / _cfg.get("daily_dir", "llm-memory/daily")
KNOWLEDGE_DIR = ROOT_DIR / _cfg.get("knowledge_dir", "llm-memory/knowledge")
CONCEPTS_DIR = KNOWLEDGE_DIR / "concepts"
CONNECTIONS_DIR = KNOWLEDGE_DIR / "connections"
QA_DIR = KNOWLEDGE_DIR / "qa"
REPORTS_DIR = LMC_CONTENT_DIR / "reports"
SCRIPTS_DIR = ROOT_DIR / "scripts"
HOOKS_DIR = ROOT_DIR / "hooks"

# AGENTS.md lives in llm-memory/ in the project; fall back to root for legacy setups.
_agents_candidates = [LMC_CONTENT_DIR / "AGENTS.md", ROOT_DIR / "AGENTS.md"]
AGENTS_FILE = next((p for p in _agents_candidates if p.exists()), LMC_CONTENT_DIR / "AGENTS.md")

INDEX_FILE = KNOWLEDGE_DIR / "index.md"
LOG_FILE = KNOWLEDGE_DIR / "log.md"

# State and log files — .llm-memory/ when configured, scripts/ for backward compat
_state_base = ROOT_DIR / ".llm-memory" if _config_exists else ROOT_DIR / "scripts"
STATE_FILE = _state_base / "state.json"
LAST_FLUSH_FILE = _state_base / "last-flush.json"
STATE_DIR = _state_base
FLUSH_LOG_FILE = _state_base / "flush.log"
COMPILE_LOG_FILE = _state_base / "compile.log"

# ── Global lmc home ───────────────────────────────────────────────────
LMC_HOME = Path.home() / ".lmc"

# ── Agent / Provider config ────────────────────────────────────────────
TIMEZONE = _cfg.get("timezone", "America/Chicago")
CONFIGURED_AGENT = _cfg.get("agent", "claude-code")
API_PROVIDER = _cfg.get("api_provider", "claude-agent-sdk")
MODEL = _cfg.get("model", "claude-sonnet-4-6")


def lmc_cmd() -> list[str]:
    """Return the shell command list to invoke lmc.

    Prefers the globally installed `lmc` binary (PATH) so hook commands stay
    short. Falls back to `uv run --directory ROOT_DIR lmc` when lmc isn't on
    PATH (e.g. immediately after cloning, before running `lmc init`).
    """
    import shutil
    if shutil.which("lmc"):
        return ["lmc"]
    return ["uv", "run", "--directory", str(ROOT_DIR), "lmc"]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
