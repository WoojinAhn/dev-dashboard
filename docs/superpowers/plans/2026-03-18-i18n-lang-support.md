# i18n Language Support Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all user-facing strings language-aware (en/ko) with locale auto-detection and `--lang` override.

**Architecture:** Dictionary-based i18n with a top-level `STRINGS` dict. `detect_lang()` resolves language once, then passes `lang` param through all output functions. Cache keys include language for separation.

**Tech Stack:** Python stdlib (`locale`, `os`, `argparse`)

**Spec:** `docs/superpowers/specs/2026-03-18-i18n-lang-support-design.md`

---

## File Map

| File | Responsibility |
|---|---|
| `cclanes.py` | All production code — STRINGS dict, detect_lang(), i18n-aware output functions |
| `tests/test_cclanes.py` | All tests |
| `~/.claude/commands/lanes.md` | Slash command help text |

---

### Task 1: Add STRINGS dict and detect_lang()

**Files:**
- Modify: `cclanes.py:1-16` (imports + new constants)
- Test: `tests/test_cclanes.py`

- [ ] **Step 1: Write failing tests for detect_lang**

Add to `tests/test_cclanes.py`:

```python
def test_detect_lang_override_en():
    """--lang en overrides system locale."""
    args = lately.parse_args(["--lang", "en"])
    assert lately.detect_lang(args) == "en"


def test_detect_lang_override_ko():
    """--lang ko overrides system locale."""
    args = lately.parse_args(["--lang", "ko"])
    assert lately.detect_lang(args) == "ko"


def test_detect_lang_default_fallback(monkeypatch):
    """No --lang and non-Korean locale falls back to en."""
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    args = lately.parse_args([])
    assert lately.detect_lang(args) == "en"


def test_detect_lang_korean_locale(monkeypatch):
    """Korean locale auto-detects ko."""
    monkeypatch.setenv("LANG", "ko_KR.UTF-8")
    args = lately.parse_args([])
    assert lately.detect_lang(args) == "ko"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cclanes.py -k "detect_lang" -v`
Expected: FAIL — `parse_args` doesn't accept `--lang`, `detect_lang` doesn't exist

- [ ] **Step 3: Add --lang to parse_args, add STRINGS dict and detect_lang**

In `cclanes.py`, add `import locale` and `import os` to imports.

Add `STRINGS` dict (from spec) after the existing constants (`CLAUDE_PROJECTS_DIR`).

Add `detect_lang` function:

```python
def detect_lang(args: argparse.Namespace) -> str:
    """Determine UI language from --lang flag or system locale."""
    if args.lang:
        return args.lang
    # Check system locale
    lang_env = os.environ.get("LANG", "")
    if lang_env.startswith("ko"):
        return "ko"
    try:
        loc = locale.getlocale()[0]
        if loc and loc.startswith("ko"):
            return "ko"
    except ValueError:
        pass
    return "en"
```

Add `--lang` argument to `parse_args`:

```python
parser.add_argument("--lang", choices=["en", "ko"], default=None,
                    help="Output language (default: auto-detect from locale)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cclanes.py -k "detect_lang" -v`
Expected: all 4 PASS

- [ ] **Step 5: Commit**

```bash
git add cclanes.py tests/test_cclanes.py
git commit -m "feat: add STRINGS dict, detect_lang(), --lang flag"
```

---

### Task 2: i18n format_relative_time

**Files:**
- Modify: `format_relative_time` function in `cclanes.py`
- Test: `tests/test_cclanes.py`

Note: line numbers shift after Task 1. Use function names to locate code.

- [ ] **Step 1: Update existing test + write new failing tests**

First, update the existing `test_format_relative_time` to pass `lang="ko"` to all calls (since the default will change to `"en"`). Then add new tests:

