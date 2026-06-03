"""Memory flush agent - extracts important knowledge from conversation context.

Spawned by session-end or pre-compact hooks as a background process. Reads
pre-extracted conversation context from a .md file, uses the LLM to decide
what's worth saving, and appends the result to today's daily log.
"""

from __future__ import annotations

# Recursion prevention: set before any imports that might trigger the agent
import os
os.environ["CLAUDE_INVOKED_BY"] = "memory_flush"

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


COMPILE_AFTER_HOUR = 18


def load_flush_state(state_file: Path) -> dict:
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_flush_state(state_file: Path, state: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state), encoding="utf-8")


def append_to_daily_log(daily_dir: Path, content: str, section: str = "Session") -> None:
    today = datetime.now(timezone.utc).astimezone()
    log_path = daily_dir / f"{today.strftime('%Y-%m-%d')}.md"

    if not log_path.exists():
        daily_dir.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"# Daily Log: {today.strftime('%Y-%m-%d')}\n\n## Sessions\n\n## Memory Maintenance\n\n",
            encoding="utf-8",
        )

    time_str = today.strftime("%H:%M")
    entry = f"### {section} ({time_str})\n\n{content}\n\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


async def run_flush(context: str, root: Path) -> str:
    from llm_memory.providers import get_provider

    prompt = f"""Review the conversation context below and respond with a concise summary
of important items that should be preserved in the daily log.
Do NOT use any tools — just return plain text.

Format your response as a structured daily log entry with these sections:

**Context:** [One line about what the user was working on]

**Key Exchanges:**
- [Important Q&A or discussions]

**Decisions Made:**
- [Any decisions with rationale]

**Lessons Learned:**
- [Gotchas, patterns, or insights discovered]

**Action Items:**
- [Follow-ups or TODOs mentioned]

Skip anything that is:
- Routine tool calls or file reads
- Content that's trivial or obvious
- Trivial back-and-forth or clarification exchanges

Only include sections that have actual content. If nothing is worth saving,
respond with exactly: FLUSH_OK

## Conversation Context

{context}"""

    provider = get_provider()
    response = ""

    try:
        response, _ = await provider.call(
            prompt,
            allowed_tools=[],
            max_turns=2,
            cwd=str(root),
        )
    except Exception as e:
        import traceback
        logging.error("Provider error: %s\n%s", e, traceback.format_exc())
        response = f"FLUSH_ERROR: {type(e).__name__}: {e}"

    return response


def maybe_trigger_compilation(root: Path, daily_dir: Path, state_dir: Path) -> None:
    import subprocess as _sp

    now = datetime.now(timezone.utc).astimezone()
    if now.hour < COMPILE_AFTER_HOUR:
        return

    today_log = f"{now.strftime('%Y-%m-%d')}.md"
    compile_state_file = state_dir / "state.json"
    if compile_state_file.exists():
        try:
            compile_state = json.loads(compile_state_file.read_text(encoding="utf-8"))
            ingested = compile_state.get("ingested", {})
            if today_log in ingested:
                from hashlib import sha256
                log_path = daily_dir / today_log
                if log_path.exists():
                    current_hash = sha256(log_path.read_bytes()).hexdigest()[:16]
                    if ingested[today_log].get("hash") == current_hash:
                        return
        except (json.JSONDecodeError, OSError):
            pass

    logging.info("End-of-day compilation triggered (after %d:00)", COMPILE_AFTER_HOUR)

    cmd = ["uv", "run", "--directory", str(root), "llm-memory-compiler", "compile"]

    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = _sp.CREATE_NEW_PROCESS_GROUP | _sp.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True

    try:
        compile_log = state_dir / "compile.log"
        compile_log.parent.mkdir(parents=True, exist_ok=True)
        log_handle = open(str(compile_log), "a")
        _sp.Popen(cmd, stdout=log_handle, stderr=_sp.STDOUT, cwd=str(root), **kwargs)
    except Exception as e:
        logging.error("Failed to spawn compile: %s", e)


def main() -> None:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <context_file.md> <session_id>", file=sys.stderr)
        sys.exit(1)

    context_file = Path(sys.argv[1])
    session_id = sys.argv[2]

    # Import config after setting up logging path
    from llm_memory.config import (
        DAILY_DIR,
        FLUSH_LOG_FILE,
        LAST_FLUSH_FILE,
        ROOT_DIR,
        STATE_DIR,
    )

    _setup_logging(FLUSH_LOG_FILE)
    logging.info("flush started for session %s, context: %s", session_id, context_file)

    if not context_file.exists():
        logging.error("Context file not found: %s", context_file)
        return

    state = load_flush_state(LAST_FLUSH_FILE)
    if (
        state.get("session_id") == session_id
        and time.time() - state.get("timestamp", 0) < 60
    ):
        logging.info("Skipping duplicate flush for session %s", session_id)
        context_file.unlink(missing_ok=True)
        return

    context = context_file.read_text(encoding="utf-8").strip()
    if not context:
        logging.info("Context file is empty, skipping")
        context_file.unlink(missing_ok=True)
        return

    logging.info("Flushing session %s: %d chars", session_id, len(context))

    response = asyncio.run(run_flush(context, ROOT_DIR))

    if "FLUSH_OK" in response:
        logging.info("Result: FLUSH_OK")
        append_to_daily_log(DAILY_DIR, "FLUSH_OK - Nothing worth saving from this session", "Memory Flush")
    elif "FLUSH_ERROR" in response:
        logging.error("Result: %s", response)
        append_to_daily_log(DAILY_DIR, response, "Memory Flush")
    else:
        logging.info("Result: saved to daily log (%d chars)", len(response))
        append_to_daily_log(DAILY_DIR, response, "Session")

    save_flush_state(LAST_FLUSH_FILE, {"session_id": session_id, "timestamp": time.time()})
    context_file.unlink(missing_ok=True)
    maybe_trigger_compilation(ROOT_DIR, DAILY_DIR, STATE_DIR)
    logging.info("Flush complete for session %s", session_id)


if __name__ == "__main__":
    main()
