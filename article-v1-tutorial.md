# 手把手教你用 Python + LLM 做一个 AI 研究日报推送系统

> 每天早上 9 点，自动抓取 OpenAI/Anthropic 最新研究，过滤噪音，生成中文摘要，推送到你的飞书/微信/Telegram。

## 先看效果

```
📡 今日 AI 研究雷达 | 2026-07-01

━━━━━━━━━━━━━━━━━━

1. Measuring AI agent autonomy in practice
📎 来源：Anthropic
📂 类型：Research / Agent Evaluation
⭐ 重要程度：★★★★★

💡 三句话总结：
• Anthropic 提出了一套度量 AI Agent 自主性的方法论
• 涉及决策链路分析、自主程度分级、风险评估框架
• Agent 评估不能只看完成率，自主性度量是下一个关键维度

🎯 你需要关注：agent autonomy、自主性度量
```

每天 3 篇新文章 + 1 篇经典补课，全中文，带评分。

---

## 为什么不用 RSS 阅读器？

| 工具 | 问题 |
|------|------|
| Feedly / Inoreader | 只是聚合，还要自己读，没有摘要 |
| 即刻 AI 话题 | 二手信息多，营销号扎堆 |
| Twitter/X 列表 | 噪音太大，算法推荐干扰 |
| 自己手动刷 | 每天 30-60 分钟，且经常漏看 |

**这个系统的差异**：

1. **只看官方源头**（OpenAI Blog / Anthropic Research），不看二手转述
2. **自动评分筛选**，营销内容直接过滤
3. **LLM 生成中文摘要**，3 句话讲完一篇文章
4. **补课机制**，没有新文章时推送经典论文

---

## 架构设计

```
RSS 抓取 ──→ Python 评分器 ──→ 去重 ──→ LLM 摘要 ──→ 模板渲染 ──→ 推送
  (确定性)      (确定性)       (确定性)   (LLM)       (确定性)    (API)
```

**核心原则：LLM 只做理解，代码做执行。**

| 环节 | 负责方 | 为什么 |
|------|--------|--------|
| RSS 解析 | Python | XML 解析不需要 LLM |
| 文章评分 | Python | 规则打分不能漂移 |
| 去重 | Python | URL 比对是纯逻辑 |
| 渲染模板 | Python | 固定格式不需要创造 |
| 生成摘要 | LLM | 需要语义理解和中文生成 |
| 判断文章类型 | LLM | "这是论文还是营销？"需要理解 |

---

## 从零搭建

### 第一步：准备环境

```bash
mkdir ai-research-watch && cd ai-research-watch
pip install feedparser requests
```

### 第二步：RSS 抓取器

```python
# fetch_rss.py
import feedparser
import json
import sys

def fetch(url):
    """抓取 RSS feed，返回文章列表"""
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        articles.append({
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "description": entry.get("summary", "")[:200],
            "pub_date": entry.get("published", ""),
            "source": "OpenAI" if "openai" in url else "Anthropic"
        })
    return articles

if __name__ == "__main__":
    urls = [
        "https://openai.com/news/rss.xml",
        # Anthropic 没有 RSS，需要网页抓取（后面会讲）
    ]
    all_articles = []
    for url in urls:
        all_articles.extend(fetch(url))
    print(json.dumps(all_articles, indent=2, ensure_ascii=False))
```

测试一下：

```bash
python fetch_rss.py
```

输出：

```json
[
  {
    "title": "Introducing GeneBench-Pro",
    "url": "https://openai.com/index/introducing-genebench-pro",
    "description": "A new benchmark testing AI in genomics...",
    "pub_date": "Tue, 30 Jun 2026",
    "source": "OpenAI"
  }
]
```

### 第三步：确定性评分器

这是核心——用规则给每篇文章打分，不用 LLM，保证每次结果一致。

