import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cclanes as lately


def test_load_config_empty():
    """No config file → empty exclude list."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "config.json"
        cfg = lately.load_config(path)
        assert cfg == {"exclude": []}


def test_load_config_existing():
    """Existing config is loaded correctly."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "config.json"
        path.write_text(json.dumps({"exclude": ["repo1", "repo2"]}))
        cfg = lately.load_config(path)
        assert cfg["exclude"] == ["repo1", "repo2"]


def test_save_config():
    """Config is saved and can be reloaded."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "config.json"
        cfg = {"exclude": ["a", "b"]}
        lately.save_config(cfg, path)
        loaded = json.loads(path.read_text())
        assert loaded["exclude"] == ["a", "b"]


def test_add_exclude():
    """--exclude adds repos to config."""
    cfg = {"exclude": ["a"]}
    cfg = lately.add_excludes(cfg, ["b", "c"])
    assert sorted(cfg["exclude"]) == ["a", "b", "c"]


def test_add_exclude_no_duplicates():
    """--exclude does not duplicate existing entries."""
    cfg = {"exclude": ["a"]}
    cfg = lately.add_excludes(cfg, ["a", "b"])
    assert sorted(cfg["exclude"]) == ["a", "b"]


def test_remove_exclude():
    """--include removes repos from config."""
    cfg = {"exclude": ["a", "b", "c"]}
    cfg = lately.remove_excludes(cfg, ["b"])
    assert cfg["exclude"] == ["a", "c"]


def test_remove_exclude_missing():
    """--include with non-existing repo is a no-op."""
    cfg = {"exclude": ["a"]}
    cfg = lately.remove_excludes(cfg, ["z"])
    assert cfg["exclude"] == ["a"]


def test_collect_git_data_valid_repo(tmp_path):
    """Collects git data from a real git repo."""
    repo = tmp_path / "testrepo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
    (repo / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init commit"], cwd=repo, capture_output=True)

    data = lately.collect_git_data(repo)
    assert data["branch"] is not None
    assert data["last_commit_msg"] == "init commit"
    assert data["last_commit_date"] is not None
    assert data["dirty_count"] == 0
    assert data["has_remote"] is False


def test_collect_git_data_dirty(tmp_path):
    """Dirty count reflects uncommitted changes."""
    repo = tmp_path / "testrepo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
    (repo / "file.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)
    (repo / "file.txt").write_text("changed")
    (repo / "new.txt").write_text("new")

    data = lately.collect_git_data(repo)
    assert data["dirty_count"] == 2


def test_collect_git_data_not_a_repo(tmp_path):
    """Non-git directory returns None."""
    data = lately.collect_git_data(tmp_path)
    assert data is None


def test_parse_claude_session(tmp_path):
    """Extracts custom-title and last messages from JSONL."""
    jsonl = tmp_path / "session.jsonl"
    lines = [
        json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "Fix the login bug"}]}, "timestamp": "2026-03-15T10:00:00Z"}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "I'll fix the login validation..."}]}, "timestamp": "2026-03-15T10:01:00Z"}),
        json.dumps({"type": "custom-title", "customTitle": "fix-login-bug", "sessionId": "abc"}),
        json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "Now add tests for it"}]}, "timestamp": "2026-03-15T10:05:00Z"}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Adding test cases for the login..."}]}, "timestamp": "2026-03-15T10:06:00Z"}),
    ]
    jsonl.write_text("\n".join(lines) + "\n")

    data = lately.parse_claude_session(jsonl)
    assert data["custom_title"] == "fix-login-bug"
    assert "Now add tests" in data["last_user_msg"]
    assert "Adding test cases" in data["last_assistant_msg"]


def test_parse_claude_session_no_title(tmp_path):
    """Session without custom-title returns None for title."""
    jsonl = tmp_path / "session.jsonl"
    lines = [
        json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "hello"}]}, "timestamp": "2026-03-15T10:00:00Z"}),
    ]
    jsonl.write_text("\n".join(lines) + "\n")

    data = lately.parse_claude_session(jsonl)
    assert data["custom_title"] is None
    assert "hello" in data["last_user_msg"]


def test_parse_claude_session_empty(tmp_path):
    """Empty file returns None."""
    jsonl = tmp_path / "session.jsonl"
    jsonl.write_text("")
    data = lately.parse_claude_session(jsonl)
    assert data is None


def test_find_claude_session_for_repo(tmp_path):
    """Finds the most recent JSONL file for a repo."""
    proj_dir = tmp_path / "-Users-woojin-home-myrepo"
    proj_dir.mkdir()
    old = proj_dir / "old-session.jsonl"
    new = proj_dir / "new-session.jsonl"
    old.write_text(json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "old"}]}, "timestamp": "2026-03-10T00:00:00Z"}) + "\n")
    import time; time.sleep(0.05)
    new.write_text(json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "new"}]}, "timestamp": "2026-03-15T00:00:00Z"}) + "\n")

    result = lately.find_claude_session(tmp_path, "myrepo")
    assert result is not None
    assert result.name == "new-session.jsonl"


# --- Memo validity tests ---

def test_memo_valid_within_15min():
    """Memo is valid when within 15 min of last activity."""
    now = datetime.now(tz=timezone.utc)
    assert lately.is_memo_valid(
        memo_mtime=now,
        last_activity=now - timedelta(minutes=10),
    ) is True


def test_memo_invalid_after_15min():
    """Memo is stale when > 15 min from last activity."""
    now = datetime.now(tz=timezone.utc)
    assert lately.is_memo_valid(
        memo_mtime=now - timedelta(hours=2),
        last_activity=now,
    ) is False


def test_memo_valid_no_activity():
    """Memo is always valid when no other activity exists."""
    now = datetime.now(tz=timezone.utc)
    assert lately.is_memo_valid(
        memo_mtime=now,
        last_activity=None,
    ) is True


def test_memo_valid_memo_after_activity():
    """Memo written 5 min after last commit is valid."""
    now = datetime.now(tz=timezone.utc)
    assert lately.is_memo_valid(
        memo_mtime=now,
        last_activity=now - timedelta(minutes=5),
    ) is True


def test_memo_invalid_activity_much_later():
    """Memo from yesterday, activity today → stale."""
    now = datetime.now(tz=timezone.utc)
    assert lately.is_memo_valid(
        memo_mtime=now - timedelta(days=1),
        last_activity=now,
    ) is False


# --- Output formatting tests ---

def test_format_relative_time():
    """Formats datetime as Korean relative time string."""
    now = datetime.now(tz=timezone.utc)
    assert lately.format_relative_time(now - timedelta(minutes=30), now, lang="ko") == "30분 전"
    assert lately.format_relative_time(now - timedelta(hours=3), now, lang="ko") == "3시간 전"
    assert lately.format_relative_time(now - timedelta(days=2), now, lang="ko") == "2일 전"
    assert lately.format_relative_time(now - timedelta(days=14), now, lang="ko") == "2주 전"


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


def test_build_raw_summary():
    """Builds raw summary string from repo data."""
    repo = {
        "name": "myrepo",
        "git": {"branch": "main", "last_commit_msg": "fix bug", "dirty_count": 2,
                "last_commit_date": datetime.now(tz=timezone.utc), "has_remote": True},
        "claude": {"custom_title": "fixing-login", "last_user_msg": None,
                   "last_assistant_msg": None, "mtime": datetime.now(tz=timezone.utc)},
        "memo": None,
        "last_activity": datetime.now(tz=timezone.utc),
    }
    summary = lately.build_raw_summary(repo, lang="ko")
    assert "fix bug" in summary
    assert "fixing-login" in summary


def test_build_raw_summary_with_memo():
    """Memo overrides other summary content."""
    repo = {
        "name": "myrepo",
        "git": {"branch": "main", "last_commit_msg": "fix bug", "dirty_count": 0,
                "last_commit_date": datetime.now(tz=timezone.utc), "has_remote": True},
        "claude": None,
        "memo": "작업 중단, PR 리뷰 대기",
        "last_activity": datetime.now(tz=timezone.utc),
    }
    summary = lately.build_raw_summary(repo, lang="ko")
    assert "[memo]" in summary
    assert "작업 중단" in summary


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


# --- LLM payload tests ---

def test_build_llm_payload_excludes_memo():
    """Repos with valid memos are excluded from LLM payload."""
    repos = [
        {"name": "a", "git": {"branch": "main", "last_commit_msg": "fix", "dirty_count": 0}, "claude": None, "memo": "working on X", "last_activity": datetime.now(tz=timezone.utc)},
        {"name": "b", "git": {"branch": "dev", "last_commit_msg": "add feature", "dirty_count": 1}, "claude": None, "memo": None, "last_activity": datetime.now(tz=timezone.utc)},
    ]
    payload = lately.build_llm_payload(repos)
    assert len(payload) == 1
    assert payload[0]["name"] == "b"


def test_build_llm_payload_truncates():
    """Long messages are truncated to 500 chars."""
    repos = [
        {
            "name": "c",
            "git": {"branch": "main", "last_commit_msg": "x", "dirty_count": 0},
            "claude": {"custom_title": "t", "last_user_msg": "a" * 1000, "last_assistant_msg": "b" * 1000, "mtime": datetime.now(tz=timezone.utc)},
            "memo": None,
            "last_activity": datetime.now(tz=timezone.utc),
        },
    ]
    payload = lately.build_llm_payload(repos)
    assert len(payload[0]["last_user_msg"]) == 500
    assert len(payload[0]["last_assistant_msg"]) == 500


# --- Cache tests ---

def test_compute_cache_key():
    """Cache key changes when git or session data changes."""
    repo = {
        "name": "myrepo",
        "git": {"branch": "main", "last_commit_msg": "fix", "dirty_count": 0,
                "last_commit_date": datetime(2026, 3, 15, tzinfo=timezone.utc), "has_remote": True},
        "claude": {"custom_title": "t", "last_user_msg": "x", "last_assistant_msg": "y",
                   "mtime": datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)},
        "memo": None,
        "last_activity": datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
    }
    key1 = lately.compute_cache_key(repo)

    # Different commit → different key
    repo2 = {**repo, "git": {**repo["git"], "last_commit_msg": "new commit"}}
    key2 = lately.compute_cache_key(repo2)
    assert key1 != key2

    # Different session mtime → different key
    repo3 = {**repo, "claude": {**repo["claude"], "mtime": datetime(2026, 3, 16, tzinfo=timezone.utc)}}
    key3 = lately.compute_cache_key(repo3)
    assert key1 != key3


def test_compute_cache_key_no_claude():
    """Cache key works without Claude session data."""
    repo = {
        "name": "myrepo",
        "git": {"branch": "main", "last_commit_msg": "fix", "dirty_count": 0,
                "last_commit_date": datetime(2026, 3, 15, tzinfo=timezone.utc), "has_remote": True},
        "claude": None,
        "memo": None,
        "last_activity": datetime(2026, 3, 15, tzinfo=timezone.utc),
    }
    key = lately.compute_cache_key(repo)
    assert isinstance(key, str)
    assert len(key) > 0


def test_load_save_cache():
    """Cache can be saved and loaded."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cache.json"
        cache = {"myrepo": {"key": "abc", "summary": "doing stuff"}}
        lately.save_cache(cache, path)
        loaded = lately.load_cache(path)
        assert loaded["myrepo"]["summary"] == "doing stuff"


