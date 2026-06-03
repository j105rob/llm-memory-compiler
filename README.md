# LLM Memory Compiler

**Your AI conversations compile themselves into a searchable knowledge base.**

Adapted from [Karpathy's LLM Knowledge Base](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) architecture. When a session ends, hooks capture the conversation transcript and a background process uses an LLM to extract decisions, lessons, patterns, and gotchas into a daily log. Those logs compile into structured, cross-referenced knowledge articles. Retrieval uses a simple index file — no vector database, no embeddings, just markdown.

Works with **Claude Code** (full auto-capture via session hooks), **Cursor**, **Windsurf**, and **GitHub Copilot** (context injection).

## Quick Start

```bash
git clone https://github.com/j105rob/llm-memory-compiler
cd llm-memory-compiler
uv sync
uv run llm-memory-compiler init
```

The `init` command walks you through:
1. **Select your AI agent** — Claude Code, Cursor, Windsurf, or GitHub Copilot
2. **Select your LLM provider** — claude-agent-sdk (uses your Claude subscription) or Anthropic API key
3. **Configure directories** — where to store daily logs and knowledge articles

For **Claude Code**: hooks activate automatically next time you open the project. After 6 PM local time, the next session automatically triggers end-of-day compilation.

For **Cursor / Windsurf / Copilot**: run `uv run llm-memory-compiler inject-context` to push the knowledge index into your agent's context rules file. Re-run after each compile to keep it fresh.

## How It Works

```
Conversation → SessionEnd/PreCompact hooks → flush extracts knowledge
    → daily/YYYY-MM-DD.md → compile → knowledge/concepts/, connections/, qa/
        → SessionStart hook injects index into next session → cycle repeats
```

- **Hooks** (Claude Code only) capture conversations automatically at session end and before compaction
- **flush** calls the LLM to decide what's worth saving; triggers end-of-day compilation automatically after 6 PM
- **compile** turns daily logs into organized concept articles with cross-references
- **query** answers questions using index-guided retrieval (no RAG needed at personal scale)
- **lint** runs 7 health checks (broken links, orphans, contradictions, staleness)

## Commands

```bash
uv run llm-memory-compiler init                         # setup wizard (run once)
uv run llm-memory-compiler inject-context               # push index to agent context file

uv run llm-memory-compiler compile                      # compile new daily logs
uv run llm-memory-compiler compile --all                # recompile everything
uv run llm-memory-compiler query "your question"        # ask the knowledge base
uv run llm-memory-compiler query "question" --file-back # ask + save answer as Q&A article
uv run llm-memory-compiler lint                         # run all health checks
uv run llm-memory-compiler lint --structural-only       # free structural checks only
```

Legacy `uv run python scripts/*.py` commands still work.

## LLM Provider

| Provider | Credential | Notes |
|----------|-----------|-------|
| `claude-agent-sdk` (default) | `~/.claude/.credentials.json` | Uses your Claude Max/Team/Enterprise subscription |
| `anthropic-api` | `ANTHROPIC_API_KEY` env var | Direct API billing; works without Claude Code installed |

Anthropic has clarified that personal use of the Claude Agent SDK is covered under your existing Claude subscription — no separate API credits needed for the default provider.

## Why No RAG?

Karpathy's insight: at personal scale (50–500 articles), the LLM reading a structured `index.md` outperforms vector similarity. The LLM understands what you're really asking; cosine similarity just finds similar words. RAG becomes necessary at ~2,000+ articles when the index exceeds the context window.

## Technical Reference

See **[AGENTS.md](AGENTS.md)** for the complete technical reference: article formats, hook architecture, script internals, cross-platform details, costs, and customization options.
