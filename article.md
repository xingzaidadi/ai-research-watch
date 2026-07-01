# 我用 OpenClaw 做了一个 AI 研究每日雷达，每天 9 点自动推送到飞书

> 每天早上 9 点，我的飞书会收到 3 篇 OpenAI/Anthropic 最新研究的中文摘要。没有新文章时，还会推送一篇经典论文补课。这一切由一个 Skill + Cron 自动完成。

## 为什么要做这个

作为一个关注 AI Agent 方向的开发者，我每天都要刷 OpenAI Blog、Anthropic Research、arXiv，时间成本很高。而且经常出现两种情况：

1. **漏看重要文章**：OpenAI 发了新的 benchmark 但我不知道
2. **看到二手信息**：技术群里转发的文章，标题夸张但内容空洞

我想做一个**只看官方源头、自动筛选、推送中文摘要**的工具。

## 技术选型：为什么是 Skill + Cron

一开始我想写一个 Python 爬虫 + 定时任务，但很快发现两个问题：

1. **RSS 解析后的文章需要语义理解**：怎么判断一篇文章是"研究论文"还是"营销新闻"？纯规则很难
2. **中文摘要需要 LLM**：用 GPT 翻译+总结，比自己写好 10 倍

OpenClaw 的 Skill 体系天然适合这种场景：

- **Skill** = 定义"怎么做"（抓取、评分、渲染的规则和流程）
- **Cron** = 定义"什么时候做"（每天 09:00）
- **LLM** = 负责"理解"（判断文章类型、生成中文摘要）
- **Python 脚本** = 负责"确定性执行"（评分规则、去重、渲染模板）

最终架构：

```
用户说"查最新" ──→ Skill 触发 ──→ 抓取 RSS/网页
                                      │
                                      ▼
                              Python 评分器（确定性）
                                      │
                                      ▼
                              去重（seen.json）
                                      │
                                      ▼
                              LLM 生成三句话摘要
                                      │
                                      ▼
                              Python 渲染器（固定模板）
                                      │
                                      ▼
                              飞书私聊推送
```

## 核心设计：LLM 和 Python 的分工

这是我在这个项目中最重要的设计决策：**LLM 只做它擅长的事，其他全交给代码**。

| 环节 | 负责方 | 原因 |
|------|--------|------|
| RSS 抓取 | Python（fetch_rss.py） | 确定性解析，不需要 LLM |
| 文章评分 | Python（score_articles.py） | 基于规则，不能漂移 |
| 去重 | Python（state_manager.py） | URL 比对，纯逻辑 |
| 渲染模板 | Python（render_digest.py） | 固定格式，不需要创造 |
| 判断文章类型 | LLM | 需要语义理解 |
| 生成三句话摘要 | LLM | 需要自然语言生成 |

**为什么不全交给 LLM？**

因为 LLM 的输出是非确定性的。同一个 prompt 跑两次，评分可能一个 +5 一个 +3。评分标准一旦漂移，推荐质量就不稳定。而 Python 代码跑 1000 次结果都一样。

**为什么不全交给 Python？**

因为"这篇文章讲了什么""三句话怎么总结"这种事，写规则比写 LLM prompt 难 10 倍，而且效果差很多。

## 评分器设计

评分器是最核心的模块，规则如下：

```python
# 正分
+5  官方 Research / Publication
+4  Benchmark / System Card / Eval
+3  Agent / Reasoning / Alignment / Safety
+2  模型发布 / 技术说明
+1~3  关键词匹配（eval_keywords.yml 三级权重）

# 负分
-3  纯营销 / 招聘 / 合作新闻稿
-5  非官方二手转述
-2  非技术内容（office/funding）
```

实际效果测试：

```json
// Measuring AI agent autonomy（Anthropic 官方研究）
{"score": 10, "reasons": ["官方Research/论文 (+5)", "Agent/Reasoning/Safety (+3)", "关键词匹配 [agent] (+2)"]}

// Introducing GeneBench-Pro（OpenAI 新 benchmark）
{"score": 9, "reasons": ["Benchmark/Eval/System Card (+4)", "模型发布/技术说明 (+2)", "关键词匹配 [benchmark] (+3)"]}

// HP Inc launches partnership（合作新闻稿）
{"score": 2, "reasons": ["模型发布/技术说明 (+2)"]}
```

可以看到，合作新闻稿虽然也有 +2，但相比研究论文的 +10 差距明显，不会被推到前面。

