# AGENTS.md — LLM Memory Compiler Schema & Technical Reference

> Adapted from [Andrej Karpathy's LLM Knowledge Base](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) architecture.
> Instead of ingesting external articles, this system compiles knowledge from your own AI conversations.

This file serves two purposes:
1. **Schema specification** — tells the LLM compiler exactly how to create and maintain knowledge articles
2. **Technical reference** — documents the full system architecture for developers and AI agents working on this codebase

---

## The Compiler Analogy

```
daily/          = source code    (your conversations — the raw material)
LLM             = compiler       (extracts and organizes knowledge)
knowledge/      = executable     (structured, queryable knowledge base)
lint            = test suite     (health checks for consistency)
queries         = runtime        (using the knowledge)
```

You don't manually organize your knowledge. You have conversations, and the LLM handles the synthesis, cross-referencing, and maintenance.

---

## Architecture

### Layer 1: `daily/` — Conversation Logs (Immutable Source)

Daily logs capture what happened in your AI coding sessions. Append-only, never edited after the fact.

```
daily/
├── 2026-04-01.md
├── 2026-04-02.md
└── ...
```

Each file format:

```markdown
# Daily Log: YYYY-MM-DD

## Sessions

### Session (HH:MM)

**Context:** What the user was working on.

**Key Exchanges:**
- User asked about X, assistant explained Y
- Decided to use Z approach because...

**Decisions Made:**
- Chose library X over Y because...

**Lessons Learned:**
- Always do X before Y to avoid...

**Action Items:**
- [ ] Follow up on X
```

### Layer 2: `knowledge/` — Compiled Knowledge (LLM-Owned)

The LLM owns this directory entirely. Humans read it but rarely edit it directly.

```
knowledge/
├── index.md              # Master catalog — every article with one-line summary
├── log.md                # Append-only chronological build log
├── concepts/             # Atomic knowledge articles
├── connections/          # Cross-cutting insights linking 2+ concepts
└── qa/                   # Filed query answers (compounding knowledge)
```

### Layer 3: This File (AGENTS.md)

The schema that tells the LLM how to compile and maintain the knowledge base.

---

## Structural Files

### `knowledge/index.md` — Master Catalog

A table listing every article. This is the primary retrieval mechanism — the LLM reads this FIRST when answering any query, then selects relevant articles to read in full.

```markdown
# Knowledge Base Index

| Article | Summary | Compiled From | Updated |
|---------|---------|---------------|---------|
| [[concepts/supabase-auth]] | Row-level security patterns and JWT gotchas | daily/2026-04-02.md | 2026-04-02 |
| [[connections/auth-and-webhooks]] | Token verification patterns shared across auth and webhooks | daily/2026-04-04.md | 2026-04-04 |
```

### `knowledge/log.md` — Build Log

Append-only chronological record of every compile, query, and lint operation.

```markdown
# Build Log

## [2026-04-01T14:30:00] compile | Daily Log 2026-04-01
- Source: daily/2026-04-01.md
- Articles created: [[concepts/nextjs-project-structure]], [[concepts/tailwind-setup]]

## [2026-04-02T09:00:00] query | "How do I handle auth redirects?"
- Consulted: [[concepts/supabase-auth]], [[concepts/nextjs-middleware]]
- Filed to: [[qa/auth-redirect-handling]]
```

---

## Article Formats

### Concept Articles (`knowledge/concepts/`)

One article per atomic piece of knowledge.

```markdown
---
title: "Concept Name"
aliases: [alternate-name, abbreviation]
tags: [domain, topic]
sources:
  - "daily/2026-04-01.md"
  - "daily/2026-04-03.md"
created: 2026-04-01
updated: 2026-04-03
---

# Concept Name

[2-4 sentence core explanation]

## Key Points
- [3-5 bullet points, each self-contained]

## Details
[Deeper explanation, 2+ paragraphs]

## Related Concepts
- [[concepts/related-concept]] — How it connects

## Sources
- [[daily/2026-04-01.md]] — Initial discovery
- [[daily/2026-04-03.md]] — Updated after debugging session
```

### Connection Articles (`knowledge/connections/`)

Cross-cutting synthesis linking 2+ concepts. Created when a conversation reveals a non-obvious relationship.

```markdown
---
title: "Connection: X and Y"
connects:
  - "concepts/concept-x"
  - "concepts/concept-y"
sources:
  - "daily/2026-04-04.md"
created: 2026-04-04
updated: 2026-04-04
---

# Connection: X and Y

## The Connection
[What links these concepts]

## Key Insight
[The non-obvious relationship discovered]

## Evidence
[Specific examples from conversations]

## Related Concepts
- [[concepts/concept-x]]
- [[concepts/concept-y]]
```

### Q&A Articles (`knowledge/qa/`)

Filed answers from queries. Every complex question can be permanently stored, making future queries smarter.

```markdown
---
title: "Q: Original Question"
question: "The exact question asked"
consulted:
  - "concepts/article-1"
  - "concepts/article-2"
filed: 2026-04-05
---

# Q: Original Question

## Answer
[Synthesized answer with [[wikilinks]] to sources]

## Sources Consulted
- [[concepts/article-1]] — Relevant because...

## Follow-Up Questions
- What about edge case X?
```

---

## Core Operations

### 1. Compile (`daily/` → `knowledge/`)

1. Read the daily log file
2. Read `knowledge/index.md` to understand current knowledge state
3. Read existing articles that may need updating
4. For each piece of knowledge:
   - Existing concept covers it → UPDATE with new info, add daily log as source
   - New topic → CREATE a new `concepts/` article
5. Non-obvious connection between 2+ existing concepts → CREATE a `connections/` article
6. UPDATE `knowledge/index.md`
7. APPEND to `knowledge/log.md`

Guidelines:
- A single daily log typically touches 3–10 articles
- Prefer updating existing articles over creating near-duplicates
- Use `[[wikilinks]]` with full paths relative to `knowledge/`
- Encyclopedia style: factual, concise, self-contained
- Every article must have YAML frontmatter with title, sources, created, updated

### 2. Query (Index-Guided Retrieval)

1. Read `knowledge/index.md` (master catalog)
2. Identify 3–10 relevant articles
3. Read those articles in full
4. Synthesize an answer with `[[wikilink]]` citations
5. If `--file-back`: create a `knowledge/qa/` article and update index.md and log.md

**Why no RAG:** At personal KB scale (50–500 articles), the LLM reading a structured index outperforms cosine similarity. The LLM understands what you're really asking; embeddings find similar words.

### 3. Lint (Health Checks)

| Check | Type | Catches |
|-------|------|---------|
| Broken links | Structural | `[[wikilinks]]` to non-existent articles |
| Orphan pages | Structural | Articles with zero inbound links |
| Orphan sources | Structural | Daily logs not yet compiled |
| Stale articles | Structural | Source log changed since last compilation |
| Missing backlinks | Structural | A links to B but B doesn't link back |
| Sparse articles | Structural | Under 200 words |
| Contradictions | LLM | Conflicting claims across articles |

Output: `reports/lint-YYYY-MM-DD.md`.

---

## Project Structure

```
llm-memory-compiler/
├── lmc                          # Executable wrapper: ./lmc <cmd> (installs ~/.local/bin/lmc)
├── pyproject.toml               # Package config; entry points: lmc, llm-memory-compiler
├── AGENTS.md                    # This file — schema + technical reference
├── README.md                    # Overview + quick start
│
├── llm_memory/                  # Python package (canonical location for all logic)
│   ├── cli.py                   # Click CLI: lmc init/compile/query/lint/flush/inject-context/hook
│   ├── config.py                # Path constants, lmc_cmd(), reads .llm-memory/config.json
│   ├── utils.py                 # Shared helpers (hashing, wikilinks, state I/O)
│   ├── transcript.py            # JSONL extractors: Claude/Cursor format + Windsurf format
│   ├── compile.py               # Daily logs → knowledge articles
│   ├── query.py                 # Index-guided retrieval
│   ├── lint.py                  # 7 health checks
│   ├── flush.py                 # Background memory extraction + auto-compile trigger
│   │
│   ├── session_start.py         # Claude Code SessionStart hook logic
│   ├── session_end.py           # Claude Code SessionEnd hook logic
│   ├── pre_compact.py           # Claude Code PreCompact hook logic
│   ├── cursor_session_start.py  # Cursor sessionStart (different output format)
│   ├── cursor_session_end.py    # Cursor sessionEnd (uses reason, not status)
│   ├── cursor_pre_compact.py    # Cursor preCompact (uses conversation_id)
│   ├── cursor_stop.py           # Legacy Cursor stop hook (retained for compat)
│   ├── windsurf_hook.py         # Windsurf post_cascade_response_with_transcript
│   ├── generic_session_end.py   # Shared handler for all standard-protocol agents
│   │
│   ├── providers/               # LLM provider abstraction
│   │   ├── base.py              # LLMProvider ABC: call(prompt, *, allowed_tools, ...) → (text, cost)
│   │   ├── claude_agent.py      # claude-agent-sdk (default; uses ~/.claude/.credentials.json)
│   │   └── anthropic_api.py     # anthropic SDK (uses ANTHROPIC_API_KEY; no file tools)
│   │
│   └── agents/                  # Agent adapter registry
│       ├── base.py              # AgentAdapter ABC + StandardHookAdapter base class
│       ├── claude_code.py       # .claude/settings.json
│       ├── cursor.py            # .cursor/hooks.json
│       ├── windsurf.py          # ~/.codeium/windsurf/hooks.json
│       ├── gemini.py            # ~/.gemini/settings.json
│       ├── codex.py             # ~/.codex/hooks.json
│       ├── tabnine.py           # ~/.tabnine/agent/settings.json
│       ├── continue_dev.py      # ~/.continue/settings.json
│       ├── qwen.py              # ~/.qwen/settings.json
│       ├── devin.py             # .devin/hooks.v1.json
│       └── copilot.py           # .github/copilot-instructions.md
│
├── hooks/                       # Thin one-line wrappers → delegates to llm_memory/
│   ├── session-start.py         # → llm_memory.session_start
│   ├── session-end.py           # → llm_memory.session_end
│   ├── pre-compact.py           # → llm_memory.pre_compact
│   ├── cursor-session-start.py  # → llm_memory.cursor_session_start
│   ├── cursor-session-end.py    # → llm_memory.cursor_session_end
│   ├── cursor-pre-compact.py    # → llm_memory.cursor_pre_compact
│   ├── windsurf-hook.py         # → llm_memory.windsurf_hook
│   └── generic-session-end.py  # → llm_memory.generic_session_end
│
├── scripts/                     # Legacy stubs → delegates to llm_memory/
│   ├── compile.py, query.py, lint.py, flush.py
│   ├── config.py, utils.py      # Re-export from llm_memory.*
│
├── .llm-memory/                 # Runtime config + state (gitignored except config.json)
│   ├── config.json              # Written by lmc init: agent, api_provider, dirs
│   ├── state.json               # Compilation state (gitignored)
│   ├── last-flush.json          # Flush dedup state (gitignored)
│   ├── flush.log                # Hook process log (gitignored)
│   └── compile.log              # Compilation log (gitignored)
│
├── daily/                       # Source logs (gitignored)
├── knowledge/                   # Compiled knowledge (gitignored)
└── reports/                     # Lint reports (gitignored)
```

---

## The `lmc` Command

`lmc` is the primary interface. Three equivalent invocation forms:

```bash
./lmc <cmd>                   # repo-local wrapper (works immediately after clone)
uv run lmc <cmd>              # explicit uv invocation
lmc <cmd>                     # after lmc install writes ~/.local/bin/lmc
```

### Installation vs. Initialisation

These are separate steps run in order:

```bash
# 1. Install once per machine
./lmc install          # writes ~/.local/bin/lmc; verifies uv; syncs deps

# 2. Configure once per knowledge base
lmc init               # selects agent + LLM provider; writes hook config
```

`lmc install` writes `~/.local/bin/lmc` — a generated launcher script with the KB's absolute path hardcoded:

```bash
#!/usr/bin/env bash
# lmc — LLM Memory Compiler
exec uv run --directory /abs/path/to/llm-memory-compiler lmc "$@"
```

A custom install location is supported: `lmc install --bin-dir ~/bin`.

`lmc_cmd()` in `config.py` is used by all background subprocess spawns: returns `["lmc"]` if `lmc` is on PATH, otherwise `["uv", "run", "--directory", ROOT_DIR, "lmc"]`.

---

## Hook System

### Overview

Hooks fire automatically when your AI agent starts or ends a session, capturing the transcript for memory extraction and injecting the knowledge index as context.

All hook commands registered in agent config files use `lmc hook <name>`:
- **Project-level hooks** (Claude Code, Cursor, Devin, Windsurf): `./lmc hook <name>`
- **Global hooks** (Gemini, Codex, Tabnine, Continue, Qwen): `/abs/path/to/kb/lmc hook <name>`

### `lmc hook` Dispatcher

The `hook` subcommand group (hidden from `lmc --help`) dispatches to the appropriate Python module:

| Command | Module | Used by |
|---------|--------|---------|
| `lmc hook session-start` | `session_start` | Claude Code SessionStart |
| `lmc hook session-end` | `session_end` | Claude Code SessionEnd |
| `lmc hook pre-compact` | `pre_compact` | Claude Code PreCompact |
| `lmc hook cursor-session-start` | `cursor_session_start` | Cursor sessionStart |
| `lmc hook cursor-session-end` | `cursor_session_end` | Cursor sessionEnd |
| `lmc hook cursor-pre-compact` | `cursor_pre_compact` | Cursor preCompact |
| `lmc hook windsurf` | `windsurf_hook` | Windsurf post_cascade_response_with_transcript |
| `lmc hook generic-session-end` | `generic_session_end` | Gemini, Codex, Tabnine, Continue, Qwen, Devin |

### Agent-Specific Hook Details

#### Claude Code (`.claude/settings.json`)

```json
{
  "hooks": {
    "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": "./lmc hook session-start", "timeout": 15}]}],
    "PreCompact":   [{"matcher": "", "hooks": [{"type": "command", "command": "./lmc hook pre-compact",   "timeout": 10}]}],
    "SessionEnd":   [{"matcher": "", "hooks": [{"type": "command", "command": "./lmc hook session-end",   "timeout": 10}]}]
  }
}
```

- **SessionStart**: Reads `knowledge/index.md` + recent daily log; outputs `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}` (max 20,000 chars)
- **SessionEnd**: Reads transcript from `transcript_path`; spawns `lmc flush` as detached background process
- **PreCompact**: Same as SessionEnd; requires ≥ 5 turns; guards against missing `transcript_path`

#### Cursor (`.cursor/hooks.json`)

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [{"command": "./lmc hook cursor-session-start", "timeout": 15}],
    "sessionEnd":   [{"command": "./lmc hook cursor-session-end",   "timeout": 10}],
    "preCompact":   [{"command": "./lmc hook cursor-pre-compact",   "timeout": 10}]
  }
}
```

Key differences from Claude Code:
- **sessionStart** output format: `{"additional_context": "..."}` (top-level, not nested)
- **sessionEnd** payload: uses `session_id` (event-specific) + `reason` field; skips `reason=error`
- **preCompact** payload: uses `conversation_id` (common base, no `session_id`); requires ≥ 5 turns
- All three events provide `transcript_path` in the common base payload

#### Windsurf (`~/.codeium/windsurf/hooks.json`)

```json
{
  "hooks": {
    "post_cascade_response_with_transcript": [{
      "command": "./lmc hook windsurf",
      "working_directory": "/abs/path/to/kb"
    }]
  }
}
```

- Fires after **every response** (not just session end); `working_directory` sets CWD to KB root
- Transcript at `tool_info.transcript_path`; uses Windsurf's step-centric JSONL format
- `extract_windsurf_context()` in `transcript.py` handles `user_input`/`planner_response` entries
- 60-second dedup window in `flush.py` prevents redundant flushes within one session

#### Standard Protocol Agents (Gemini, Codex, Tabnine, Continue, Qwen)

These all inherited Claude Code's hook architecture. Config examples:

```json
// ~/.gemini/settings.json (SessionEnd)
// ~/.codex/hooks.json     (Stop — same payload schema)
// ~/.tabnine/agent/settings.json, ~/.continue/settings.json, ~/.qwen/settings.json
{
  "hooks": {
    "SessionEnd": [{
      "hooks": [{"type": "command", "command": "/abs/path/to/kb/lmc hook generic-session-end"}]
    }]
  }
}
```

All deliver `session_id` and `transcript_path` in the stdin JSON payload. `generic_session_end.py` handles all of them identically.

#### Devin CLI (`.devin/hooks.v1.json`)

```json
{
  "SessionEnd": [{
    "hooks": [{"type": "command", "command": "./lmc hook generic-session-end", "timeout": 30}]
  }]
}
```

Schema difference: top-level keys ARE the event names (no `"hooks"` wrapper). Project-level, so `./lmc` works.

### Background Flush Process

All hook scripts except sessionStart spawn `lmc flush <context_file> <session_id>` as a fully detached background process:
- **Windows:** `CREATE_NO_WINDOW` creation flag
- **Mac/Linux:** `start_new_session=True`

`flush.py` lifecycle:
1. Sets `CLAUDE_INVOKED_BY=memory_flush` (recursion guard — prevents hooks from re-firing)
2. Reads pre-extracted context from temp `.md` file
3. Skips if same session was flushed within 60 seconds (dedup via `.llm-memory/last-flush.json`)
4. Calls LLM (`allowed_tools=[]`, `max_turns=2`) — returns structured bullet points or `FLUSH_OK`
5. Appends result to `daily/YYYY-MM-DD.md`
6. Cleans up temp context file
7. **End-of-day auto-compile:** If past `COMPILE_AFTER_HOUR` (6 PM) and today's log hash differs from `state.json`, spawns `lmc compile` as another detached process

### JSONL Transcript Formats

**Claude Code / Cursor / standard agents** — message-centric:
```python
entry = json.loads(line)
msg = entry.get("message", {})       # nested under "message"
role = msg.get("role", "")           # "user" or "assistant"
content = msg.get("content", "")     # string or list of {"type":"text","text":"..."} blocks
```

**Windsurf** — step-centric:
```python
entry = json.loads(line)
entry_type = entry.get("type", "")   # "user_input" or "planner_response"
# user_input:       entry["user_input"]["user_response"]
# planner_response: entry["planner_response"]["response"]
```

Both extractors live in `llm_memory/transcript.py`.

---

## CLI Reference

```bash
lmc install [--bin-dir DIR]
lmc init [--agent AGENT] [--provider PROVIDER] [--knowledge-dir DIR] [--daily-dir DIR]
lmc compile [--all] [--file PATH] [--dry-run]
lmc query QUESTION [--file-back]
lmc lint [--structural-only]
lmc flush CONTEXT_FILE SESSION_ID
lmc inject-context
```

### `lmc install`

Verifies uv, syncs dependencies, writes the `lmc` launcher script to `~/.local/bin/` (or `--bin-dir`), and reports PATH status. Run once per machine after cloning.

### `lmc init`

Writes `.llm-memory/config.json` and installs agent hook config. Supports 10 agents:
`claude-code`, `cursor`, `windsurf`, `gemini`, `codex`, `tabnine`, `continue`, `qwen`, `devin`, `copilot`.

Non-interactive: `lmc init --agent cursor --provider anthropic-api`

### `lmc inject-context`

Builds context from `knowledge/index.md` + recent daily log, writes it to the configured agent's context file. Used by agents without sessionStart hooks (Windsurf, Gemini, etc. only get context through hook auto-capture; but non-hook agents like Copilot rely on this).

---

## Configuration

### `.llm-memory/config.json`

Written by `lmc init`. Committed to git (user-shareable). Runtime state files in the same directory are gitignored.

```json
{
  "agent": "claude-code",
  "api_provider": "claude-agent-sdk",
  "knowledge_dir": "knowledge",
  "daily_dir": "daily"
}
```

`config.py` loads this at import time via `Path.cwd()` as root. Falls back to defaults when absent (backward compat — existing setups require no migration).

### State Files (`.llm-memory/`, gitignored)

- `state.json` — SHA-256 hashes of compiled daily logs, timestamps, costs, query count
- `last-flush.json` — session_id + timestamp for flush dedup (60-second window)
- `flush.log`, `compile.log` — background process logs

When `.llm-memory/config.json` doesn't exist, state files fall back to `scripts/` for backward compatibility.

---

## LLM Provider Abstraction

`llm_memory/providers/` abstracts the LLM backend:

| Provider | Class | Credential | Tool use |
|----------|-------|-----------|----------|
| `claude-agent-sdk` (default) | `ClaudeAgentProvider` | `~/.claude/.credentials.json` | Full (Read, Write, Edit, Glob, Grep) |
| `anthropic-api` | `AnthropicAPIProvider` | `ANTHROPIC_API_KEY` | None (`allowed_tools=[]` only) |

`compile` and `query --file-back` require file tools and will error with `anthropic-api`. All other operations (flush, lint, query without file-back) work with either provider.

Install the optional Anthropic dependency: `uv add 'llm-memory-compiler[anthropic]'`

---

## Agent Adapter Architecture

`llm_memory/agents/base.py` defines two base classes:

**`AgentAdapter` (ABC):** `install(project_root)`, `write_context_file(project_root, context)`, `context_file_path(project_root)`, `supports_session_hooks: bool`

**`StandardHookAdapter(AgentAdapter)`:** Shared install logic for all agents using the JSON hooks protocol. Subclasses provide: `key`, `display_name`, `hook_event` (default `"SessionEnd"`), and `_config_file(project_root)`. The base class builds the config dict, merges with any existing config, and writes the file. Devin overrides `_build_hooks_entry` and `_merge` for its wrapper-free schema.

Adding a new agent: create a file in `agents/`, subclass `StandardHookAdapter` (4 lines), register in `agents/__init__.py`.

---

## Costs

| Operation | Cost |
|-----------|------|
| Compile one daily log | $0.45–0.65 |
| Query (no file-back) | $0.15–0.25 |
| Query (with file-back) | $0.25–0.40 |
| Full lint (with contradictions) | $0.15–0.25 |
| Structural lint only | $0.00 |
| Memory flush (per session) | $0.02–0.05 |

Costs increase as the knowledge base grows (more existing articles in compile context). Covered under Claude Max/Team/Enterprise with `claude-agent-sdk`.

---

## Dependencies

```toml
claude-agent-sdk>=0.1.29   # LLM calls with file tool support (default provider)
click>=8.0                 # CLI framework
rich>=13.0                 # Terminal colors, splash screen, progress output
python-dotenv>=1.0.0       # Environment variable management
tzdata>=2024.1             # Timezone data
# Optional:
anthropic>=0.40            # Direct Anthropic API (uv add 'llm-memory-compiler[anthropic]')
```

Python 3.12+, managed by [uv](https://docs.astral.sh/uv/).

---

## Conventions

- **Wikilinks:** Obsidian-style `[[path/to/article]]` without `.md` extension
- **Writing style:** Encyclopedia-style, factual, third-person where appropriate
- **Dates:** ISO 8601 (`YYYY-MM-DD` for dates, full ISO for log timestamps)
- **File naming:** lowercase, hyphens (`supabase-row-level-security.md`)
- **Frontmatter:** Every article must have YAML frontmatter: title, sources, created, updated

---

## Customization

### Additional Article Types

Add directories like `people/`, `projects/`, `tools/` to `knowledge/`. Define the format in this file (AGENTS.md) and update `llm_memory/utils.py`'s `list_wiki_articles()` to include them.

### Obsidian Integration

The knowledge base is pure markdown with `[[wikilinks]]` — works natively in Obsidian. Point a vault at `knowledge/` for graph view, backlinks, and search.

### Scaling Beyond Index-Guided Retrieval

At ~2,000+ articles, the index becomes too large for the context window. Add hybrid RAG (keyword + semantic) as a retrieval layer before the LLM. See Karpathy's recommendation of `qmd` by Tobi Lutke for search at scale.

### Changing the Compile Hour

`COMPILE_AFTER_HOUR = 18` in `llm_memory/flush.py`. Set to any hour (0–23) in local time.
