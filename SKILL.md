---
name: ai-research-watch
name_zh: "AI 前沿研究每日雷达"
version: "1.0.0"
description: |
  每日自动抓取 OpenAI/Anthropic/arXiv 等 AI 前沿研究，经确定性评分和去重后，
  生成中文三句话摘要推送到飞书；支持按需下载论文全文并生成飞书文档+PDF+Markdown 压缩包。
  触发词：查最新研究、AI 雷达、research watch、今日 AI 资讯、下载论文全文、获取论文原文、全部下载、下载第X篇。
  输出：飞书消息推送（含标题/来源/星级/摘要）+ 可选的飞书文档+PDF+Markdown 压缩包。
examples:
  - "查最新研究"
  - "今日 AI 资讯有哪些"
  - "下载这篇论文 https://arxiv.org/abs/2507.xxxxx"
  - "有没有突发文章"
not_for:
  - "非 AI 领域的研究论文追踪"
  - "论文深度解读/学术评审（本 skill 只做摘要+归档）"
  - "批量论文翻译（单篇标题翻译支持，全文翻译不支持）"
metadata:
  author: 刘四星
  domain: office
---

## 触发条件

当用户说以下任意内容时激活本 skill：
- 「查最新研究」「AI 雷达」「research watch」「今日 AI 资讯」
- 「有没有突发文章」（实时模式）
- 「下载论文全文」「获取论文原文」「download paper」「把这篇搞下来」
- 用户给出 arXiv 链接/ID 要求获取内容
- Cron 定时任务触发（每日 09:00 Asia/Shanghai）

---

## 前置条件

- Python 3 环境 + `pip install requests feedparser`（RSS 抓取）
- 飞书 lark-cli 可用（文档创建/权限/消息推送）
- 脚本目录：`skills/ai-research-watch/scripts/`
- 状态目录：`skills/ai-research-watch/state/seen.json`

---

## 操作说明

### 模式判断

本 skill 有三种运行模式：

| 模式 | 触发方式 | 核心流程 |
|------|---------|---------|
| 每日定时推送 | Cron 09:00 | RSS→评分→去重→渲染→推送 |
| 实时按需 | 用户说"查最新研究" | 同上，但立即执行 |
| 论文下载 | 用户给链接/说"下载" | fetch→元数据→飞书文档→PDF→压缩包 |

### Phase 1：RSS 抓取

```bash
cd /root/.openclaw/workspace/skills/ai-research-watch
python3 scripts/fetch_rss.py https://openai.com/news/rss.xml > /tmp/rss_articles.json
```

**三层降级**：RSS 优先 → HTML 解析(web_access_tool) → 搜索兜底(web_access_tool search)

### Phase 2：评分

```bash
python3 scripts/score_articles.py /tmp/rss_articles.json > /tmp/scored.json
```

评分规则（确定性，由脚本执行）：

| 条件 | 分数 |
|------|------|
| 官方 Research / Publication | +5 |
| System Card / Eval / Benchmark | +4 |
| Agent / Reasoning / Alignment / Safety | +3 |
| 模型发布 / 技术说明 | +2 |
| 含 eval_keywords.yml 关键词 | +1~3 |
| 纯营销 / 招聘 / 合作新闻稿 | -3 |
| 非技术内容 | -2 |
| 非官方二手转述 | -5 |

### Phase 3：去重

```bash
python3 scripts/state_manager.py check <每篇文章URL>
```

- URL 精确去重（seen.json）
- 标题 Jaccard 相似度 > 0.7 视为重复
- 保留 30 天，超过自动清理

### Phase 4：生成中文摘要（⚠️ 强制中文）

为每篇正分文章生成三句话摘要（what/why/value）+ 中文标题。

> ⛔ **语言铁律**：摘要和标题**必须用中文**撰写。即使原文是英文，三句话总结也必须是中文。标题需翻译为中文（保留 CoRe、DPO 等专有名词）。

写入文章 JSON 的 `summary` 字段。

### Phase 5：渲染推送

```bash
python3 scripts/render_digest.py /tmp/scored.json > /tmp/digest.txt
```

⛔ 禁止自己拼 interactive card！必须用 render_digest.py 输出。

### Phase 6：推送飞书

用 message tool 发送 `/tmp/digest.txt` 内容（target: `user:ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef`）

### Phase 7：记录

```bash
python3 scripts/track_user.py push --date $(date +%Y-%m-%d) --count {文章数} --urls {URL列表}
```

### Phase 8：下载提示

发送：「📥 感兴趣的论文可以一键获取全文：回复"下载第X篇"或"全部下载"」

### 无新内容处理

评分后无正分文章 → 从 evergreen 池选补课文章 → 同样用 render_digest.py 渲染。

---

## 论文下载流程（深度阅读模式）

