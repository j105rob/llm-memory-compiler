# LLM Memory Compiler

**Your AI conversations compile themselves into a searchable knowledge base.**

Adapted from [Karpathy's LLM Knowledge Base](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) architecture. When a session ends, hooks capture the conversation transcript and a background process uses an LLM to extract decisions, lessons, patterns, and gotchas into a daily log. Those logs compile into structured, cross-referenced knowledge articles. Retrieval uses a simple index file — no vector database, no embeddings, just markdown.

## Project Layout

After `lmc init`, your knowledge base directory will contain:

```
my-kb/
├── llm-memory/               # all lmc content lives here
│   ├── daily/                # auto-captured session logs (one file per day)
│   ├── knowledge/            # compiled articles
│   │   ├── index.md          # auto-generated index (injected at session start)
│   │   ├── concepts/         # concept articles
│   │   ├── connections/      # relationship articles
│   │   └── qa/               # Q&A articles
│   ├── AGENTS.md             # article format reference (read by lmc compile)
│   └── README.md             # quick reference
└── .llm-memory/              # lmc config (hidden)
    └── config.json
```

Agent hook configs (`.claude/settings.json`, `.cursor/hooks.json`, etc.) are written alongside the config — outside `llm-memory/` since they belong to the agent, not the KB.

## Supported Agents

| Agent | Support | Hook events | Config written |
|-------|---------|-------------|----------------|
| **Claude Code** | Full auto-capture | SessionStart, SessionEnd, PreCompact | `.claude/settings.json` |
| **Cursor** | Full auto-capture | sessionStart, sessionEnd, preCompact | `.cursor/hooks.json` |
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

**Step 1 — Install lmc (once per machine)**

```bash
git clone https://github.com/j105rob/llm-memory-compiler
cd llm-memory-compiler
uv sync
./lmc install
```

`install` verifies uv, syncs dependencies, and writes a launcher script to `~/.local/bin/lmc` so `lmc` is available from any directory. It will warn you if `~/.local/bin` isn't on your PATH yet.

**Step 2 — Configure your project (once per knowledge base)**

```bash
lmc init
```

`init` asks which AI agent you use, which LLM provider to use for compilation, and writes the hook config for that agent. Run it from the directory you want as your knowledge base root.

## How It Works

```
Conversation → session-end hook → background flush extracts knowledge
    → llm-memory/daily/YYYY-MM-DD.md → compile → llm-memory/knowledge/concepts/, connections/, qa/
        → next session gets index injected → cycle repeats
```

- **Hooks** fire automatically at session end — and at session start to inject your knowledge index as context
- **flush** calls the LLM to decide what's worth saving; auto-triggers end-of-day compilation after 6 PM
- **compile** turns daily logs into organized concept articles with cross-references
- **query** answers questions using index-guided retrieval (no RAG needed at personal scale)
- **lint** runs 7 health checks (broken links, orphans, contradictions, staleness)

## Agent Setup Details

### Claude Code
Hooks in `.claude/settings.json`: SessionStart injects your knowledge index as context at the start of every session; SessionEnd captures the transcript; PreCompact captures context before auto-summarization discards it.

### Cursor
Three hooks in `.cursor/hooks.json`: sessionStart (context injection), sessionEnd (transcript capture, skips `reason=error`), preCompact (capture before auto-compaction, requires ≥ 5 turns). Cursor's JSONL transcript format is compatible with the standard extractor.

### Windsurf
A global hook in `~/.codeium/windsurf/hooks.json` fires after every Cascade response (not just session end). `working_directory` is set to the KB root so `./lmc` resolves correctly. A 60-second dedup window prevents redundant flushes within one session.

### Gemini CLI / OpenAI Codex / Tabnine / Continue.dev / Qwen Code
All use the standard JSON hooks protocol. A global hook config is written to the agent's settings file with the absolute path to `lmc` hardcoded (e.g. `/home/you/llm-memory-compiler/lmc hook generic-session-end`). The `SessionEnd` (or `Stop` for Codex) event delivers `session_id` and `transcript_path` in the stdin payload — the same fields our handler reads.

### Devin CLI
Hook config in `.devin/hooks.v1.json` inside this project. Devin's schema omits the outer `"hooks"` wrapper key, but the stdin payload is identical.

### GitHub Copilot
Interactive Copilot Chat has no public session hooks. Run `lmc inject-context` to push the knowledge index into `.github/copilot-instructions.md` so Copilot sees your knowledge base as context.

## Unsupported Agents

If your agent isn't listed, you can still use the knowledge base manually:

**Option 1 — Manual flush after each session**

Export or copy your conversation to a plain text file, then:
```bash
lmc flush /path/to/conversation.txt my-session-id
```
The flush command extracts knowledge and appends it to today's daily log.

**Option 2 — Inject context before each session**

Run this after compiling or whenever you want the context refreshed:
```bash
lmc inject-context
```
This writes `knowledge/index.md` to your agent's context rules file. Select the closest supported agent during `init` to control where it writes.

**Option 3 — Schedule periodic context injection**

```bash
# crontab -e: refresh context every hour
0 * * * * /path/to/llm-memory-compiler/lmc inject-context
```

**Option 4 — Point your agent's rules file at the index directly**

Most agents support an "always include" rule. Configure it to include `knowledge/index.md` from this repo — no `lmc` invocation required.

## Commands

```bash
lmc install                       # install lmc globally — run once per machine
lmc install --bin-dir ~/bin       # install to a custom directory
lmc init                          # configure this project — select agent + write hook config
lmc inject-context                # push knowledge index to agent context file

lmc compile                       # compile new/changed daily logs
lmc compile --all                 # force recompile everything
lmc compile --dry-run             # preview without running
lmc query "your question"         # ask the knowledge base
lmc query "question" --file-back  # ask + save answer as Q&A article
lmc lint                          # run all 7 health checks
lmc lint --structural-only        # structural checks only (free, instant)
lmc flush <file> <session-id>     # manually flush a conversation file
```

Before `lmc init`, or if `lmc` isn't on PATH yet:
```bash
./lmc init          # repo-local wrapper, works immediately after clone
uv run lmc init     # explicit uv invocation
```

Legacy `uv run python scripts/*.py` still works.

## LLM Provider

| Provider | Credential | Notes |
|----------|-----------|-------|
| `claude-agent-sdk` (default) | `~/.claude/.credentials.json` | Claude Max/Team/Enterprise — no separate API billing |
| `anthropic-api` | `ANTHROPIC_API_KEY` env var | Direct API; works without Claude Code installed |

## Why No RAG?

Karpathy's insight: at personal scale (50–500 articles), the LLM reading a structured `index.md` outperforms vector similarity. The LLM understands what you're really asking; cosine similarity just finds similar words. RAG becomes necessary at ~2,000+ articles when the index exceeds the context window.

## Technical Reference

See **[AGENTS.md](AGENTS.md)** for the complete technical reference: article formats, hook architecture, script internals, multi-agent hook protocol details, costs, and customization options.
