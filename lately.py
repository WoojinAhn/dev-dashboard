#!/usr/bin/env python3
"""lately — per-repo 'what was I working on' CLI tool."""

import argparse
import json
import sys
from datetime import datetime, timezone
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
                            # Skip system/skill messages
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