```python
def test_format_relative_time_en():
    """English relative time strings."""
    now = datetime.now(tz=timezone.utc)
    assert lately.format_relative_time(now - timedelta(seconds=10), now, lang="en") == "just now"
    assert lately.format_relative_time(now - timedelta(minutes=30), now, lang="en") == "30m ago"
    assert lately.format_relative_time(now - timedelta(hours=3), now, lang="en") == "3h ago"
    assert lately.format_relative_time(now - timedelta(days=2), now, lang="en") == "2d ago"
    assert lately.format_relative_time(now - timedelta(days=14), now, lang="en") == "2w ago"


def test_format_relative_time_ko():
    """Korean relative time strings still work."""
    now = datetime.now(tz=timezone.utc)
    assert lately.format_relative_time(now - timedelta(minutes=30), now, lang="ko") == "30분 전"
    assert lately.format_relative_time(now - timedelta(hours=3), now, lang="ko") == "3시간 전"
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `pytest tests/test_cclanes.py -k "format_relative_time" -v`
Expected: new tests FAIL — `format_relative_time` doesn't accept `lang`

- [ ] **Step 3: Add lang param to format_relative_time**

```python
def format_relative_time(dt: datetime, now: datetime | None = None, lang: str = "en") -> str:
    """Format datetime as relative time string."""
    if now is None:
        now = datetime.now(tz=timezone.utc)
    s = STRINGS[lang]
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return s["just_now"]
    minutes = seconds // 60
    if minutes < 60:
        return s["minutes_ago"].format(n=minutes)
    hours = minutes // 60
    if hours < 24:
        return s["hours_ago"].format(n=hours)
    days = hours // 24
    if days < 14:
        return s["days_ago"].format(n=days)
    weeks = days // 7
    if weeks < 8:
        return s["weeks_ago"].format(n=weeks)
    months = days // 30
    return s["months_ago"].format(n=months)
```

- [ ] **Step 4: Run all format_relative_time tests**

Run: `pytest tests/test_cclanes.py -k "format_relative_time" -v`
Expected: all PASS (existing test now uses `lang="ko"`, new tests use `lang="en"` and `lang="ko"`)

- [ ] **Step 5: Commit**

```bash
git add cclanes.py tests/test_cclanes.py
git commit -m "feat: i18n format_relative_time with lang param"
```

---

### Task 3: i18n build_raw_summary

**Files:**
- Modify: `build_raw_summary` function in `cclanes.py`
- Test: `tests/test_cclanes.py`

- [ ] **Step 1: Update existing tests + write new failing tests**

First, update existing `test_build_raw_summary` and `test_build_raw_summary_with_memo` to pass `lang="ko"` (since default will change to `"en"`). Then add new tests:

```python
def test_build_raw_summary_en():
    """English raw summary uses English labels."""
    repo = {
        "name": "myrepo",
        "git": {"branch": "main", "last_commit_msg": "fix bug", "dirty_count": 2,
                "last_commit_date": datetime.now(tz=timezone.utc), "has_remote": True},
        "claude": {"custom_title": "fixing-login", "last_user_msg": None,
                   "last_assistant_msg": None, "mtime": datetime.now(tz=timezone.utc)},
        "memo": None,
        "last_activity": datetime.now(tz=timezone.utc),
    }
    summary = lately.build_raw_summary(repo, lang="en")
    assert "session: fixing-login" in summary
    assert "commit: fix bug" in summary
    assert "2 uncommitted" in summary


def test_build_raw_summary_no_activity_en():
    """No activity shows English message."""
    repo = {
        "name": "empty",
        "git": {"branch": "main", "last_commit_msg": None, "dirty_count": 0,
                "last_commit_date": None, "has_remote": False},
        "claude": None,
        "memo": None,
        "last_activity": None,
    }
    summary = lately.build_raw_summary(repo, lang="en")
    assert summary == "(no activity)"
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `pytest tests/test_cclanes.py -k "build_raw_summary" -v`
Expected: new tests FAIL — `build_raw_summary` doesn't accept `lang`

- [ ] **Step 3: Add lang param to build_raw_summary**

