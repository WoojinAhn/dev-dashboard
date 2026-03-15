#!/usr/bin/env python3
"""lately — per-repo 'what was I working on' CLI tool."""

import argparse
import json
import subprocess as sp
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME_DIR = Path.home() / "home"
CONFIG_PATH = Path.home() / ".lately" / "config.json"
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


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
    memo_path = repo_path / ".lately"
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


def format_relative_time(dt: datetime, now: datetime | None = None) -> str:
    """Format datetime as Korean relative time string."""
    if now is None:
        now = datetime.now(tz=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "방금"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}분 전"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}시간 전"
    days = hours // 24
    if days < 14:
        return f"{days}일 전"
    weeks = days // 7
    if weeks < 8:
        return f"{weeks}주 전"
    months = days // 30
    return f"{months}개월 전"


def build_raw_summary(repo: dict) -> str:
    """Build a raw (no-LLM) summary string for a repo."""
    if repo["memo"]:
        return f"[memo] {repo['memo']}"

    parts = []
    git = repo["git"]
    claude = repo.get("claude")

    if claude and claude.get("custom_title"):
        parts.append(f"세션: {claude['custom_title']}")

    if git["last_commit_msg"]:
        parts.append(f"커밋: {git['last_commit_msg']}")

    if git["dirty_count"] > 0:
        parts.append(f"미커밋 {git['dirty_count']}개")

    return ", ".join(parts) if parts else "(활동 없음)"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lately",
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
        memo_path = HOME_DIR / repo_name / ".lately"
        if not (HOME_DIR / repo_name).is_dir():
            print(f"오류: ~/home/{repo_name} 디렉토리가 없습니다.", file=sys.stderr)
            sys.exit(1)
        memo_path.write_text(message + "\n")
        print(f"메모 저장됨: ~/home/{repo_name}/.lately")
        return

    # Default: scan and display (placeholder)
    print("(scan not implemented yet)")


if __name__ == "__main__":
    main()