def test_load_cache_empty():
    """No cache file → empty dict."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cache.json"
        assert lately.load_cache(path) == {}


def test_get_cached_summaries():
    """Cached summaries are returned for repos with matching keys."""
    repos = [
        {"name": "a", "git": {"branch": "main", "last_commit_msg": "x", "dirty_count": 0,
                               "last_commit_date": datetime(2026, 3, 15, tzinfo=timezone.utc), "has_remote": False},
         "claude": None, "memo": None, "last_activity": datetime(2026, 3, 15, tzinfo=timezone.utc)},
    ]
    key = lately.compute_cache_key(repos[0])
    cache = {"a": {"key": key, "summary": "cached result"}}
    cached, uncached = lately.split_cached(repos, cache)
    assert cached == {"a": "cached result"}
    assert uncached == []


def test_split_cached_miss():
    """Repos with stale cache keys are returned as uncached."""
    repos = [
        {"name": "a", "git": {"branch": "main", "last_commit_msg": "NEW", "dirty_count": 0,
                               "last_commit_date": datetime(2026, 3, 15, tzinfo=timezone.utc), "has_remote": False},
         "claude": None, "memo": None, "last_activity": datetime(2026, 3, 15, tzinfo=timezone.utc)},
    ]
    cache = {"a": {"key": "old_stale_key", "summary": "old result"}}
    cached, uncached = lately.split_cached(repos, cache)
    assert cached == {}
    assert len(uncached) == 1


# --- Language detection tests ---

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
    monkeypatch.setattr("locale.getlocale", lambda: ("en_US", "UTF-8"))
    args = lately.parse_args([])
    assert lately.detect_lang(args) == "en"


def test_detect_lang_korean_locale(monkeypatch):
    """Korean locale auto-detects ko."""
    monkeypatch.setenv("LANG", "ko_KR.UTF-8")
    args = lately.parse_args([])
    assert lately.detect_lang(args) == "ko"