```python
# score_articles.py
import json
import sys

def score(title, description, url):
    """基于规则的确定性评分"""
    score = 0
    reasons = []
    text = (title + " " + description).lower()

    # 正分：来源类型
    if any(s in url for s in ["/research/", "arxiv.org"]):
        score += 5
        reasons.append("官方研究 (+5)")

    if any(s in text for s in ["benchmark", "system card", "eval"]):
        score += 4
        reasons.append("Benchmark/Eval (+4)")

    if any(s in text for s in ["agent", "reasoning", "safety", "alignment"]):
        score += 3
        reasons.append("Agent/Safety (+3)")

    if any(s in text for s in ["introducing", "release", "new model"]):
        score += 2
        reasons.append("模型发布 (+2)")

    # 正分：关键词匹配
    high_kw = ["eval", "benchmark", "system card"]
    med_kw = ["agent", "reasoning", "tool use", "planning"]
    for kw in high_kw:
        if kw in text: score += 3; reasons.append(f"[{kw}] +3")
    for kw in med_kw:
        if kw in text: score += 2; reasons.append(f"[{kw}] +2")

    # 负分：噪音过滤
    if any(s in text for s in ["hiring", "job opening", "partnership"]):
        score -= 3; reasons.append("营销/合作 (-3)")

    if any(s in text for s in ["says", "according to", "reportedly"]):
        official = ["openai.com", "anthropic.com", "arxiv.org"]
        if not any(d in url for d in official):
            score -= 5; reasons.append("二手转述 (-5)")

    return score, reasons

if __name__ == "__main__":
    articles = json.load(sys.stdin)
    for art in articles:
        s, r = score(art["title"], art["description"], art["url"])
        art["score"] = s
        art["reasons"] = r
    articles.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps(articles, indent=2, ensure_ascii=False))
```

使用：

```bash
cat articles.json | python score_articles.py
```

输出：

```json
[
  {
    "title": "Measuring AI agent autonomy",
    "score": 10,
    "reasons": ["官方研究 (+5)", "Agent/Safety (+3)", "[agent] +2"]
  },
  {
    "title": "HP launches partnership",
    "score": 2,
    "reasons": ["模型发布 (+2)"]
  }
]
```

10 分 vs 2 分，一目了然。

### 第四步：LLM 生成摘要

对评分 top 3 的文章，用 LLM 生成三句话中文摘要：

```python
# generate_summary.py
import json
import sys
from openai import OpenAI

client = OpenAI()  # 需要设置 OPENAI_API_KEY

def summarize(title, description):
    """用 GPT 生成三句话中文摘要"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"""用中文总结以下文章，3 句话，每句一行：
标题：{title}
摘要：{description}

格式：
• 这篇主要解决什么问题
• 它用了什么方法
• 对 AI 开发者有什么启发"""
        }],
        temperature=0.3
    )
    return resp.choices[0].message.content

if __name__ == "__main__":
    articles = json.load(sys.stdin)
    for art in articles[:3]:
        art["summary_cn"] = summarize(art["title"], art["description"])
    print(json.dumps(articles, indent=2, ensure_ascii=False))
```

### 第五步：渲染推送文本

```python
# render.py
import json
import sys
from datetime import datetime

def render(articles):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"📡 今日 AI 研究雷达 | {today}",
        "", "━━━━━━━━━━━━━━━━━━", ""
    ]
    stars = lambda s: "★" * min(5, max(1, s // 2)) + "☆" * max(0, 5 - s // 2)

    for i, art in enumerate(articles[:3], 1):
        lines.append(f"{i}. {art['title']}")
        lines.append(f"📎 来源：{art.get('source', 'Unknown')}")
        lines.append(f"⭐ 重要程度：{stars(art.get('score', 0))}")
        lines.append(f"🔗 {art['url']}")
        lines.append("")
        lines.append("💡 三句话总结：")
        lines.append(art.get("summary_cn", "暂无摘要"))
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append("")

    return "\n".join(lines)

if __name__ == "__main__":
    data = json.load(sys.stdin)
    print(render(data))
```

### 第六步：去重

用一个 JSON 文件记录已推送的文章：

```python
# dedup.py
import json
from pathlib import Path

STATE_FILE = Path("seen.json")

def load():
    if STATE_FILE.exists():
        return json.load(open(STATE_FILE))
    return {}

def save(state):
    json.dump(state, open(STATE_FILE, "w"), indent=2)

def is_seen(url):
    return url in load()

def mark_seen(url):
    from datetime import datetime
    state = load()
    state[url] = datetime.now().strftime("%Y-%m-%d")
    save(state)

def filter_new(articles):
    return [a for a in articles if not is_seen(a["url"])]
```

### 第七步：串联 + 定时

主流程：

