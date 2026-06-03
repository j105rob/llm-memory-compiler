"""Generic session-end hook handler for agents using the standard JSON hooks protocol.

Covers: Gemini CLI, OpenAI Codex, Tabnine CLI, Continue.dev, Qwen Code, Devin CLI.
All of these pass the same stdin payload shape as Claude Code:
  { session_id, transcript_path, hook_event_name, cwd, ... }
and produce JSONL transcripts compatible with extract_conversation_context().
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Recursion guard: flush.py sets this to prevent hook re-entry
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

MIN_TURNS_TO_FLUSH = 1


def _setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [hook] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    from llm_memory.config import FLUSH_LOG_FILE, ROOT_DIR, STATE_DIR
    from llm_memory.transcript import extract_conversation_context

    _setup_logging(FLUSH_LOG_FILE)

    try:
        raw = sys.stdin.read()
        try:
            hook_input: dict = json.loads(raw)
        except json.JSONDecodeError:
            fixed = re.sub(r'(?<!\\)\\(?!["\\])', r'\\\\', raw)
            hook_input = json.loads(fixed)
    except (json.JSONDecodeError, ValueError, EOFError) as e:
        logging.error("Failed to parse stdin: %s", e)
        return

    session_id = hook_input.get("session_id", "unknown")
    event = hook_input.get("hook_event_name", "unknown")
    transcript_path_str = hook_input.get("transcript_path", "")

    logging.info("%s fired: session=%s", event, session_id)

    if not transcript_path_str or not isinstance(transcript_path_str, str):
        logging.info("SKIP: no transcript path")
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logging.info("SKIP: transcript missing: %s", transcript_path_str)
        return

    try:
        context, turn_count = extract_conversation_context(transcript_path)
    except Exception as e:
        logging.error("Context extraction failed: %s", e)
        return

    if not context.strip() or turn_count < MIN_TURNS_TO_FLUSH:
        logging.info("SKIP: only %d turns", turn_count)
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    context_file = STATE_DIR / f"hook-{session_id}-{timestamp}.md"
    context_file.write_text(context, encoding="utf-8")

    from llm_memory.config import lmc_cmd
    cmd = [*lmc_cmd(), "flush", str(context_file), session_id]

    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        logging.info("Spawned flush: session=%s turns=%d", session_id, turn_count)
    except Exception as e:
        logging.error("Failed to spawn flush: %s", e)


if __name__ == "__main__":
    main()
