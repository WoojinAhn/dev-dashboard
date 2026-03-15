# lately — Design Spec

> Per-repo "what was I working on" CLI tool for parallel vibe coding.

## Problem

When vibe coding across 10+ Ghostty terminal windows, coming back after a day or two means: "What was I doing in each repo?" Scrolling through terminal history or asking Claude wastes time. No existing tool combines Claude Code session context + git state + manual notes into a per-repo summary.

## Solution

A single CLI command `lately` that scans `~/home/*`, collects git + Claude Code session data per repo, and outputs a one-line summary for each — sorted by last activity.

## Usage

```bash
lately                          # Scan all repos, show summaries sorted by last activity
lately --days 7                 # Only repos with activity in the last 7 days
lately --raw                    # No LLM summary — raw git + session title only (fast/offline)
lately --memo <repo> "message"  # Save a manual memo to the repo's .lately file
lately --exclude repo1,repo2    # Permanently exclude repos (saved to config)
lately --include repo1          # Remove repos from permanent exclusion
```

## Output

```
레포                    마지막 활동    요약
dev-dashboard           2시간 전      로컬 레포 모니터링 도구 설계 중, IDEAS.md 리서치 완료
kr-whisky-tracker       12일 전      가격 크롤러 UI 스크린샷 확인 중
GoPeaceTrain            5일 전       [memo] 텔레그램 알림 포맷 v2 작업 중단, 재개 필요
tab-labeler             20일 전      초기 설정 완료, 미커밋 변경 없음
```

## Data Sources (priority order)

### 1. Manual memo (highest priority)

- File: `{repo}/.lately`
- Plain text, one-liner describing current work status.
- Displayed with `[memo]` prefix, replaces LLM summary.

**Validity rule**: `.lately` mtime must be within 15 minutes of `max(last Claude session activity, last git commit)`. If stale, the memo is ignored (not deleted) and LLM summary is used instead.

### 2. Claude Code session history

- Path: `~/.claude/projects/-Users-woojin-home-{repo}/`
- Pick the most recently modified `*.jsonl` file.
- Extract:
  - `custom-title` entries (session name set via `/rename`)
  - Last `user` message text (first 200 chars)
  - Last `assistant` message text (first 200 chars)

### 3. Git data

```
last_commit_date    # git log -1 --format=%ci
last_commit_msg     # git log -1 --format=%s
branch              # git branch --show-current
dirty_count         # git status --porcelain | wc -l
has_remote          # git remote (non-empty = True)
```

## LLM Summary

- All repo data is batched into a single JSON payload.
- Sent to `claude -p --model haiku` in one call.
- Prompt asks for a one-line Korean summary per repo.
- Repos with valid `.lately` memos are excluded from the LLM call.

## Configuration

File: `~/.lately/config.json`

```json
{
  "exclude": ["repo1", "repo2"]
}
```

- `--exclude` adds to the list and prints confirmation.
- `--include` removes from the list and prints confirmation.

## Error Handling

| Scenario | Behavior |
|---|---|
| `claude` CLI not found | Fallback to `--raw` mode + warning |
| Git error on a repo | Skip that repo + one-line warning |
| No Claude session for a repo | Summarize from git data only |
| No matching `~/.claude/projects/` dir | Summarize from git data only |
| Haiku call fails (network, etc.) | Fallback to `--raw` output + warning |

## Project Structure

```
~/home/dev-dashboard/
├── lately.py          # Single-file script
├── pyproject.toml     # Metadata only (no external deps)
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-03-16-lately-design.md
```

- **Dependencies**: Python stdlib only. `claude` CLI invoked via `subprocess`.
- **Installation**: `alias lately="python3 ~/home/dev-dashboard/lately.py"`

## Scope Boundaries

**In scope (v1):**
- `~/home/*` scan (hardcoded)
- Git data collection
- Claude Code session JSONL parsing
- `.lately` memo with 15-min validity
- LLM summary via `claude -p --model haiku`
- `--raw`, `--days`, `--memo`, `--exclude`, `--include` flags
- `~/.lately/config.json` for persistent exclusions

**Out of scope (future):**
- Configurable scan paths
- TUI / web dashboard
- Running process / service detection
- AI session monitoring (busy/idle)
- Auto-memo generation on session exit
