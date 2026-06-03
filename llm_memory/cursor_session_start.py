"""Cursor sessionStart hook - injects knowledge base context into every session.

Cursor's sessionStart output format differs from Claude Code's:
  { "additional_context": "..." }   (Cursor)
vs
  { "hookSpecificOutput": { "hookEventName": "SessionStart", "additionalContext": "..." } }  (Claude Code)
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    from llm_memory.config import DAILY_DIR, KNOWLEDGE_DIR
    from llm_memory.session_start import build_context

    context = build_context(KNOWLEDGE_DIR, DAILY_DIR)
    print(json.dumps({"additional_context": context}))


if __name__ == "__main__":
    main()
