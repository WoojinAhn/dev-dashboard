🇰🇷 [한국어](README.ko.md)

# cclanes

> "What was I working on?" — A per-repo work summary CLI for parallel vibe coding.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![No Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](https://docs.python.org/3/library/)

Scan all your local repos, collect git activity + Claude Code session history + manual memos, and get a sorted summary table — powered by LLM one-liners via `claude` CLI.

## Demo

```
$ cclanes
📋 cache 19 / new 2
Repo                        Last Active   Summary
──────────────────────────  ────────────  ────────────────────────────────────────
cclanes                     just now      cclanes CLI implementation complete
kr-whisky-tracker           11d ago       Whisky sorting feature implemented
GoPeaceTrain                10h ago       Hotel reservation monitoring started
```

## Why "lanes"?

Like lanes in a swimming pool — each repo is a lane, and the work inside (Claude Code sessions, commits, branches) is the swimmer training in it. You're the coach on the poolside: cclanes is your scoreboard, showing every lane's progress at a glance so you know exactly where to focus next.

## Features

- 🔍 **Auto-scan** — Discovers all repos under `~/home/*` automatically
- 🤖 **LLM summaries** — One-line work summaries via Claude Haiku, no API key needed (uses `claude` CLI)
- ⚡ **Smart caching** — Only re-analyzes repos that changed since last run
- 📝 **Manual memos** — Attach short notes to any repo (auto-expire after 15 min)
- 🚫 **Exclude/Include** — Permanently hide irrelevant repos from output
- 📊 **Raw mode** — Skip LLM, show raw git + session data directly
- 📦 **Zero dependencies** — Python 3.10+ stdlib only

## Quick Start

### Prerequisites

- Python 3.10+
- [`claude` CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated (for LLM summaries)
- Git repos under `~/home/`

### Installation

```bash
# Clone
git clone https://github.com/WoojinAhn/cclanes.git
cd cclanes

# Run directly
python cclanes.py

# Or add an alias
echo 'alias cclanes="python ~/home/cclanes/cclanes.py"' >> ~/.zshrc
```

### Usage

```bash
cclanes                          # Full scan with LLM summaries
cclanes --raw                    # No LLM, raw git + session data
cclanes --days 7                 # Only repos active in last 7 days
cclanes --lang en                # Force English output
cclanes --lang ko                # Force Korean output
cclanes --memo <repo> "message"  # Save manual memo
cclanes --exclude repo1,repo2    # Permanently exclude repos
cclanes --include repo1          # Remove from exclusion
```

> **Language:** Output language is auto-detected from your system locale. Use `--lang` to override.

## Claude Code Slash Command

You can register cclanes as a `/lanes` slash command in Claude Code:

```bash
# Create the command file
mkdir -p ~/.claude/commands
cat > ~/.claude/commands/lanes.md << 'EOF'
---
description: Show per-repo "what was I working on" summaries across ~/home/
argument-hint: [--raw] [--days N] [--lang en|ko]
allowed-tools: Bash
---

Run the `cclanes` CLI to show per-repo work summaries.

Flags (passed as-is to the script):
- `--raw`: No LLM summary — show raw git + session data only (fast)
- `--days N`: Only show repos with activity in the last N days
- `--lang en|ko`: Output language (default: auto-detect from system locale)

```bash
python3 ~/home/cclanes/cclanes.py $ARGUMENTS 2>&1
```

After the command completes, present the output as-is to the user.
EOF
```

Then type `/lanes` in any Claude Code session to run it.

## Configuration

### `~/.cclanes/config.json`

```json
{
  "exclude": ["docs", "archive"]
}
```

### `.cclanes` memo files

Drop a `.cclanes` file in any repo to attach a manual note:

```bash
cclanes --memo my-repo "Waiting for API review"
```

Memos are valid when written within 15 minutes of the last git commit or Claude session activity. Stale memos are ignored (not deleted) and the LLM summary is used instead.

## How It Works

```
~/home/* repos
     │
     ├── git log / status ──────┐
     ├── Claude Code sessions ──┤──→ Cache (skip unchanged) ──→ Claude Haiku ──→ Summary Table
     └── .cclanes memos ─────────┘
```

1. **Scan** — Walk `~/home/` subdirectories, identify git repos
2. **Collect** — Gather git log, uncommitted changes, Claude Code session history, manual memos
3. **Cache** — Compare repo state hash with cached version; skip unchanged repos
4. **Summarize** — Send changed repo data to Claude Haiku for one-line summary
5. **Display** — Sort by last activity, render as a clean terminal table

## Tech Stack

| Component | Choice |
|---|---|
| Language | Python 3.10+ (stdlib only) |
| LLM | Claude Haiku via `claude` CLI |
| Data sources | git, Claude Code sessions, manual memos |
| Storage | JSON file cache (`~/.cclanes/cache.json`) |

## License

[MIT](LICENSE)