### 触发条件
- 用户给 arXiv 链接/ID
- 用户给博客链接（openai.com、anthropic.com 等）
- 用户说"下载论文""获取原文""把这篇搞下来""全部下载""下载第X篇"

### 抓取策略（三路 fallback）

| 优先级 | 策略 | 优点 | 缺点 |
|--------|------|------|------|
| 1️⃣ | arXiv HTML | 速度快、可读文本 | 非所有论文都有 |
| 2️⃣ | arXiv LaTeX 源码 | 含公式/代码/完整内容 | 需解压解析 |
| 3️⃣ | arXiv PDF | 总是可用 | 文本提取困难 |

### 执行步骤

> ⚠️ **第 0 步（强制）**：收到下载请求后，必须先 `ls scripts/` 确认可用脚本，再按步骤操作。禁止凭记忆手动 curl/python 提取。

0. **检查工具链**：`ls scripts/` → 确认 `fetch_paper.py`、`render_paper_doc.py`、`html2pdf.py`、`convert_xml_to_md.py` 存在
1. **下载论文**：`python3 scripts/fetch_paper.py <ID> -o /tmp/papers`
2. **获取元数据**：从 `{ID}.result.json` 读取 title/authors/abstract
3. **翻译标题**：英文→中文（保留专有名词）
4. **生成文档内容**：构造 JSON → `python3 scripts/render_paper_doc.py -i data.json --date $(date +%Y-%m-%d) -o doc.xml`
5. **创建飞书文档**：逐章 append 到指定文件夹（见铁律）
6. **生成 PDF**：`python3 scripts/html2pdf.py article.txt article.pdf --title "中文标题"`
7. **上传 PDF 到飞书云空间**
8. **批量下载 PDF 打包发送**（见 `references/pdf-export.md`）
9. **导出 Markdown 压缩包**（见 `references/markdown-export.md`）
10. **推送通知**：告知用户文档+压缩包已发送

### 博客文章下载流程（OpenAI/Anthropic/第三方）

> ⚠️ `fetch_paper.py` 仅支持 arXiv。博客文章（openai.com、anthropic.com 等）走以下流程。

**触发条件**：用户说「全部下载」或「下载第 X 篇」，且文章 URL 不是 arXiv。

**执行步骤**：

0. **判断文章类型**：URL 含 `arxiv.org` → 走 arXiv 流程（上方）；否则 → 走博客流程
1. **抓取全文**：用 `web_access_tool` fetch 抓取文章页面，提取正文内容
2. **构建 JSON**：手动整理为 render_paper_doc.py 要求的格式，保存到 `/tmp/papers-{日期}/{N}.json`
   ```json
   {
     "date": "2026-07-17",
     "title": "中文标题",
     "arxiv_id": "openai-xxx",
     "authors": "OpenAI",
     "source_url": "https://openai.com/...",
     "one_liner": "一句话理解",
     "quick_explain": {"what": "大白话", "analogy": "类比", "why_matters": "价值"},
     "sections": [{"title": "章节", "core": "内容", ...}]
   }
   ```
3. **渲染 XML**：`python3 scripts/render_paper_doc.py -i /tmp/papers-{日期}/{N}.json -o /tmp/papers-{日期}/{N}.xml`
4. **创建飞书文档**：⚠️ **必须在主会话执行**（B29 铁律），用 `--as user --parent-token HkPgfPqEhl9Qbpdr4FCcfnTjnxe`
5. **逐章 append**：串行执行，禁止并行
6. **生成 PDF**：`python3 scripts/html2pdf.py /tmp/papers-{日期}/{N}.txt /tmp/papers-{日期}/{N}.pdf --title "中文标题"`
7. **上传 PDF**：`feishu_lark_cli drive +upload --file /tmp/papers-{日期}/{N}.pdf --folder-token HkPgfPqEhl9Qbpdr4FCcfnTjnxe --as user`
8. **打包发送**：全部完成后 tar czf 打包 PDF + MD 发送

**⚠️ 关键约束**：
- 文档创建和 PDF 上传**禁止委派子 Agent**（B29）
- sections 内容必须从原文提炼，不能编造
- 摘要和标题必须中文

### render_paper_doc.py 用法

```bash
python3 scripts/render_paper_doc.py -i paper_data.json -o doc.xml
python3 scripts/render_paper_doc.py -i paper_data.json --validate  # 仅校验
```

JSON 核心字段：`title`, `arxiv_id`, `authors`, `source_url`, `one_liner`, `quick_explain{what,analogy,why_matters}`, `sections[]`。

> `quick_explain` 必须用大白话，禁止术语。读者应是「完全不了解这个领域的人」。

### 输出文件

