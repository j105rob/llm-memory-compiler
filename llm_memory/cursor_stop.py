"""Cursor stop hook - captures transcript when a Cursor session ends."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Recursion guard: exit if we were spawned by the flush process
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)


def _setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [cursor-stop] %(message)s",
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

    status = hook_input.get("status", "")
    conversation_id = hook_input.get("conversation_id", "unknown")

    logging.info("Cursor stop: conversation=%s status=%s", conversation_id, status)

    # Only capture fully completed sessions, not aborted or errored ones
    if status != "completed":
        logging.info("SKIP: status=%s", status)
        return

    # Transcript path arrives in the JSON payload and/or as an env var
    transcript_path_str = (
        hook_input.get("transcript_path")
        or os.environ.get("CURSOR_TRANSCRIPT_PATH", "")
    )
    if not transcript_path_str:
        logging.info("SKIP: no transcript path")
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logging.info("SKIP: transcript not found: %s", transcript_path_str)
        return

    try:
        # Cursor's JSONL format matches Claude Code's: message.role / message.content
        context, turn_count = extract_conversation_context(transcript_path)
    except Exception as e:
        logging.error("Context extraction failed: %s", e)
        return

    if not context.strip() or turn_count < 1:
        logging.info("SKIP: empty or too short context")
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    context_file = STATE_DIR / f"cursor-stop-{conversation_id}-{timestamp}.md"
    context_file.write_text(context, encoding="utf-8")

    cmd = [
        "uv", "run", "--directory", str(ROOT_DIR),
        "llm-memory-compiler", "flush", str(context_file), conversation_id,
    ]

    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        logging.info("Spawned flush: conversation=%s turns=%d", conversation_id, turn_count)
    except Exception as e:
        logging.error("Failed to spawn flush: %s", e)


if __name__ == "__main__":
    main()
