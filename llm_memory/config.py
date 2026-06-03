"""Path constants and configuration for the llm-memory-compiler."""

import json
from datetime import datetime, timezone
from pathlib import Path

_CWD = Path.cwd()
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
DAILY_DIR = ROOT_DIR / _cfg.get("daily_dir", "daily")
KNOWLEDGE_DIR = ROOT_DIR / _cfg.get("knowledge_dir", "knowledge")
CONCEPTS_DIR = KNOWLEDGE_DIR / "concepts"
CONNECTIONS_DIR = KNOWLEDGE_DIR / "connections"
QA_DIR = KNOWLEDGE_DIR / "qa"
REPORTS_DIR = ROOT_DIR / "reports"
SCRIPTS_DIR = ROOT_DIR / "scripts"
HOOKS_DIR = ROOT_DIR / "hooks"
AGENTS_FILE = ROOT_DIR / "AGENTS.md"

INDEX_FILE = KNOWLEDGE_DIR / "index.md"
LOG_FILE = KNOWLEDGE_DIR / "log.md"

# State and log files — .llm-memory/ when configured, scripts/ for backward compat
_state_base = ROOT_DIR / ".llm-memory" if _config_exists else ROOT_DIR / "scripts"
STATE_FILE = _state_base / "state.json"
LAST_FLUSH_FILE = _state_base / "last-flush.json"
STATE_DIR = _state_base
FLUSH_LOG_FILE = _state_base / "flush.log"
COMPILE_LOG_FILE = _state_base / "compile.log"

# ── Agent / Provider config ────────────────────────────────────────────
TIMEZONE = _cfg.get("timezone", "America/Chicago")
CONFIGURED_AGENT = _cfg.get("agent", "claude-code")
API_PROVIDER = _cfg.get("api_provider", "claude-agent-sdk")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