| 文件 | 内容 |
|------|------|
| `{ID}.html.txt` | HTML 全文文本 |
| `{ID}-source.tar.gz` | LaTeX 源码压缩包 |
| `{ID}.latex.txt` | 提取的 LaTeX 纯文本 |
| `{ID}.pdf` | PDF 原文件 |
| `{ID}.result.json` | 元数据 + 下载结果 JSON |

---

## 铁律（强制遵守）

### 铁律一：按 writing-guidelines.md 拆解

所有下载的文章必须按 `memory/writing-guidelines.md` 的章节模板拆解，不能搬运原文。

Callout 颜色语义（必须一致）：
- 🟠 橙色：核心定义、一句话理解
- 🔵 蓝色：面试话术
- 🔴 红色：踩坑、风险警告
- 🟡 黄色：关联章节
- 🟢 绿色：最佳实践

### 铁律二：文档所有权授予用户

所有 `docs +create` 创建的文档，**必须确保用户拥有 full_access 权限**。

| 场景 | 正确做法 | ❌ 错误做法 |
|------|---------|------------|
| 主会话（飞书 DM） | `--as user` | 用 `--as bot` |
| 子 Agent | `--as user`（失败则 `--as bot` + 手动授权） | `--as bot` 不授权 |
| 定时任务（cron） | `--as bot` + 手动授权 | `--as bot` 不授权 |

**降级策略**：先 `--as user` → 失败则 `--as bot` + `drive +permission` 手动授权 → 再失败则提醒用户手动授权。

用户 open_id：`ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef`

### 铁律三：保存到指定文件夹

- 目标文件夹 token：`HkPgfPqEhl9Qbpdr4FCcfnTjnxe`
- 创建命令：`docs +create --api-version v2 --as user --parent-token HkPgfPqEhl9Qbpdr4FCcfnTjnxe`

### 铁律四：XML 属性一律用单引号

- ✅ `<callout emoji='💡' background-color='orange'>`
- ❌ `<callout emoji="💡" background-color="orange">`

### 铁律五：append 必须串行

逐章顺序 append，禁止并行。违反会导致章节乱序。

### 铁律六：单次 append 不超过 1 章

每次 append 只传一个章节的完整内容。

### 铁律七：overwrite 前先确认

仅在文档刚创建只有骨架时使用 overwrite。

### 铁律八：PDF 生成必须验证中文

```bash
python3 -c "import fitz; doc=fitz.open('output.pdf'); text=doc[0].get_text(); assert '?' not in text[:100], '中文变问号了！'; print('✅ 验证通过')"
```

### 铁律九：文档密级设置（手动步骤）

所有创建的飞书文档，**必须提醒用户手动设置密级**。

> ⚠️ 密级由企业安全策略自动打标（默认 L3-机密文件），**无 API 可修改**。创建文档后必须提醒用户在文档 UI 中降级。

**操作步骤**：
1. 打开文档 → 顶部橙色横幅点击「设置密级」
2. 选择合适密级（公开技术文章建议 L1-公开或 L2-内部）
3. 确认保存

**推送通知中必须包含**：「⚠️ 请手动设置文档密级：打开文档 → 顶部横幅 → 设置密级」

### 铁律十：禁止自行新增脚本替代现有工具链

遇到工具缺失先报告用户，用户确认后才可新增。

### 铁律十一：摘要和标题必须用中文

所有推送的三句话摘要和文档标题必须用中文撰写。英文原文需翻译后输出。

---

## 错误排查表

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| RSS 抓取为空 | 源 URL 变更或网络不通 | 用 web_access_tool 抓取 HTML fallback |
| 评分后无正分文章 | 全是营销/二手内容 | 从 evergreen_articles.yml 补课 |
| `docs +create` 报 `no permission` | bot 对用户文件夹无权限 | 改 `--as user` 或手动 `drive +permission` |
| `args: must be array` | XML 用了双引号 | 改为单引号（铁律四） |
| append 后章节乱序 | 并行调用了 append | 改为串行（铁律五） |
| PDF 中文变问号 | 字体渲染失败 | 检查 html2pdf.py 的 font 设置（铁律八） |
| `--output` 报路径错误 | 用了绝对路径 | 改为相对路径 |
| fetch_rss.py 超时 | 单源超过 30 秒 | 跳过该源，记录错误继续 |
| 文档创建后用户打不开 | 缺少 full_access 授权 | 执行 drive +permission 授权（铁律二） |
| 飞书消息发送失败 | target 格式错误 | 确认格式：`user:ou_xxx` |

---

## 状态管理

- 状态文件：`state/seen.json`
- 格式：`{ "url": "2026-07-01", ... }`
- 每次推送后更新
- 30 天前条目自动清理（`state_manager.py cleanup`）

## 反馈机制

- 用户 👍/👎 → `state_manager.py feedback <url> up|down`
- 连续 3 天 👎 的主题降权（-1）
- 用户手动说"关注 XX"的主题加权（+2）

