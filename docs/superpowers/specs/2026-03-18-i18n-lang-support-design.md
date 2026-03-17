# Design: i18n — LLM Summary Language Support

**Issue:** #12
**Date:** 2026-03-18
**Status:** Approved

## Problem

All user-facing strings in cclanes are hardcoded in Korean. As a public repo, the default language should be English, with automatic locale detection and explicit override.

## Solution: Dictionary-based i18n

### Language Detection

`detect_lang(args)` determines the active language code (`"en"` or `"ko"`):

1. `--lang en/ko` flag (explicit override) — highest priority
2. System locale (`locale.getdefaultlocale()` / `$LANG`) — if starts with `ko`, use `"ko"`
3. Fallback: `"en"`

Called once in `main()`, passed as `lang` parameter to downstream functions.

### String Dictionary

A top-level `STRINGS` dict with `"en"` and `"ko"` keys, containing all user-facing strings:

```python
STRINGS = {
    "en": {
        # Relative time
        "just_now": "just now",
        "minutes_ago": "{n}m ago",
        "hours_ago": "{n}h ago",
        "days_ago": "{n}d ago",
        "weeks_ago": "{n}w ago",
        "months_ago": "{n}mo ago",
        # Table headers
        "col_repo": "Repo",
        "col_last_activity": "Last Active",
        "col_summary": "Summary",
        "col_session": "Session",
        # Raw summary
        "session_prefix": "session",
        "commit_prefix": "commit",
        "uncommitted": "{n} uncommitted",
        "no_activity": "(no activity)",
        # CLI messages
        "excluded_added": "Added to exclude list: {repos}",
        "excluded_removed": "Removed from exclude list: {repos}",
        "memo_saved": "Memo saved: ~/home/{repo}/.cclanes",
        "no_active_repos": "No repos with recent activity.",
        "cache_stats": "cache {cached} / new {new}",
    },
    "ko": {
        "just_now": "방금",
        "minutes_ago": "{n}분 전",
        "hours_ago": "{n}시간 전",
        "days_ago": "{n}일 전",
        "weeks_ago": "{n}주 전",
        "months_ago": "{n}개월 전",
        "col_repo": "레포",
        "col_last_activity": "마지막 활동",
        "col_summary": "요약",
        "col_session": "세션",
        "session_prefix": "세션",
        "commit_prefix": "커밋",
        "uncommitted": "미커밋 {n}개",
        "no_activity": "(활동 없음)",
        "excluded_added": "제외 목록에 추가됨: {repos}",
        "excluded_removed": "제외 목록에서 제거됨: {repos}",
        "memo_saved": "메모 저장됨: ~/home/{repo}/.cclanes",
        "no_active_repos": "활동이 있는 레포가 없습니다.",
        "cache_stats": "캐시 {cached}개 / 새 분석 {new}개",
    },
}
```

Usage: `STRINGS[lang]["key"]` or `STRINGS[lang]["key"].format(n=3)`

### LLM Prompt

Not included in `STRINGS` — handled as a conditional block in `_call_llm` due to length and structural differences:

- `lang == "ko"`: current Korean prompt (30 char limit)
- `lang == "en"`: English prompt (50 char limit, since Korean has higher information density)

### Cache Key Separation

- `compute_cache_key(repo, lang)` — appends `lang` to the hash input
- Same repo with different languages produces different cache keys
- No structural change to cache file format; language switch naturally causes cache miss and regeneration

### Scope

**Changed (language-aware):**
- Relative time formatting (`format_relative_time`)
- Table headers and layout (`display_results`)
- Raw summary labels (`build_raw_summary`)
- CLI feedback messages (`main`)
- LLM prompt and summary language (`_call_llm`)
- Cache key computation (`compute_cache_key`)

**Unchanged (English-fixed):**
- stderr warnings (developer debugging)
- Cache/config file structure (backward compatible)

## Files to Modify

| File | Changes |
|---|---|
| `cclanes.py` | Add `STRINGS` dict, `detect_lang()`, `lang` param to functions, LLM prompt branching |
| `tests/test_cclanes.py` | Add tests for `detect_lang`, en/ko `format_relative_time`, en/ko `build_raw_summary`, lang-aware cache key |
| `~/.claude/commands/lanes.md` | Add `--lang en/ko` flag description |

## Tests to Add

- `test_detect_lang_default` — no `--lang`, locale fallback
- `test_detect_lang_override` — `--lang en` overrides locale
- `test_format_relative_time_en` — English relative time (`3h ago`, etc.)
- `test_build_raw_summary_en` — English raw summary (`commit:`, `session:`, etc.)
- `test_cache_key_includes_lang` — same repo, different lang → different cache key
