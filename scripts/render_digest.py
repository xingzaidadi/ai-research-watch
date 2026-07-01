#!/usr/bin/env python3
"""
AI Research Watch - 摘要渲染器
输入：评分后的文章 JSON 列表
输出：格式化的中文推送文本
"""
import json
import sys
from datetime import datetime

def render_stars(score):
    """分数转星级（1-5）"""
    if score >= 8: return "★★★★★"
    if score >= 6: return "★★★★☆"
    if score >= 4: return "★★★☆☆"
    if score >= 2: return "★★☆☆☆"
    return "★☆☆☆☆"

def render_digest(articles, max_new=3, max_evergreen=1):
    """
    生成推送文本
    articles: 已按 score 降序排列的列表
    """
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"📡 今日 AI 研究雷达 | {today}", "", "━━━━━━━━━━━━━━━━━━", ""]

    # 新文章
    new_articles = [a for a in articles if a.get("score", 0) > 0][:max_new]
    evergreen = [a for a in articles if a.get("is_evergreen", False)][:max_evergreen]

    if new_articles:
        for i, art in enumerate(new_articles, 1):
            stars = render_stars(art.get("score", 0))
            lines.append(f"{i}. {art['title']}")
            lines.append(f"📎 来源：{art.get('source', 'Unknown')}")
            lines.append(f"📂 类型：{art.get('type', 'Other')}")
            lines.append(f"⭐ 重要程度：{stars}")
            lines.append(f"🔗 链接：{art['url']}")
            lines.append("")
            lines.append("💡 三句话总结：")

            # 使用已生成的摘要或生成占位
            summary = art.get("summary", "")
            if summary:
                for line in summary.split("\n"):
                    lines.append(f"• {line.strip()}")
            else:
                lines.append(f"• {art.get('description', '暂无摘要')[:100]}")

            lines.append("")
            tags = art.get("tags", [])
            if tags:
                lines.append(f"🎯 你需要关注：{'、'.join(tags)}")
            lines.append("")
            lines.append("━━━━━━━━━━━━━━━━━━")
            lines.append("")

    # 补课文章
    if evergreen:
        lines.append("📚 今日补课：")
        for art in evergreen:
            lines.append(f"• {art['title']}（{art.get('source', '')}）")
            lines.append(f"  🔗 {art['url']}")
            summary = art.get("summary", "")
            if summary:
                lines.append(f"  💡 {summary[:150]}")
        lines.append("")

    if not new_articles and not evergreen:
        lines.append("今日无新内容，明天见 👋")

    return "\n".join(lines)

def main():
    """命令行入口"""
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    articles = data if isinstance(data, list) else data.get("articles", [])
    max_new = data.get("max_new", 3) if isinstance(data, dict) else 3

    output = render_digest(articles, max_new=max_new)
    print(output)

if __name__ == "__main__":
    main()
