#!/usr/bin/env python3
"""cclanes — per-repo 'what was I working on' CLI tool."""

import argparse
import hashlib
import json
import locale
import os
import subprocess as sp
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME_DIR = Path.home() / "home"
CONFIG_PATH = Path.home() / ".cclanes" / "config.json"
CACHE_PATH = Path.home() / ".cclanes" / "cache.json"
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

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


def detect_lang(args: argparse.Namespace) -> str:
    """Determine UI language from --lang flag or system locale."""
    if args.lang:
        return args.lang
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


def load_config(path: Path = CONFIG_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"exclude": []}


def save_config(cfg: dict, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")


def add_excludes(cfg: dict, repos: list[str]) -> dict:
    current = set(cfg["exclude"])
    current.update(repos)
    cfg["exclude"] = sorted(current)
    return cfg


def remove_excludes(cfg: dict, repos: list[str]) -> dict:
    cfg["exclude"] = [r for r in cfg["exclude"] if r not in repos]
    return cfg


def collect_git_data(repo_path: Path) -> dict | None:
    """Collect git metadata from a repo. Returns None if not a git repo."""
    def git(*args: str) -> str | None:
        try:
            r = sp.run(["git", *args], cwd=repo_path,
                       capture_output=True, text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else None
        except (sp.TimeoutExpired, FileNotFoundError):
            return None

    if git("rev-parse", "--git-dir") is None:
        return None

    branch = git("branch", "--show-current")
    log_date = git("log", "-1", "--format=%cI")
    log_msg = git("log", "-1", "--format=%s")
    porcelain = git("status", "--porcelain")
    remote = git("remote")

    last_commit_date = None
    if log_date:
        try:
            last_commit_date = datetime.fromisoformat(log_date)
        except ValueError:
            pass

    return {
        "branch": branch or None,
        "last_commit_date": last_commit_date,
        "last_commit_msg": log_msg or None,
        "dirty_count": len(porcelain.splitlines()) if porcelain else 0,
        "has_remote": bool(remote),
    }


def find_claude_session(projects_dir: Path, repo_name: str) -> Path | None:
    """Find the most recently modified JSONL file for a repo."""
    for d in projects_dir.iterdir():
        if d.is_dir() and d.name.endswith(f"-{repo_name}"):
            jsonl_files = sorted(d.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
            return jsonl_files[-1] if jsonl_files else None
    return None


def parse_claude_session(jsonl_path: Path) -> dict | None:
    """Parse a Claude Code session JSONL file.

    Returns dict with custom_title, last_user_msg, last_assistant_msg, mtime.
    Returns None if file is empty or unparseable.
    """
    custom_title = None
    last_user_msg = None
    last_assistant_msg = None

    try:
        text = jsonl_path.read_text(encoding="utf-8")
        if not text.strip():
            return None

        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")

            if msg_type == "custom-title":
                custom_title = obj.get("customTitle")

            elif msg_type == "user":
                content = obj.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            text_val = c["text"][:200]
                            if not text_val.startswith("Base directory"):
                                last_user_msg = text_val
                            break

            elif msg_type == "assistant":
                content = obj.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            last_assistant_msg = c["text"][:200]
                            break

    except (OSError, UnicodeDecodeError) as e:
        print(f"⚠ 세션 파일 읽기 실패: {jsonl_path.name} ({e})", file=sys.stderr)
        return None

    if last_user_msg is None and last_assistant_msg is None and custom_title is None:
        return None

    return {
        "custom_title": custom_title,
        "last_user_msg": last_user_msg,
        "last_assistant_msg": last_assistant_msg,
        "mtime": datetime.fromtimestamp(jsonl_path.stat().st_mtime, tz=timezone.utc),
    }


MEMO_VALIDITY_MINUTES = 15


def is_memo_valid(memo_mtime: datetime, last_activity: datetime | None) -> bool:
    """Check if .lately memo is still valid relative to last activity.

    Valid when memo and last activity are within 15 min of each other.
    Always valid when no other activity exists.
    """
    if last_activity is None:
        return True
    gap = abs((memo_mtime - last_activity).total_seconds())
    return gap <= MEMO_VALIDITY_MINUTES * 60


def read_memo(repo_path: Path) -> tuple[str | None, datetime | None]:
    """Read .lately memo file. Returns (content, mtime) or (None, None)."""
    memo_path = repo_path / ".cclanes"
    if not memo_path.exists():
        return None, None
    try:
        content = memo_path.read_text().strip()
        mtime = datetime.fromtimestamp(memo_path.stat().st_mtime, tz=timezone.utc)
        return content if content else None, mtime
    except OSError:
        return None, None


def scan_repos(
    home_dir: Path = HOME_DIR,
    config: dict | None = None,
    claude_projects_dir: Path = CLAUDE_PROJECTS_DIR,
) -> list[dict]:
    """Scan all repos under home_dir and collect data."""
    if config is None:
        config = load_config()
    excluded = set(config.get("exclude", []))

    repos = []
    for entry in sorted(home_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in excluded:
            continue

        git_data = collect_git_data(entry)
        if git_data is None:
            continue

        # Claude session
        session_file = find_claude_session(claude_projects_dir, entry.name)
        claude_data = parse_claude_session(session_file) if session_file else None

        # Memo
        memo_content, memo_mtime = read_memo(entry)

        # Determine last activity time (git + claude only, not memo)
        activity_times = []
        if git_data["last_commit_date"]:
            activity_times.append(git_data["last_commit_date"])
        if claude_data and claude_data["mtime"]:
            activity_times.append(claude_data["mtime"])
        last_activity = max(activity_times) if activity_times else None

        # Check memo validity
        memo_valid = False
        if memo_content and memo_mtime:
            memo_valid = is_memo_valid(memo_mtime, last_activity)

        # Overall last activity (include memo mtime for sorting)
        all_times = list(activity_times)
        if memo_mtime:
            all_times.append(memo_mtime)
        overall_last = max(all_times) if all_times else None

        repos.append({
            "name": entry.name,
            "git": git_data,
            "claude": claude_data,
            "memo": memo_content if memo_valid else None,
            "last_activity": overall_last,
        })

    repos.sort(key=lambda r: r["last_activity"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return repos


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


def compute_cache_key(repo: dict) -> str:
    """Compute a cache key based on git and claude session state."""
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

    raw = "|".join(parts)
    return hashlib.md5(raw.encode()).hexdigest()


def load_cache(path: Path = CACHE_PATH) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache(cache: dict, path: Path = CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n")


def split_cached(repos: list[dict], cache: dict) -> tuple[dict[str, str], list[dict]]:
    """Split repos into cached (hit) and uncached (miss).

    Returns (cached_summaries, uncached_repos).
    """
    cached_summaries = {}
    uncached_repos = []
    for repo in repos:
        if repo["memo"]:
            continue
        key = compute_cache_key(repo)
        entry = cache.get(repo["name"])
        if entry and entry.get("key") == key:
            cached_summaries[repo["name"]] = entry["summary"]
        else:
            uncached_repos.append(repo)
    return cached_summaries, uncached_repos


def build_llm_payload(repos: list[dict]) -> list[dict]:
    """Build payload for LLM summary. Excludes repos with valid memos."""
    payload = []
    for repo in repos:
        if repo["memo"]:
            continue
        entry = {"name": repo["name"]}
        git = repo["git"]
        if git["branch"]:
            entry["branch"] = git["branch"]
        if git["last_commit_msg"]:
            entry["last_commit"] = git["last_commit_msg"]
        if git["dirty_count"]:
            entry["uncommitted_changes"] = git["dirty_count"]

        claude = repo.get("claude")
        if claude:
            if claude.get("custom_title"):
                entry["session_title"] = claude["custom_title"]
            if claude.get("last_user_msg"):
                entry["last_user_msg"] = claude["last_user_msg"][:500]
            if claude.get("last_assistant_msg"):
                entry["last_assistant_msg"] = claude["last_assistant_msg"][:500]

        payload.append(entry)
    return payload


def _call_llm(payload: list[dict]) -> dict[str, str]:
    """Call claude -p --model haiku with a payload. Returns repo→summary dict."""
    if not payload:
        return {}

    prompt = (
        "다음 JSON은 여러 로컬 Git 레포의 최근 활동 데이터입니다.\n"
        "각 레포별로 \"지금 뭘 하고 있었는지\"를 한 줄(30자 이내)로 요약해주세요.\n"
        "커밋 메시지, 세션 타이틀, 마지막 대화 내용을 종합해서 판단하세요.\n\n"
        "출력 형식 (JSON만, 다른 텍스트 없이):\n"
        "{\"repo_name\": \"요약\", ...}\n\n"
        f"데이터:\n{json.dumps(payload, ensure_ascii=False)}"
    )

    try:
        result = sp.run(
            ["claude", "-p", "--model", "haiku"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print("⚠ claude CLI 호출 실패", file=sys.stderr)
            return {}

        response = result.stdout.strip()
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        return {}
    except FileNotFoundError:
        print("⚠ claude CLI를 찾을 수 없습니다. --raw 모드로 전환합니다.", file=sys.stderr)
        return {}
    except sp.TimeoutExpired:
        print("⚠ claude CLI 응답 시간 초과", file=sys.stderr)
        return {}
    except json.JSONDecodeError:
        print("⚠ LLM 응답 파싱 실패", file=sys.stderr)
        return {}


def get_llm_summaries(repos: list[dict]) -> dict[str, str]:
    """Get per-repo summaries with caching. Only calls LLM for changed repos."""
    cache = load_cache()
    cached_summaries, uncached_repos = split_cached(repos, cache)

    # Call LLM only for uncached repos
    new_summaries = {}
    if uncached_repos:
        payload = build_llm_payload(uncached_repos)
        new_summaries = _call_llm(payload)

    # Update cache with new results
    if new_summaries:
        for repo in uncached_repos:
            name = repo["name"]
            if name in new_summaries:
                cache[name] = {
                    "key": compute_cache_key(repo),
                    "summary": new_summaries[name],
                }
        save_cache(cache)

    # Merge cached + new
    all_summaries = {**cached_summaries, **new_summaries}

    if cached_summaries:
        cache_count = len(cached_summaries)
        new_count = len(new_summaries)
        print(f"📋 캐시 {cache_count}개 / 새 분석 {new_count}개", file=sys.stderr)

    return all_summaries


def display_results(repos: list[dict], summaries: dict[str, str], raw: bool = False) -> None:
    """Print the formatted output table."""
    if not repos:
        print("활동이 있는 레포가 없습니다.")
        return

    now = datetime.now(tz=timezone.utc)

    max_name = max(len(r["name"]) for r in repos)
    max_name = max(max_name, 4)

    # Collect session titles for the extra column
    session_titles = {}
    for repo in repos:
        claude = repo.get("claude")
        if claude and claude.get("custom_title"):
            session_titles[repo["name"]] = claude["custom_title"]

    show_session = bool(session_titles)
    max_summary = 40

    if show_session:
        max_session = max(len(t) for t in session_titles.values())
        max_session = max(max_session, 4)
        print(f"{'레포':<{max_name}}  {'마지막 활동':<12}  {'요약':<{max_summary}}  세션")
        print(f"{'─' * max_name}  {'─' * 12}  {'─' * max_summary}  {'─' * max_session}")
    else:
        print(f"{'레포':<{max_name}}  {'마지막 활동':<12}  요약")
        print(f"{'─' * max_name}  {'─' * 12}  {'─' * max_summary}")

    for repo in repos:
        name = repo["name"]
        if repo["last_activity"]:
            time_str = format_relative_time(repo["last_activity"], now)
        else:
            time_str = "-"

        if repo["memo"]:
            summary = f"[memo] {repo['memo']}"
        elif raw:
            summary = build_raw_summary(repo)
        elif name in summaries:
            summary = summaries[name]
        else:
            summary = build_raw_summary(repo)

        if show_session:
            session = session_titles.get(name, "")
            print(f"{name:<{max_name}}  {time_str:<12}  {summary:<{max_summary}}  {session}")
        else:
            print(f"{name:<{max_name}}  {time_str:<12}  {summary}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cclanes",
        description="Per-repo 'what was I working on' summaries.",
    )
    parser.add_argument("--days", type=int, default=None,
                        help="Only show repos with activity in the last N days")
    parser.add_argument("--raw", action="store_true",
                        help="No LLM summary — raw data only (fast/offline)")
    parser.add_argument("--memo", nargs=2, metavar=("REPO", "MESSAGE"),
                        help="Save a manual memo to a repo's .lately file")
    parser.add_argument("--exclude", type=str,
                        help="Permanently exclude repos (comma-separated)")
    parser.add_argument("--include", type=str,
                        help="Remove repos from permanent exclusion (comma-separated)")
    parser.add_argument("--lang", choices=["en", "ko"], default=None,
                        help="Output language (default: auto-detect from locale)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # --exclude: add to config and exit
    if args.exclude:
        repos = [r.strip() for r in args.exclude.split(",")]
        cfg = load_config()
        cfg = add_excludes(cfg, repos)
        save_config(cfg)
        print(f"제외 목록에 추가됨: {', '.join(repos)}")
        return

    # --include: remove from config and exit
    if args.include:
        repos = [r.strip() for r in args.include.split(",")]
        cfg = load_config()
        cfg = remove_excludes(cfg, repos)
        save_config(cfg)
        print(f"제외 목록에서 제거됨: {', '.join(repos)}")
        return

    # --memo: write memo file and exit
    if args.memo:
        repo_name, message = args.memo
        memo_path = HOME_DIR / repo_name / ".cclanes"
        if not (HOME_DIR / repo_name).is_dir():
            print(f"오류: ~/home/{repo_name} 디렉토리가 없습니다.", file=sys.stderr)
            sys.exit(1)
        memo_path.write_text(message + "\n")
        print(f"메모 저장됨: ~/home/{repo_name}/.lately")
        return

    # Scan repos
    repos = scan_repos()

    # Filter by --days
    if args.days is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=args.days)
        repos = [r for r in repos if r["last_activity"] and r["last_activity"] >= cutoff]

    # Get LLM summaries (unless --raw)
    summaries = {}
    if not args.raw:
        summaries = get_llm_summaries(repos)
        if not summaries and any(r["memo"] is None for r in repos):
            print("⚠ LLM 요약 실패, raw 모드로 표시합니다.\n", file=sys.stderr)

    display_results(repos, summaries, raw=args.raw)


if __name__ == "__main__":
    main()
