"""
log_entry.py — Append a single log entry to the AGENTS.md-mandated log file.

Usage:
    python code/log_entry.py "Short title" "User prompt (redacted)" "Agent summary" "Actions taken"

Or import and call append_entry() directly from other scripts.

The log lives at: %USERPROFILE%\hackerrank_orchestrate\log.txt  (Windows)
                  $HOME/hackerrank_orchestrate/log.txt          (Unix)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

LOG_DIR = Path.home() / "hackerrank_orchestrate"
LOG_FILE = LOG_DIR / "log.txt"
REPO_ROOT = Path(__file__).parent.parent.resolve()


def _now_iso() -> str:
    # Local time with UTC offset
    local_dt = datetime.now().astimezone()
    return local_dt.isoformat(timespec="seconds")


def append_entry(title: str, user_prompt: str, summary: str, actions: str,
                 branch: str = "main") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = _now_iso()
    entry = (
        f"\n## [{ts}] {title[:80]}\n\n"
        f"User Prompt (verbatim, secrets redacted):\n{user_prompt}\n\n"
        f"Agent Response Summary:\n{summary}\n\n"
        f"Actions:\n{actions}\n\n"
        f"Context:\n"
        f"tool=GitHub Copilot\n"
        f"branch={branch}\n"
        f"repo_root={REPO_ROOT}\n"
        f"worktree=main\n"
        f"parent_agent=none\n"
    )
    with open(LOG_FILE, "a", encoding="utf-8", newline="\n") as f:
        f.write(entry)
    print(f"Appended to {LOG_FILE}")


def append_session_start(branch: str = "main") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = _now_iso()
    # Time remaining until 2026-05-02T11:00:00+05:30
    deadline = datetime(2026, 5, 2, 11, 0, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    now = datetime.now().astimezone()
    remaining = deadline - now
    if remaining.total_seconds() > 0:
        total_mins = int(remaining.total_seconds() // 60)
        days, rem = divmod(total_mins, 1440)
        hours, mins = divmod(rem, 60)
        time_left = f"{days}d {hours}h {mins}m"
    else:
        time_left = "DEADLINE PASSED"

    entry = (
        f"\n## [{ts}] SESSION START\n\n"
        f"Agent: GitHub Copilot\n"
        f"Repo Root: {REPO_ROOT}\n"
        f"Branch: {branch}\n"
        f"Worktree: main\n"
        f"Parent Agent: none\n"
        f"Language: py\n"
        f"Time Remaining: {time_left}\n"
    )
    with open(LOG_FILE, "a", encoding="utf-8", newline="\n") as f:
        f.write(entry)
    print(f"Session start logged. Time remaining: {time_left}")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--session":
        append_session_start()
    elif len(sys.argv) == 5:
        append_entry(
            title=sys.argv[1],
            user_prompt=sys.argv[2],
            summary=sys.argv[3],
            actions=sys.argv[4],
        )
    else:
        print("Usage:")
        print("  python code/log_entry.py --session")
        print('  python code/log_entry.py "Title" "Prompt" "Summary" "Actions"')