```python
def build_raw_summary(repo: dict, lang: str = "en") -> str:
    """Build a raw (no-LLM) summary string for a repo."""
    s = STRINGS[lang]
    if repo["memo"]:
        return f"[memo] {repo['memo']}"

    parts = []
    git = repo["git"]
    claude = repo.get("claude")

    if claude and claude.get("custom_title"):
        parts.append(f"{s['session_prefix']}: {claude['custom_title']}")

    if git["last_commit_msg"]:
        parts.append(f"{s['commit_prefix']}: {git['last_commit_msg']}")

    if git["dirty_count"] > 0:
        parts.append(s["uncommitted"].format(n=git["dirty_count"]))

    return ", ".join(parts) if parts else s["no_activity"]
```

- [ ] **Step 4: Run all build_raw_summary tests**

Run: `pytest tests/test_cclanes.py -k "build_raw_summary" -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add cclanes.py tests/test_cclanes.py
git commit -m "feat: i18n build_raw_summary with lang param"
```

---

### Task 4: i18n compute_cache_key

**Files:**
- Modify: `compute_cache_key` function in `cclanes.py`
- Test: `tests/test_cclanes.py`

- [ ] **Step 1: Update existing tests + write new failing test**

First, update existing `test_compute_cache_key` and `test_compute_cache_key_no_claude` to pass `lang="en"` to all `compute_cache_key` calls. Also update `test_get_cached_summaries` and `test_split_cached_miss` to pass `lang="en"`. Then add:

```python
def test_cache_key_includes_lang():
    """Same repo with different lang produces different cache keys."""
    repo = {
        "name": "myrepo",
        "git": {"branch": "main", "last_commit_msg": "fix", "dirty_count": 0,
                "last_commit_date": datetime(2026, 3, 15, tzinfo=timezone.utc), "has_remote": True},
        "claude": None,
        "memo": None,
        "last_activity": datetime(2026, 3, 15, tzinfo=timezone.utc),
    }
    key_en = lately.compute_cache_key(repo, lang="en")
    key_ko = lately.compute_cache_key(repo, lang="ko")
    assert key_en != key_ko
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cclanes.py -k "cache_key_includes_lang" -v`
Expected: FAIL — `compute_cache_key` doesn't accept `lang`

- [ ] **Step 3: Add lang param to compute_cache_key**

```python
def compute_cache_key(repo: dict, lang: str = "en") -> str:
    """Compute a cache key based on git, claude session state, and language."""
    parts = []
    git = repo["git"]
    if git["last_commit_msg"]:
        parts.append(git["last_commit_msg"])
    if git["last_commit_date"]:
        parts.append(str(git["last_commit_date"]))
    parts.append(str(git["dirty_count"]))

    claude = repo.get("claude")
    if claude and claude.get("mtime"):
        parts.append(str(claude["mtime"]))
    if claude and claude.get("custom_title"):
        parts.append(claude["custom_title"])

    parts.append(lang)
    raw = "|".join(parts)
    return hashlib.md5(raw.encode()).hexdigest()
```

- [ ] **Step 4: Run all cache key tests**

Run: `pytest tests/test_cclanes.py -k "cache_key" -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add cclanes.py tests/test_cclanes.py
git commit -m "feat: include lang in cache key for per-language separation"
```

---

### Task 5: i18n display_results

**Files:**
- Modify: `display_results` function in `cclanes.py`
- Test: `tests/test_cclanes.py`

- [ ] **Step 1: Write failing tests for display_results**

