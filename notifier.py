#!/usr/bin/env python3
"""
Polls GitHub notifications via `gh api` and shows new ones as desktop
notifications (notify-send). Tracks seen thread IDs in a state file so
each notification only fires once.

Usage:
    python3 notifier.py [--interval 60] [--reason review_requested,comment,mention,...]
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

STATE_FILE = Path.home() / ".cache" / "github-notifier" / "seen.json"

REASON_LABELS = {
    "review_requested": "Review requested",
    "comment": "New comment",
    "mention": "Mentioned you",
    "assign": "Assigned",
    "author": "Activity on your thread",
    "state_change": "State changed",
    "team_mention": "Team mentioned",
    "subscribed": "Subscribed thread activity",
}


def load_seen() -> set:
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()))
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def save_seen(seen: set) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(seen)))


def fetch_notifications():
    result = subprocess.run(
        ["gh", "api", "notifications", "--paginate"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def web_url(subject_api_url: str, html_url_hint: str = "") -> str:
    # gh notifications give an API url, not a browser url; best-effort convert.
    url = subject_api_url.replace("api.github.com/repos", "github.com")
    url = url.replace("/pulls/", "/pull/")
    return url


def notify(title: str, body: str, url: str) -> None:
    subprocess.run(
        ["notify-send", "--app-name=GitHub", title, body],
        check=False,
    )
    if url:
        print(f"{title}: {body} -> {url}")


def run_once(seen: set, reasons: set) -> set:
    notifications = fetch_notifications()
    new_seen = set(seen)
    for n in notifications:
        thread_id = n["id"]
        if thread_id in seen:
            continue
        new_seen.add(thread_id)
        reason = n.get("reason", "")
        if reasons and reason not in reasons:
            continue
        subject = n.get("subject", {})
        repo = n.get("repository", {}).get("full_name", "")
        title = REASON_LABELS.get(reason, reason or "Notification")
        body = f"{repo}: {subject.get('title', '')}"
        url = web_url(subject.get("url", "") or "")
        notify(title, body, url)
    return new_seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=60, help="poll interval in seconds")
    parser.add_argument("--reason", type=str, default="", help="comma-separated reasons to filter (default: all)")
    parser.add_argument("--once", action="store_true", help="run a single check and exit")
    args = parser.parse_args()

    reasons = {r.strip() for r in args.reason.split(",") if r.strip()}
    seen = load_seen()

    try:
        while True:
            seen = run_once(seen, reasons)
            save_seen(seen)
            if args.once:
                break
            time.sleep(args.interval)
    except subprocess.CalledProcessError as e:
        print(f"gh api call failed: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