## 状态管理：seen.json

去重的核心是一个 JSON 文件：

```json
{
  "articles": {
    "https://openai.com/index/introducing-genebench-pro": "2026-07-01"
  },
  "evergreen_push_counts": {
    "https://anthropic.com/engineering/demystifying-evals": 1
  },
  "feedback": {
    "thumbs_up": [],
    "thumbs_down": []
  }
}
```

| 字段 | 作用 |
|------|------|
| articles | 已推送文章 URL → 日期，防止重复推送 |
| evergreen_push_counts | 补课文章推送次数，超过 2 次自动轮换 |
| feedback | 用户反馈，后续可做主题降权 |

另外还有标题相似度去重（Jaccard > 0.7 视为重复），防止同一篇文章换标题重发。

## Cron 配置

OpenClaw 的 Cron 支持 `agentTurn` 类型，会启动一个 isolated session 执行任务：

```json
{
  "name": "ai-research-watch-daily",
  "schedule": {
    "kind": "cron",
    "expr": "0 9 * * *",
    "tz": "Asia/Shanghai"
  },
  "payload": {
    "kind": "agentTurn",
    "message": "执行 AI Research Watch 每日推送...\n\n步骤 1：清理旧状态\n步骤 2：抓取 RSS\n...",
    "timeoutSeconds": 600
  }
}
```

关键是 prompt 里写清楚了 10 个步骤，每步都指定了具体的脚本和命令，LLM 只需要按步骤执行，不需要自己判断"该怎么做"。

## 文件结构

```
ai-research-watch/
├── SKILL.md                           # Skill 定义（流程、规则、格式）
├── scripts/
│   ├── fetch_rss.py                   # RSS 抓取器（71行）
│   ├── score_articles.py              # 确定性评分器（161行）
│   ├── render_digest.py               # 推送渲染器（89行）
│   └── state_manager.py              # 状态管理器（151行）
├── references/
│   ├── sources.yml                    # 9个信息源配置
│   ├── eval_keywords.yml              # 三级权重关键词
│   └── evergreen_articles.yml         # 10篇补课文章池
└── state/
    └── seen.json                      # 运行状态
```

总共 472 行 Python + 配置文件，很轻量。

## 踩过的坑

### 1. RSS 不是万能的

OpenAI 有 RSS，Anthropic 没有。最终方案：
- OpenAI：RSS 优先（确定性解析）
- Anthropic：web_access_tool 抓取页面 + LLM 提取文章列表

### 2. LLM 评分会漂移

一开始我用 LLM 直接评分，结果同一个文章今天 +5 明天 +3。改成 Python 规则评分后彻底解决。

### 3. Cron 执行质量不可控

如果 Cron 的 prompt 只说"去抓最新文章"，每次执行结果都不一样。最终方案是在 prompt 里写死 10 个步骤 + 具体脚本命令，LLM 只是"按步骤执行"。

### 4. 补课文章会反复推

evergreen 池只有 10 篇文章，不控制的话每天都推同一篇。加了 push_count 计数，超过 2 次自动轮换。

## 最终效果

每天早上 9 点，飞书私聊会收到：

```
📡 今日 AI 研究雷达 | 2026-07-01

━━━━━━━━━━━━━━━━━━

1. Measuring AI agent autonomy in practice
📎 来源：Anthropic
📂 类型：Research / Agent Evaluation
⭐ 重要程度：★★★★★

💡 三句话总结：
• Anthropic 提出了一套度量 AI Agent 自主性的实践方法论
• 涉及 Agent 决策链路分析、自主程度分级、风险评估框架
• 做 Agent 评估不能只看完成率，自主性度量是下一个关键维度

🎯 你需要关注：agent autonomy、自主性度量

━━━━━━━━━━━━━━━━━━
（共 3 篇新文章 + 1 篇补课）
```

## 开源

项目已开源：https://github.com/xingzaidadi/ai-research-watch

欢迎 star、issue、PR。如果你也想做一个类似的信息雷达，fork 后改 `sources.yml` 和 `eval_keywords.yml` 就能用。

## 写在最后

这个项目的核心思路就一句话：**LLM 做理解，代码做执行，配置做扩展**。

不要什么都丢给 LLM，也不要把什么都要写成规则。找到那个边界，才是好架构。

---

*如果觉得有用，点个赞 👍 你的赞是我更新的动力。*