```python
def test_display_results_en(capsys):
    """English table headers are used when lang=en."""
    repos = [{
        "name": "myrepo",
        "git": {"branch": "main", "last_commit_msg": "fix", "dirty_count": 0,
                "last_commit_date": datetime.now(tz=timezone.utc), "has_remote": True},
        "claude": None,
        "memo": None,
        "last_activity": datetime.now(tz=timezone.utc),
    }]
    lately.display_results(repos, {"myrepo": "test summary"}, raw=False, lang="en")
    output = capsys.readouterr().out
    assert "Repo" in output
    assert "Last Active" in output
    assert "Summary" in output


def test_display_results_ko(capsys):
    """Korean table headers are used when lang=ko."""
    repos = [{
        "name": "myrepo",
        "git": {"branch": "main", "last_commit_msg": "fix", "dirty_count": 0,
                "last_commit_date": datetime.now(tz=timezone.utc), "has_remote": True},
        "claude": None,
        "memo": None,
        "last_activity": datetime.now(tz=timezone.utc),
    }]
    lately.display_results(repos, {"myrepo": "test summary"}, raw=False, lang="ko")
    output = capsys.readouterr().out
    assert "레포" in output
    assert "마지막 활동" in output


def test_display_results_empty_en(capsys):
    """No repos shows English empty message."""
    lately.display_results([], {}, raw=False, lang="en")
    output = capsys.readouterr().out
    assert "No repos with recent activity." in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cclanes.py -k "display_results" -v`
Expected: FAIL — `display_results` doesn't accept `lang`

- [ ] **Step 3: Add lang param to display_results**

Replace hardcoded Korean headers with `STRINGS[lang]` lookups. Add `lang: str = "en"` param. Pass `lang` to `format_relative_time` and `build_raw_summary` calls within the function. Replace `"활동이 있는 레포가 없습니다."` with `STRINGS[lang]["no_active_repos"]`.

- [ ] **Step 4: Run all tests**

Run: `pytest tests/test_cclanes.py -k "display_results" -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add cclanes.py tests/test_cclanes.py
git commit -m "feat: i18n display_results with lang param"
```

---

### Task 6: i18n _call_llm and get_llm_summaries

**Files:**
- Modify: `_call_llm`, `get_llm_summaries`, `split_cached` functions in `cclanes.py`

- [ ] **Step 1: Add lang param to _call_llm**

```python
def _call_llm(payload: list[dict], lang: str = "en") -> dict[str, str]:
    """Call claude -p --model haiku with a payload. Returns repo→summary dict."""
    if not payload:
        return {}

    if lang == "ko":
        prompt = (
            "다음 JSON은 여러 로컬 Git 레포의 최근 활동 데이터입니다.\n"
            "각 레포별로 \"지금 뭘 하고 있었는지\"를 한 줄(30자 이내)로 요약해주세요.\n"
            "커밋 메시지, 세션 타이틀, 마지막 대화 내용을 종합해서 판단하세요.\n\n"
            "출력 형식 (JSON만, 다른 텍스트 없이):\n"
            "{\"repo_name\": \"요약\", ...}\n\n"
            f"데이터:\n{json.dumps(payload, ensure_ascii=False)}"
        )
    else:
        prompt = (
            "The following JSON contains recent activity data from local Git repos.\n"
            "Summarize what was being worked on for each repo in one line (max 50 chars).\n"
            "Use commit messages, session titles, and last conversation to judge.\n\n"
            "Output format (JSON only, no other text):\n"
            "{\"repo_name\": \"summary\", ...}\n\n"
            f"Data:\n{json.dumps(payload, ensure_ascii=False)}"
        )
    # ... rest of function unchanged
```

- [ ] **Step 2: Add lang param to split_cached and get_llm_summaries**

Thread `lang` through `get_llm_summaries(repos, lang="en")` → `split_cached(repos, cache, lang)` → `compute_cache_key(repo, lang)`, and → `_call_llm(payload, lang)`.

Update the `cache_stats` stderr message to use `STRINGS[lang]["cache_stats"]`:
```python
print(f"📋 {STRINGS[lang]['cache_stats'].format(cached=cache_count, new=new_count)}", file=sys.stderr)
```

- [ ] **Step 3: Run all tests**