---

## 脚本参数速查

| 脚本 | 参数 | 必填 | 说明 |
|------|------|------|------|
| `fetch_rss.py` | `<url>` | 是 | RSS 源 URL |
| `score_articles.py` | `<input.json>` | 是 | 文章 JSON 文件路径 |
| `state_manager.py check` | `<url>` | 是 | 检查 URL 是否已推送 |
| `state_manager.py mark` | `<url>` | 是 | 标记 URL 为已推送 |
| `state_manager.py feedback` | `<url> <up\|down>` | 是 | 记录用户反馈 |
| `state_manager.py stats` | 无 | — | 查看状态统计 |
| `state_manager.py cleanup` | 无 | — | 清理 30 天前记录 |
| `render_digest.py` | `<scored.json>` | 是 | 渲染推送文本 |
| `fetch_paper.py` | `<ID> -o <dir>` | 是 | 下载论文，三路 fallback |
| `render_paper_doc.py` | `-i <json> -o <xml>` | 是 | JSON→飞书 XML |
| `render_paper_doc.py` | `-i <json> --validate` | — | 仅校验 JSON |
| `html2pdf.py` | `<input.txt> <output.pdf> --title <t>` | 是 | 文本→PDF |
| `convert_xml_to_md.py` | `<input.xml> -o <output.md>` | 是 | 飞书 XML→Markdown |
| `track_user.py push` | `--date <d> --count <n> --urls <u>` | 是 | 记录推送统计 |
| `track_user.py stats` | 无 | — | 查看推送统计 |

---

## 为什么这是一个多步骤 Skill

- 该任务包含 **7+ 个步骤**（抓取→评分→去重→摘要→渲染→推送→记录）
- 关键依赖：评分依赖抓取结果，去重依赖评分结果，渲染依赖去重+摘要
- 中间产物：`/tmp/rss_articles.json` → `/tmp/scored.json` → `/tmp/digest.txt`
- 失败点：RSS 源不可用、评分脚本异常、飞书 API 限流
- 单步骤 skill 无法覆盖的原因：每步有独立逻辑和状态，需要串联执行

## Execution Contract

```yaml
execution_contract:
  contract_version: 1.0.0
  side_effect_level: medium
  timeout:
    per_step: 30s
    total: 10m
  retry:
    max_attempts: 2
    strategy: exponential_backoff
    retryable_errors: ["network_timeout", "rate_limit", "429"]
  idempotent: true  # 去重机制保证幂等
```

## Output Contract

```yaml
output_contract:
  format: plain_text
  language: zh-CN  # ⛔ 强制中文
  structure:
    - header: "📡 今日 AI 研究雷达 | {日期}"
    - articles: 最多 3 篇（每篇含标题/来源/类型/星级/链接/三句话摘要）
    - evergreen: 补课文章（如有）
  constraints:
    - summary_must_be_chinese: true
    - title_must_be_chinese: true
    - max_articles: 3
```

## Checkpoint 设计

```yaml
checkpoints:
  - name: rss_fetched
    file: /tmp/rss_articles.json
    validation: "非空 JSON 数组"
  - name: scored
    file: /tmp/scored.json
    validation: "每篇文章含 score 字段"
  - name: deduplicated
    file: /tmp/scored.json  # 去重后同文件
    validation: "seen.json 中无重复 URL"
  - name: rendered
    file: /tmp/digest.txt
    validation: "非空文本，含 '📡'"
```

## 终态定义

```yaml
final_states:
  success: "推送成功 + track_user.py 记录完成"
  partial_success: "推送成功但记录失败（不影响用户体验）"
  failed: "推送失败（所有源都失败 或 飞书 API 异常）"
  fallback: "无新内容，已推送补课文章"
```

## 失败处理

| 阶段 | 失败情况 | 处理 |
|------|---------|------|
| RSS 抓取 | 单源失败 | 跳过，继续其他源 |
| RSS 抓取 | 全部失败 | 推送"今日雷达异常"通知 |
| 评分 | 脚本异常 | 重试 1 次，仍失败则推送错误通知 |
| 去重 | 全部已推送 | 进入补课模式 |
| 摘要生成 | LLM 异常 | 用文章原始 description 兜底 |
| 飞书推送 | API 限流 | 等待 5 秒重试，最多 3 次 |
| 文档创建 | 权限不足 | 降级策略（铁律二） |

---

## 参考文档（按需读取）

- `references/markdown-export.md` — 本地 Markdown 导出流程
- `references/pdf-export.md` — PDF 批量下载流程
- `references/evergreen_articles.yml` — 补课文章池
- `references/sources.yml` — RSS 源配置
- `references/eval_keywords.yml` — 评分关键词
