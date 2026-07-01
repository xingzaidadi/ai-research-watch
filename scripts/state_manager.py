#!/usr/bin/env python3
"""
AI Research Watch - 状态管理器
处理去重、清理、反馈、权重更新
"""
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

STATE_DIR = Path(__file__).parent.parent / "state"
SEEN_FILE = STATE_DIR / "seen.json"

def load_state():
    if SEEN_FILE.exists():
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {"version": 1, "last_updated": "", "articles": {}, "evergreen_push_counts": {}, "feedback": {"thumbs_up": [], "thumbs_down": []}, "weights": {}}

def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(SEEN_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def is_seen(state, url):
    return url in state.get("articles", {})

def mark_seen(state, url, date=None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    state.setdefault("articles", {})[url] = date

def cleanup_old(state, days=30):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    before = len(state.get("articles", {}))
    state["articles"] = {k: v for k, v in state.get("articles", {}).items() if v >= cutoff}
    after = len(state["articles"])
    return before - after

def title_similarity(t1, t2):
    """Jaccard similarity on word-level tokens"""
    w1 = set(t1.lower().split())
    w2 = set(t2.lower().split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)

def is_title_duplicate(state, title, threshold=0.7):
    # Simple check against recent titles (stored in a separate field)
    recent_titles = state.get("recent_titles", [])
    for t in recent_titles:
        if title_similarity(title, t) > threshold:
            return True
    return False

def add_title(state, title, max_recent=100):
    recent = state.setdefault("recent_titles", [])
    recent.append(title)
    if len(recent) > max_recent:
        state["recent_titles"] = recent[-max_recent:]

def add_feedback(state, url, feedback_type):
    """feedback_type: 'up' or 'down'"""
    key = "thumbs_up" if feedback_type == "up" else "thumbs_down"
    state.setdefault("feedback", {}).setdefault(key, [])
    state["feedback"][key].append({"url": url, "date": datetime.now().strftime("%Y-%m-%d")})

def get_weight_adjustments(state):
    """Calculate topic weight adjustments based on feedback"""
    weights = state.get("weights", {})
    # Count consecutive thumbs_down per topic tag
    down_counts = {}
    for entry in state.get("feedback", {}).get("thumbs_down", []):
        tags = entry.get("tags", [])
        for tag in tags:
            down_counts[tag] = down_counts.get(tag, 0) + 1
    adjustments = {}
    for tag, count in down_counts.items():
        if count >= 3:
            adjustments[tag] = -1
    return adjustments

def get_evergreen_count(state, url):
    return state.get("evergreen_push_counts", {}).get(url, 0)

def increment_evergreen(state, url):
    state.setdefault("evergreen_push_counts", {})[url] = get_evergreen_count(state, url) + 1

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI Research Watch State Manager")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("cleanup", help="Remove entries older than 30 days")
    sub.add_parser("stats", help="Show state statistics")

    check = sub.add_parser("check", help="Check if URL is seen")
    check.add_argument("url")

    mark = sub.add_parser("mark", help="Mark URL as seen")
    mark.add_argument("url")
    mark.add_argument("--date", default=None)

    dup = sub.add_parser("check-title", help="Check title similarity")
    dup.add_argument("title")

    fb = sub.add_parser("feedback", help="Record feedback")
    fb.add_argument("url")
    fb.add_argument("type", choices=["up", "down"])

    args = parser.parse_args()
    state = load_state()

    if args.cmd == "cleanup":
        removed = cleanup_old(state)
        save_state(state)
        print(json.dumps({"removed": removed, "remaining": len(state["articles"])}))

    elif args.cmd == "stats":
        print(json.dumps({
            "total_articles": len(state.get("articles", {})),
            "evergreen_pushes": state.get("evergreen_push_counts", {}),
            "thumbs_up": len(state.get("feedback", {}).get("thumbs_up", [])),
            "thumbs_down": len(state.get("feedback", {}).get("thumbs_down", [])),
            "last_updated": state.get("last_updated", "never")
        }, indent=2))

    elif args.cmd == "check":
        print(json.dumps({"seen": is_seen(state, args.url)}))

    elif args.cmd == "mark":
        mark_seen(state, args.url, args.date)
        save_state(state)
        print(json.dumps({"ok": True}))

    elif args.cmd == "check-title":
        dup = is_title_duplicate(state, args.title)
        print(json.dumps({"duplicate": dup}))

    elif args.cmd == "feedback":
        add_feedback(state, args.url, args.type)
        save_state(state)
        print(json.dumps({"ok": True}))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
