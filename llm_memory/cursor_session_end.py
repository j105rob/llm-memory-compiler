"""Cursor sessionEnd hook - captures transcript when a session ends.

Cursor's sessionEnd payload:
  Common base: conversation_id, transcript_path, hook_event_name, ...
  Specific:    session_id, reason, duration_ms, is_background_agent, ...

We use session_id (sessionEnd-specific) as the dedup key and
transcript_path (common base) to locate the conversation.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

MIN_TURNS_TO_FLUSH = 1


def _setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    from llm_memory.utils import rotate_log
    rotate_log(log_file)
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [cursor-session-end] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    from llm_memory.config import FLUSH_LOG_FILE, ROOT_DIR, STATE_DIR
    from llm_memory.transcript import extract_conversation_context

    _setup_logging(FLUSH_LOG_FILE)

    try:
        hook_input: dict = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError, ValueError) as e:
        logging.error("Failed to parse stdin: %s", e)
        return

    # session_id is in the sessionEnd-specific fields; conversation_id is the common base
    session_id = hook_input.get("session_id") or hook_input.get("conversation_id", "unknown")
    reason = hook_input.get("reason", "unknown")

    logging.info("Cursor sessionEnd: session=%s reason=%s", session_id, reason)

    # Skip sessions that errored out mid-stream
    if reason == "error":
        logging.info("SKIP: reason=error")
        return

    transcript_path_str = (
        hook_input.get("transcript_path")
        or os.environ.get("CURSOR_TRANSCRIPT_PATH", "")
    )
    logging.info("transcript_path=%s", transcript_path_str or "(none)")
    if not transcript_path_str:
        logging.info("SKIP: no transcript path")
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logging.info("SKIP: transcript not found: %s", transcript_path_str)
        return

    # Log a sample of the transcript so format issues are diagnosable
    try:
        sample = transcript_path.read_text(encoding="utf-8")[:500]
        logging.info("transcript sample (first 500 chars): %s", sample.replace("\n", " ↵ "))
    except Exception:
        pass

    try:
        context, turn_count = extract_conversation_context(transcript_path)
    except Exception as e:
        logging.error("Context extraction failed: %s", e)
        return

    logging.info("extracted %d turns", turn_count)
    if not context.strip() or turn_count < MIN_TURNS_TO_FLUSH:
        logging.info("SKIP: only %d turns", turn_count)
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    context_file = STATE_DIR / f"cursor-end-{session_id}-{timestamp}.md"
    context_file.write_text(context, encoding="utf-8")

    from llm_memory.config import lmc_cmd
    cmd = [*lmc_cmd(), "flush", str(context_file), session_id]

    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        log_fh = open(str(FLUSH_LOG_FILE), "a")
        subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=log_fh,
            creationflags=creation_flags,
        )
        logging.info("Spawned flush: session=%s turns=%d", session_id, turn_count)
    except Exception as e:
        logging.error("Failed to spawn flush: %s", e)


if __name__ == "__main__":
    main()
