"""SessionStart hook - injects knowledge base context into every conversation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_CONTEXT_CHARS = 20_000
MAX_LOG_LINES = 30


def build_context(knowledge_dir: Path, daily_dir: Path) -> str:
    parts = []

    today = datetime.now(timezone.utc).astimezone()
    parts.append(f"## Today\n{today.strftime('%A, %B %d, %Y')}")

    index_file = knowledge_dir / "index.md"
    if index_file.exists():
        index_content = index_file.read_text(encoding="utf-8")
        parts.append(f"## Knowledge Base Index\n\n{index_content}")
    else:
        parts.append("## Knowledge Base Index\n\n(empty - no articles compiled yet)")

    recent_log = _get_recent_log(daily_dir, today)
    parts.append(f"## Recent Daily Log\n\n{recent_log}")

    context = "\n\n---\n\n".join(parts)

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n...(truncated)"

    return context


def _get_recent_log(daily_dir: Path, today: datetime) -> str:
    for offset in range(2):
        date = today - timedelta(days=offset)
        log_path = daily_dir / f"{date.strftime('%Y-%m-%d')}.md"
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").splitlines()
            recent = lines[-MAX_LOG_LINES:] if len(lines) > MAX_LOG_LINES else lines
            return "\n".join(recent)
    return "(no recent daily log)"


def main() -> None:
    from llm_memory.config import DAILY_DIR, KNOWLEDGE_DIR

    context = build_context(KNOWLEDGE_DIR, DAILY_DIR)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
