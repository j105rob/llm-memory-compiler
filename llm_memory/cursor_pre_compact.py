"""Cursor preCompact hook - captures transcript before context compaction.

Fires before Cursor auto-compacts the context window. Captures the full
conversation so far since compaction discards detailed message history.

Cursor's preCompact payload:
  Common base: conversation_id, transcript_path, hook_event_name, ...
  Specific:    trigger, context_usage_percent, context_tokens, ...

We use conversation_id (common base) as the session identifier since
preCompact has no session_id field.
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

# Require more turns than sessionEnd since preCompact fires mid-session
MIN_TURNS_TO_FLUSH = 5


def _setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    from llm_memory.utils import rotate_log
    rotate_log(log_file)
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [cursor-pre-compact] %(message)s",
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

    # preCompact has conversation_id in the common base (no session_id)
    conversation_id = hook_input.get("conversation_id", "unknown")
    trigger = hook_input.get("trigger", "unknown")
    usage_pct = hook_input.get("context_usage_percent", 0)

    logging.info(
        "Cursor preCompact: conversation=%s trigger=%s usage=%s%%",
        conversation_id, trigger, usage_pct,
    )

    logging.info("full hook payload: %s", json.dumps(hook_input))

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

    try:
        sample = transcript_path.read_text(encoding="utf-8")[:1000]
        logging.info("transcript sample: %s", sample.replace("\n", " ↵ "))
    except Exception as e:
        logging.error("could not read transcript: %s", e)

    try:
        context, turn_count = extract_conversation_context(transcript_path)
    except Exception as e:
        logging.error("Context extraction failed: %s", e)
        return

    logging.info("extracted %d turns", turn_count)
    if not context.strip() or turn_count < MIN_TURNS_TO_FLUSH:
        logging.info("SKIP: only %d turns (min %d)", turn_count, MIN_TURNS_TO_FLUSH)
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    context_file = STATE_DIR / f"cursor-compact-{conversation_id}-{timestamp}.md"
    context_file.write_text(context, encoding="utf-8")

    from llm_memory.config import lmc_cmd
    cmd = [*lmc_cmd(), "flush", str(context_file), conversation_id]

    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        log_fh = open(str(FLUSH_LOG_FILE), "a")
        subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=log_fh,
            creationflags=creation_flags,
        )
        logging.info(
            "Spawned flush: conversation=%s turns=%d", conversation_id, turn_count,
        )
    except Exception as e:
        logging.error("Failed to spawn flush: %s", e)


if __name__ == "__main__":
    main()