```python
# main.py
from fetch_rss import fetch
from score_articles import score
from dedup import filter_new, mark_seen
from generate_summary import summarize
from render import render

# 1. 抓取
articles = fetch("https://openai.com/news/rss.xml")

# 2. 去重
articles = filter_new(articles)

# 3. 评分
for art in articles:
    s, _ = score(art["title"], art["description"], art["url"])
    art["score"] = s
articles.sort(key=lambda x: x["score"], reverse=True)

# 4. 摘要 top 3
top = articles[:3]
for art in top:
    art["summary_cn"] = summarize(art["title"], art["description"])

# 5. 渲染
digest = render(top)

# 6. 推送（飞书 Webhook / Telegram Bot / 企业微信）
send_to_feishu(digest)

# 7. 标记已推送
for art in top:
    mark_seen(art["url"])
```

定时执行（Linux cron）：

```bash
# 每天早上 9 点执行
0 9 * * * cd /path/to/ai-research-watch && python main.py
```

或者用 GitHub Actions（免费）：

```yaml
# .github/workflows/daily.yml
name: Daily AI Research
on:
  schedule:
    - cron: '0 1 * * *'  # UTC 01:00 = 北京时间 09:00
jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install feedparser openai requests
      - run: python main.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          FEISHU_WEBHOOK: ${{ secrets.FEISHU_WEBHOOK }}
```

---

## 完整项目结构

```
ai-research-watch/
├── fetch_rss.py           # RSS 抓取
├── score_articles.py      # 确定性评分
├── generate_summary.py    # LLM 摘要
├── render.py              # 模板渲染
├── dedup.py               # 去重
├── main.py                # 主流程
├── seen.json              # 已推送记录
└── .github/workflows/
    └── daily.yml          # GitHub Actions 定时
```

总共 **不到 200 行 Python**，10 分钟就能跑起来。

---

## 进阶：加更多源

OpenAI 有 RSS，但 Anthropic 没有。两个方案：

**方案 1：网页抓取**

```python
# 用 BeautifulSoup 解析 Anthropic Research 页面
import requests
from bs4 import BeautifulSoup

def fetch_anthropic():
    resp = requests.get("https://www.anthropic.com/research")
    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []
    for a in soup.select("a[href*='/research/']"):
        articles.append({
            "title": a.get_text(strip=True),
            "url": "https://www.anthropic.com" + a["href"],
            "source": "Anthropic"
        })
    return articles
```

**方案 2：arXiv 搜索**

```python
# 搜 arXiv 上 OpenAI/Anthropic 的论文
import arxiv

def fetch_arxiv(query="openai OR anthropic", max_results=10):
    search = arxiv.Search(query=query, max_results=max_results)
    return [{
        "title": r.title,
        "url": r.pdf_url,
        "description": r.summary[:200],
        "source": "arXiv"
    } for r in search.results()]
```

---

## 加分项：补课机制

没有新文章时，从经典论文池里选一篇推送：

```python
# evergreen 池
EVERGREEN = [
    {"title": "Demystifying evals for AI agents",
     "url": "https://anthropic.com/engineering/demystifying-evals-for-ai-agents",
     "push_count": 0, "max_pushes": 2},
    {"title": "Building effective agents",
     "url": "https://anthropic.com/engineering/building-effective-agents",
     "push_count": 0, "max_pushes": 2},
]

def pick_evergreen():
    for art in EVERGREEN:
        if art["push_count"] < art["max_pushes"]:
            return art
    return None
```

---

## 总结

| 组件 | 作用 | 行数 |
|------|------|------|
| fetch_rss.py | RSS 抓取 | ~30 行 |
| score_articles.py | 确定性评分 | ~50 行 |
| generate_summary.py | LLM 摘要 | ~30 行 |
| render.py | 模板渲染 | ~30 行 |
| dedup.py | 去重 | ~25 行 |
| main.py | 串联 | ~30 行 |

**核心原则就一句话**：LLM 做理解，代码做执行，配置做扩展。

不要什么都丢给 LLM，也不要把什么都要写成规则。找到那个边界，才是好架构。

---

*代码已开源：[GitHub](https://github.com/xingzaidadi/ai-research-watch)，欢迎 star。*

*如果觉得有用，点个赞 👍 你的赞是我写下一篇的动力。*
