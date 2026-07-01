#!/usr/bin/env python3
"""
AI Research Watch - 用户行为追踪
自动记录推送后的用户反馈
"""
import json
import sys
from datetime import datetime
from pathlib import Path

TRACK_FILE = Path(__file__).parent.parent / "state" / "tracking.json"

def load():
    if TRACK_FILE.exists():
        return json.load(open(TRACK_FILE))
    return {"daily_records": [], "weekly_summary": {}}

def save(data):
    TRACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACK_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def record_push(date, articles_count, article_urls):
    """记录一次推送"""
    data = load()
    data["daily_records"].append({
        "date": date,
        "articles_pushed": articles_count,
        "article_urls": article_urls,
        "feedback": None,  # 待用户反馈
        "articles_read": 0,
        "articles_detailed": 0
    })
    save(data)

def record_feedback(date, feedback):
    """记录用户反馈: "read" / "skip" / "like" / "dislike" """
    data = load()
    for rec in data["daily_records"]:
        if rec["date"] == date:
            rec["feedback"] = feedback
            if feedback in ("read", "like"):
                rec["articles_read"] = rec["articles_pushed"]
            break
    save(data)

def record_article_detail(date, count):
    """记录精读数量"""
    data = load()
    for rec in data["daily_records"]:
        if rec["date"] == date:
            rec["articles_detailed"] = count
            break
    save(data)

def get_stats():
    """获取统计数据"""
    data = load()
    records = data["daily_records"]
    if not records:
        return {"status": "no_data"}

    total_pushed = sum(r["articles_pushed"] for r in records)
    total_read = sum(r["articles_read"] for r in records)
    total_detailed = sum(r["articles_detailed"] for r in records)
    feedback_counts = {}
    for r in records:
        fb = r.get("feedback") or "no_response"
        feedback_counts[fb] = feedback_counts.get(fb, 0) + 1

    return {
        "days": len(records),
        "total_pushed": total_pushed,
        "total_read": total_read,
        "total_detailed": total_detailed,
        "read_rate": f"{total_read/total_pushed*100:.0f}%" if total_pushed else "0%",
        "feedback_distribution": feedback_counts,
        "date_range": f"{records[0]['date']} ~ {records[-1]['date']}"
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p_push = sub.add_parser("push")
    p_push.add_argument("--date", required=True)
    p_push.add_argument("--count", type=int, required=True)
    p_push.add_argument("--urls", nargs="*", default=[])

    p_fb = sub.add_parser("feedback")
    p_fb.add_argument("--date", required=True)
    p_fb.add_argument("--type", required=True, choices=["read", "skip", "like", "dislike"])

    p_detail = sub.add_parser("detail")
    p_detail.add_argument("--date", required=True)
    p_detail.add_argument("--count", type=int, required=True)

    sub.add_parser("stats")

    args = parser.parse_args()
    if args.cmd == "push":
        record_push(args.date, args.count, args.urls)
        print(json.dumps({"ok": True}))
    elif args.cmd == "feedback":
        record_feedback(args.date, args.type)
        print(json.dumps({"ok": True}))
    elif args.cmd == "detail":
        record_article_detail(args.date, args.count)
        print(json.dumps({"ok": True}))
    elif args.cmd == "stats":
        print(json.dumps(get_stats(), indent=2, ensure_ascii=False))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
