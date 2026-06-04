"""Windsurf post_cascade_response_with_transcript hook.

Fires after every Cascade response (not just at session end). The dedup
mechanism in flush.py prevents redundant processing of the same session
within a 60-second window.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Recursion guard
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

# Require at least this many turns before flushing; since this hook fires
# per-response (not per-session-end), avoid flushing tiny exchanges.
MIN_TURNS_TO_FLUSH = 3


def _setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [windsurf-hook] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    from llm_memory.config import FLUSH_LOG_FILE, ROOT_DIR, STATE_DIR
    from llm_memory.transcript import extract_windsurf_context

    _setup_logging(FLUSH_LOG_FILE)

    try:
        hook_input: dict = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError, ValueError) as e:
        logging.error("Failed to parse stdin: %s", e)
        return

    trajectory_id = hook_input.get("trajectory_id", "unknown")
    transcript_path_str = hook_input.get("tool_info", {}).get("transcript_path", "")

    logging.info("Windsurf hook: trajectory=%s", trajectory_id)

    if not transcript_path_str:
        logging.info("SKIP: no transcript path in tool_info")
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logging.info("SKIP: transcript not found: %s", transcript_path_str)
        return

    try:
        context, turn_count = extract_windsurf_context(transcript_path)
    except Exception as e:
        logging.error("Context extraction failed: %s", e)
        return

    if not context.strip() or turn_count < MIN_TURNS_TO_FLUSH:
        logging.info("SKIP: %d turns (min %d)", turn_count, MIN_TURNS_TO_FLUSH)
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    context_file = STATE_DIR / f"windsurf-{trajectory_id}-{timestamp}.md"
    context_file.write_text(context, encoding="utf-8")

    from llm_memory.config import lmc_cmd
    cmd = [*lmc_cmd(), "flush", str(context_file), trajectory_id]

    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        log_fh = open(str(FLUSH_LOG_FILE), "a")
        subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=log_fh,
            creationflags=creation_flags,
        )
        logging.info("Spawned flush: trajectory=%s turns=%d", trajectory_id, turn_count)
    except Exception as e:
        logging.error("Failed to spawn flush: %s", e)


if __name__ == "__main__":
    main()
