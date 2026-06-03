# LLM Memory Compiler

**Your AI conversations compile themselves into a searchable knowledge base.**

Adapted from [Karpathy's LLM Knowledge Base](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) architecture. When a session ends, hooks capture the conversation transcript and a background process uses an LLM to extract decisions, lessons, patterns, and gotchas into a daily log. Those logs compile into structured, cross-referenced knowledge articles. Retrieval uses a simple index file — no vector database, no embeddings, just markdown.

## Supported Agents

| Agent | Support | Hook Event | Config Written |
|-------|---------|------------|----------------|
| **Claude Code** | Full auto-capture | SessionEnd, PreCompact | `.claude/settings.json` |
| **Cursor** | Full auto-capture | stop | `.cursor/hooks.json` |
| **Windsurf** | Full auto-capture | post_cascade_response_with_transcript | `~/.codeium/windsurf/hooks.json` |
| **Gemini CLI** | Full auto-capture | SessionEnd | `~/.gemini/settings.json` |
| **OpenAI Codex** | Full auto-capture | Stop | `~/.codex/hooks.json` |
| **Tabnine CLI** | Full auto-capture | SessionEnd | `~/.tabnine/agent/settings.json` |
| **Continue.dev** | Full auto-capture | SessionEnd | `~/.continue/settings.json` |
| **Qwen Code** | Full auto-capture | SessionEnd | `~/.qwen/settings.json` |
| **Devin CLI** | Full auto-capture | SessionEnd | `.devin/hooks.v1.json` |
| **GitHub Copilot** | Context injection only | — | `.github/copilot-instructions.md` |
| **Any other agent** | Manual mode | — | See [Unsupported Agents](#unsupported-agents) |

## Quick Start

```bash
git clone https://github.com/j105rob/llm-memory-compiler
cd llm-memory-compiler
uv sync
uv run llm-memory-compiler init
```

The `init` wizard asks:
1. **Which agent** you use
2. **Which LLM provider** to use for compilation (claude-agent-sdk or Anthropic API key)
3. **Directory names** for daily logs and knowledge articles (defaults are fine)

Then it writes the hook config for your agent and you're done.

## How It Works

```
Conversation → session-end hook → background flush extracts knowledge
    → daily/YYYY-MM-DD.md → compile → knowledge/concepts/, connections/, qa/
        → next session gets index injected → cycle repeats
```

- **Hooks** fire automatically at session end (or after each response for Windsurf)
- **flush** calls the LLM to decide what's worth saving; triggers end-of-day compilation after 6 PM
- **compile** turns daily logs into organized concept articles with cross-references
- **query** answers questions using index-guided retrieval (no RAG needed at personal scale)
- **lint** runs 7 health checks (broken links, orphans, contradictions, staleness)

## Agent Setup Details

### Claude Code
Hooks are registered in `.claude/settings.json` in this project. Open the project in Claude Code — hooks activate automatically. SessionEnd captures each conversation; PreCompact captures context before auto-summarization.

### Cursor
A `stop` hook in `.cursor/hooks.json` fires when a session completes. Aborted or errored sessions are skipped. Cursor's transcript format is compatible with the standard extractor.

### Windsurf
A global hook in `~/.codeium/windsurf/hooks.json` fires after every Cascade response (not just session end). A 60-second dedup window prevents redundant flushes.

### Gemini CLI / OpenAI Codex / Tabnine / Continue.dev / Qwen Code
All share the same standard JSON hooks protocol as Claude Code. A global hook config is written to the agent's settings file. The `SessionEnd` (or `Stop` for Codex) event fires with `session_id` and `transcript_path` in the stdin payload.

### Devin CLI
Hook config goes in `.devin/hooks.v1.json` inside this project. Devin's schema is slightly different (no `"hooks"` wrapper key), but the stdin payload is the same.

### GitHub Copilot
Interactive Copilot Chat has no public session hooks. Run `inject-context` to push the knowledge index to `.github/copilot-instructions.md` so Copilot sees your knowledge base as context.

## Unsupported Agents

If your agent isn't in the table above, you can still use the knowledge base manually:

**Option 1 — Manual flush after each session**

Export or copy your conversation to a file, then run:
```bash
uv run llm-memory-compiler flush /path/to/conversation.txt my-session-id
```
The flush command reads the file, extracts knowledge, and appends it to today's daily log.

**Option 2 — Inject context so your agent sees the knowledge base**

Run this before starting a session or after each compile:
```bash
uv run llm-memory-compiler inject-context
```
This reads `knowledge/index.md` and writes it to a file your agent can pick up as context (configure the output path by selecting the closest supported agent during `init`, or add the generated file to your agent's context rules manually).

**Option 3 — Schedule periodic context injection**

Add a cron job to keep your agent's context file fresh:
```bash
# Runs inject-context every hour
0 * * * * cd /path/to/llm-memory-compiler && uv run llm-memory-compiler inject-context
```

**Option 4 — Add this project as your agent's context rule**

Point your agent's rules file at `knowledge/index.md` directly. Most agents support an "always include" rule that you can configure to include this file automatically in every session.

## LLM Provider

| Provider | Credential | Use case |
|----------|-----------|----------|
| `claude-agent-sdk` (default) | `~/.claude/.credentials.json` | Claude Max/Team/Enterprise subscribers |
| `anthropic-api` | `ANTHROPIC_API_KEY` env var | Everyone else; direct API billing |

> Anthropic has clarified that personal use of the Claude Agent SDK is covered under existing Claude subscriptions — no separate API credits needed for the default provider.

## Commands

```bash
uv run llm-memory-compiler init                         # setup wizard (run once)
uv run llm-memory-compiler inject-context               # push index to agent context file

uv run llm-memory-compiler compile                      # compile new daily logs
uv run llm-memory-compiler compile --all                # recompile everything
uv run llm-memory-compiler compile --dry-run            # preview without running
uv run llm-memory-compiler query "your question"        # ask the knowledge base
uv run llm-memory-compiler query "question" --file-back # ask + save answer as Q&A article
uv run llm-memory-compiler lint                         # run all health checks
uv run llm-memory-compiler lint --structural-only       # free structural checks only
uv run llm-memory-compiler flush <file> <session-id>    # manually flush a conversation
```

Legacy `uv run python scripts/*.py` commands still work.

## Why No RAG?

Karpathy's insight: at personal scale (50–500 articles), the LLM reading a structured `index.md` outperforms vector similarity. The LLM understands what you're really asking; cosine similarity just finds similar words. RAG becomes necessary at ~2,000+ articles when the index exceeds the context window.

## Technical Reference

See **[AGENTS.md](AGENTS.md)** for the complete technical reference: article formats, hook architecture, script internals, cross-platform details, costs, and customization options.