Run: `pytest tests/test_cclanes.py -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add cclanes.py
git commit -m "feat: i18n _call_llm and get_llm_summaries with lang param"
```

---

### Task 7: Wire lang through main() and convert stderr to English

**Files:**
- Modify: `main` function in `cclanes.py`
- Modify: stderr messages throughout `cclanes.py`

Note: This also fixes the `.lately` → `.cclanes` bug in `--memo` output (incidental bugfix via STRINGS adoption).

- [ ] **Step 1: Update main() to call detect_lang and pass lang everywhere**

```python
def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    lang = detect_lang(args)

    # --exclude
    if args.exclude:
        repos_list = [r.strip() for r in args.exclude.split(",")]
        cfg = load_config()
        cfg = add_excludes(cfg, repos_list)
        save_config(cfg)
        print(STRINGS[lang]["excluded_added"].format(repos=", ".join(repos_list)))
        return

    # --include
    if args.include:
        repos_list = [r.strip() for r in args.include.split(",")]
        cfg = load_config()
        cfg = remove_excludes(cfg, repos_list)
        save_config(cfg)
        print(STRINGS[lang]["excluded_removed"].format(repos=", ".join(repos_list)))
        return

    # --memo
    if args.memo:
        repo_name, message = args.memo
        memo_path = HOME_DIR / repo_name / ".cclanes"
        if not (HOME_DIR / repo_name).is_dir():
            print(f"Error: ~/home/{repo_name} directory not found.", file=sys.stderr)
            sys.exit(1)
        memo_path.write_text(message + "\n")
        print(STRINGS[lang]["memo_saved"].format(repo=repo_name))
        return

    repos = scan_repos()

    if args.days is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=args.days)
        repos = [r for r in repos if r["last_activity"] and r["last_activity"] >= cutoff]

    summaries = {}
    if not args.raw:
        summaries = get_llm_summaries(repos, lang=lang)
        if not summaries and any(r["memo"] is None for r in repos):
            print("Warning: LLM summary failed, showing raw mode.\n", file=sys.stderr)

    display_results(repos, summaries, raw=args.raw, lang=lang)
```

- [ ] **Step 2: Convert all stderr messages to English**

Find and replace all Korean stderr messages in `cclanes.py`:
- `"⚠ 세션 파일 읽기 실패"` → `"Warning: failed to read session file"`
- `"⚠ claude CLI 호출 실패"` → `"Warning: claude CLI call failed"`
- `"⚠ claude CLI를 찾을 수 없습니다. --raw 모드로 전환합니다."` → `"Warning: claude CLI not found. Falling back to --raw mode."`
- `"⚠ claude CLI 응답 시간 초과"` → `"Warning: claude CLI response timed out"`
- `"⚠ LLM 응답 파싱 실패"` → `"Warning: failed to parse LLM response"`
- `"⚠ LLM 요약 실패, raw 모드로 표시합니다."` → `"Warning: LLM summary failed, showing raw mode."`

- [ ] **Step 3: Run all tests**

Run: `pytest tests/test_cclanes.py -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add cclanes.py
git commit -m "feat: wire lang through main(), convert stderr to English"
```

---

### Task 8: Update slash command and final verification

**Files:**
- Modify: `~/.claude/commands/lanes.md`

- [ ] **Step 1: Update lanes.md**

```markdown
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
python3 /Users/woojin/home/cclanes/cclanes.py $ARGUMENTS 2>&1
```

After the command completes, present the output as-is to the user. If the user wants to switch to a specific repo or continue work, help them navigate.
```

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/test_cclanes.py -v`
Expected: all tests PASS

- [ ] **Step 3: Manual smoke test**

```bash
python3 cclanes.py --raw --lang en
python3 cclanes.py --raw --lang ko
python3 cclanes.py --raw  # should auto-detect
```

- [ ] **Step 4: Commit**

```bash
git add ~/.claude/commands/lanes.md
git commit -m "docs: add --lang flag to /lanes slash command"
```
