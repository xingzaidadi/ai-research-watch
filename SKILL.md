# AI Research Watch - AI 前沿研究每日雷达

## 触发条件
- 用户说"查最新研究""AI 雷达""research watch""今日 AI 资讯"
- Cron 定时任务触发（每日 09:00 Asia/Shanghai）
- 用户说"有没有突发文章"（实时模式）

## 工作流程

```mermaid
flowchart TD
    A[触发] --> B{模式判断}
    B -->|每日定时| C[exec: fetch_rss.py 抓取]
    B -->|实时按需| D[web_access_tool 抓取]
    C --> E[exec: score_articles.py 评分]
    D --> E
    E --> F[exec: state_manager.py check 去重]
    F --> G{有新内容?}
    G -->|是| H[exec: render_digest.py 生成摘要]
    G -->|否| I[exec: state_manager.py 选补课文章]
    H --> J[message tool 推送飞书]
    I --> J
    J --> K[exec: state_manager.py mark 记录]
```

> ⚠️ 所有评分/去重/渲染逻辑由 Python 脚本执行，确保确定性。LLM 只负责「抓取」和「生成三句话摘要」。

## 脚本说明

| 脚本 | 作用 | 输入 | 输出 |
|------|------|------|------|
| `scripts/fetch_rss.py` | 抓取 RSS feed | URL 列表 | JSON 文章列表 |
| `scripts/score_articles.py` | 确定性评分 | 文章 JSON | 评分后 JSON |
| `scripts/state_manager.py` | 状态管理 | 子命令 | JSON 结果 |
| `scripts/render_digest.py` | 渲染推送文本 | 评分后 JSON | 格式化文本 |

### state_manager.py 子命令
- `stats` — 查看状态统计
- `check <url>` — 检查 URL 是否已推送
- `mark <url>` — 标记 URL 为已推送
- `check-title <title>` — 检查标题相似度去重
- `feedback <url> <up|down>` — 记录用户反馈
- `cleanup` — 清理 30 天前的记录

## 抓取策略

### 三层降级
1. **RSS 优先**：RSS 源直接解析 XML
2. **HTML 解析**：无 RSS 的页面用 web_access_tool 抓取
3. **搜索兜底**：前两者都失败时用 web_access_tool search

### 错误处理
- 单源失败不阻塞其他源，记录错误继续
- 所有源都失败时，推送"今日雷达异常"通知
- 超时阈值：单源 30 秒

## 评分规则

评分由 `scripts/score_articles.py` 确定性执行，规则如下：

### 正分（吸引关注）
| 条件 | 分数 |
|------|------|
| 官方 Research / Publication | +5 |
| System Card / Eval / Benchmark | +4 |
| Agent / Reasoning / Alignment / Safety | +3 |
| 模型发布 / 技术说明 | +2 |
| 含 eval_keywords.yml 中的关键词 | +1~3 |

### 负分（过滤噪音）
| 条件 | 分数 |
|------|------|
| 纯营销 / 招聘 / 合作新闻稿 | -3 |
| 非技术内容（office/funding） | -2 |
| 非官方二手转述 | -5 |
| 已在 seen.json 中 | 直接去重 |

## 去重机制
- **URL 精确去重**：seen.json 存已推送文章 URL
- **标题相似度去重**：标题 Jaccard 相似度 > 0.7 视为重复
- **保留天数**：seen.json 保留 30 天，超过自动清理

## 推送格式

```
📡 今日 AI 研究雷达 | {日期}

━━━━━━━━━━━━━━━━━━

{序号}. {标题}
📎 来源：{OpenAI / Anthropic / arXiv}
📂 类型：{Research / System Card / Eval / Model Release}
⭐ 重要程度：{★★★★★}
🔗 链接：{url}

💡 三句话总结：
• {解决什么问题}
• {用了什么方法}
• {对你的启发}

🎯 你需要关注：{关键词1}、{关键词2}

━━━━━━━━━━━━━━━━━━

{最多 3 篇新文章}

{如有补课文章}
📚 今日补课：
{补课文章摘要}
```

## 推送渠道
- **默认**：飞书私聊推送给用户（ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef）
- **紧急/突发**：标题加 🔴 前缀

## 状态管理
- 状态文件：`state/seen.json`
- 格式：`{ "url": "2026-07-01", ... }`
- 每次推送后更新
- 30 天前的条目自动清理

## 反馈机制
- 推送后等待用户 👍/👎 反馈
- 连续 3 天 👎 的主题降权（评分 -1）
- 用户手动说"关注 XX"的主题加权（评分 +2）

## 补课机制
- 当天无新内容时触发
- 从 `references/evergreen_articles.yml` 中选取
- 优先选未推送过的
- 每篇最多推送 2 次后移出候选池

---

## 本地 Markdown 导出（强制步骤）

每次完成飞书文档创建后，**必须自动执行**以下流程，将所有已创建的文档导出为 Markdown 并发送压缩包给用户，供用户下载到本地桌面。

### 为什么需要这一步
用户需要在本地阅读/标注/备份文章，飞书在线阅读不够方便。导出为 Markdown 压缩包后，用户直接下载到桌面解压即可。

### 工具链
- `feishu_lark_cli docs +fetch --api-version v2 --as user --doc <token> --scope full`：获取文档 DocxXML 内容
- `scripts/convert_xml_to_md.py`：DocxXML → Markdown 转换脚本
- `tar czf`：打包压缩
- `feishu_lark_cli im +messages-send --user-id ou_xxx --file xxx.tar.gz`：发送压缩包给用户

### 执行步骤（每次下载论文后自动执行）

1. **收集文档 token**：从本次创建的所有飞书文档中收集 document_id（包括之前已创建但本次未更新的文档）
2. **批量 fetch + 转换**：对每个文档 token 执行 `docs +fetch`，将返回的 content 字段传入 `convert_xml_to_md.py` 转换为 Markdown
   - 可并行 fetch 多个文档（每次最多5个并行调用以避免限流）
   - 输出文件命名：`{日期}_{简称}.md`（如 `07-14_Building_Agents.md`）
3. **打包**：`tar czf papers-export.tar.gz papers-export/*.md`
4. **发送给用户**：
   ```bash
   feishu_lark_cli im +messages-send --user-id ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef --file papers-export.tar.gz
   ```
5. **推送解压说明**：告知用户文件已发送，附解压命令 `tar xzf papers-export.tar.gz`

### convert_xml_to_md.py 转换规则
- `<title>` → `# 标题`
- `<h1>/<h2>/<h3>` → `# / ## / ###`
- `<b>/<strong>` → `**加粗**`
- `<i>/<em>` → `*斜体*`
- `<a href="url">text</a>` → `[text](url)`
- `<code>` → `` `代码` ``
- `<callout>` → `> blockquote`
- `<blockquote>` → `> blockquote`
- `<table>` → Markdown 表格
- `<hr/>` → `---`
- 清除所有剩余 HTML 标签

### 错误处理
- fetch 失败（429 限流）：自动重试，最多3次，每次间隔5秒
- fetch 失败（权限问题）：跳过该文档，在最终报告中标注
- 转换失败：保留原始 XML 内容，在最终报告中标注

---

## PDF 批量下载（强制步骤）

每次完成飞书文档创建后，**必须自动执行**以下流程，将论文库文件夹中所有 PDF 下载到本地并打包发送给用户。

### 为什么需要这一步
用户需要在本地阅读/标注 PDF 文件。通过 `drive +download` 接口批量下载后打包发送，用户直接下载到桌面解压即可。

### 工具链
- `feishu_lark_cli drive files list --params '{"folder_token":"HkPgfPqEhl9Qbpdr4FCcfnTjnxe"}' --as user`：列出文件夹下所有文件
- `feishu_lark_cli drive +download --file-token <token> --as user --output <filename>`：下载单个 PDF（注意：`--output` 只接受相对路径）
- `tar czf`：打包压缩
- `feishu_lark_cli im +messages-send --user-id ou_xxx --file xxx.tar.gz`：发送压缩包给用户

### 执行步骤（每次下载论文后自动执行）

1. **列出文件夹内容**：
   ```bash
   feishu_lark_cli drive files list --params '{"folder_token":"HkPgfPqEhl9Qbpdr4FCcfnTjnxe","page_size":"200"}' --as user
   ```
2. **筛选 PDF 文件**：从返回结果中筛选 `type: "file"` 且 `name` 以 `.pdf` 结尾的文件
3. **批量下载 PDF**：
   - 先创建临时目录：`mkdir -p pdfs`
   - 对每个 PDF 文件执行下载：
     ```bash
     feishu_lark_cli drive +download --file-token <token> --as user --output <filename>.pdf --overwrite
     ```
   - ⚠️ `--output` 必须用**相对路径**（相对于当前工作目录），不能用绝对路径
   - ⚠️ 文件名中避免特殊字符，用英文命名（如 `1_Building_Agents.pdf`）
4. **打包**：`tar czf all-papers.tar.gz pdfs/*.pdf`
5. **发送给用户**：
   ```bash
   feishu_lark_cli im +messages-send --user-id ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef --file all-papers.tar.gz
   ```
6. **推送解压说明**：告知用户文件已发送，附文件列表和解压命令

### 两种压缩包一起发
Markdown 压缩包和 PDF 压缩包可以一起发给用户（两个独立文件），或者合并为一个压缩包。
- 建议分开打包：`papers-export.tar.gz`（Markdown）+ `all-papers.tar.gz`（PDF）
- 分两次发送，避免单个文件过大

### 错误处理
- 下载失败：跳过该文件，在最终报告中标注失败的文件名
- 文件夹为空：跳过 PDF 下载步骤，仅发送 Markdown 压缩包
- 网络超时：自动重试，最多3次

---

## 论文全文抓取（深度阅读模式）

### 触发条件
- 用户说"下载论文全文""获取论文原文""抓取论文""download paper" "fetch paper" "下载这篇文章" "把这篇搞下来"
- 用户给出 arXiv 链接/ID 要求获取内容
- 用户给出任意文章链接（博客/arXiv/新闻）要求下载
- 用户说"把这篇论文搞下来""原文在哪"

### 抓取策略（三路 fallback，确保成功）

| 优先级 | 策略 | 优点 | 缺点 |
|--------|------|------|------|
| 1️⃣ | arXiv HTML | 速度快、可读文本 | 非所有论文都有 |
| 2️⃣ | arXiv LaTeX 源码 | 含公式/代码/完整内容 | 需解压解析 |
| 3️⃣ | arXiv PDF | 总是可用 | 文本提取困难 |

**关键设计**：串行尝试，每步成功都继续尝试后续策略作为备份，最终选最佳格式。

### 工作流程

```mermaid
flowchart TD
    A[用户请求] --> B[extract_arxiv_id]
    B --> C[获取元数据 title/authors/abstract]
    C --> D[策略1: arXiv HTML]
    D -->|成功| E[保存文本]
    D -->|失败| F[策略2: LaTeX 源码]
    E --> F
    F -->|成功| G[解压+提取文本]
    F -->|失败| H[策略3: PDF]
    G --> H
    H --> I[保存所有格式到本地]
    I --> J[创建飞书文档到指定文件夹]
    J --> K[生成阅读摘要]
```

### 保存为飞书文档（强制规则）

抓取完成后，将论文内容保存为飞书文档，**必须遵守以下三条铁律**：

#### 铁律一：按 writing-guidelines.md 拆解

所有下载的文章必须按 `memory/writing-guidelines.md` 的章节模板拆解，不能只是搬运原文。

每个章节必须包含：
- `> 📌 一句话锚定`（blockquote）
- `## 🔍 为什么需要它？`（场景故事切入）
- `## 🧩 核心拆解`（文字拆解 + 对比表格 + 橙色 callout）
- `## ⚠️ 边学边踩坑`（问题→后果→方案表格）
- `## 🔗 关联章节`（前置预告 + 回溯引用）
- `## 📌 本章最该记住的一句话`
- `## 💬 面试准备`（蓝色 callout Q&A）

Callout 颜色语义（必须一致）：
- 🟠 橙色：核心定义、一句话理解
- 🔵 蓝色：面试话术
- 🔴 红色：踩坑、风险警告
- 🟡 黄色：关联章节
- 🟢 绿色：最佳实践

#### 铁律二：文档所有权授予用户（⚠️ 关键铁律，违反=用户打不开）

所有用 `feishu_lark_cli docs +create` 创建的文档，**必须确保用户拥有 full_access 权限**。

**身份选择规则（严格遵守）：**

| 场景 | 正确做法 | ❌ 错误做法 |
|------|---------|------------|
| 主会话（飞书 DM 触发） | `--as user`（用户 OAuth 可用） | 用 `--as bot` |
| 子任务/子 Agent（sessions_spawn） | `--as user`（仍可用，see below） | 用 `--as bot` |
| 定时任务（cron） | `--as bot` + 手动授权 | `--as bot` + 不授权 |

**⚠️ 子 Agent 身份限制（2026-07-05 实测确认）：**
- 子 Agent 中 `--as user` **可能失败**（报 `用户身份不可用：缺少 senderOpenId`）
- 如果 `--as user` 失败，**必须先用 `--as bot` 创建文档，然后立即手动授权用户**：
  ```
  feishu_lark_cli drive +permission --token <doc_token> --type docx --member --member-id ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef --perm full_access
  ```
- **禁止跳过授权步骤**：`--as bot` 创建后，CLI 自动授权会因 `no current CLI user open_id` 被 skip，必须手动补授权

**降级策略（按顺序尝试）：**
1. 先尝试 `--as user` + `--parent-token HkPgfPqEhl9Qbpdr4FCcfnTjnxe`（最佳：用户身份直接有文件夹权限）
2. 若报 `用户身份不可用`，改用 `--as bot` + `--parent-token` + 立即 `drive +permission` 授权
3. 若 `drive +permission` 也失败（bot 无文件夹权限），创建后**必须在报告中提醒用户手动授权**

用户 open_id：`ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef`

#### 铁律三：保存到指定文件夹

所有文档必须保存到用户指定的论文库文件夹：
- **目标文件夹 token**：`HkPgfPqEhl9Qbpdr4FCcfnTjnxe`
- **创建命令（优先）**：`feishu_lark_cli docs +create --api-version v2 --as user --parent-token HkPgfPqEhl9Qbpdr4FCcfnTjnxe --content '...'`
- **⚠️ 禁止 `--as bot` + `--parent-token` 直接创建**：bot 对用户文件夹无写权限，会报 `destination parent no permission`
- **降级方案**：如果无法用 `--as user`，先创建文档（不带 `--parent-token`），再授权用户，由用户手动移动到目标文件夹

#### 文档命名
- **arXiv 论文**：`{日期}_{中文标题}`
- **博客文章**：`{日期}_{来源}_{中文标题}`
- **⚠️ 日期铁律**：文档标题中的日期必须是**创建文档当天的日期**，不是论文下载日期。使用 `render_paper_doc.py --date $(date +%Y-%m-%d)` 覆盖 JSON 中的旧日期。
- **⚠️ 语言铁律**：文档标题必须用**中文**，方便后期阅读和检索。英文论文标题需翻译为中文（保留专有名词如 CoRe、DPO 等）。

#### 文档内容结构模板
```xml
<title>{日期}_{标题}</title>
<callout emoji="💡" background-color="orange"><b>一句话理解</b>：{核心结论}</callout>
<p><i>来源：{来源链接} | 作者：{作者}</i></p>
<hr/>
<callout emoji="🧪" background-color="green"><b>30秒速懂</b>（给非专业人士的直觉解释）
• <b>这东西在干嘛</b>：{用一句话大白话说明，禁止术语}
• <b>打个比方</b>：{一个生活化/工作中的类比，让读者秒懂}
• <b>为什么重要</b>：{一句话说清价值，比如「让搜索结果更准」而不是「提升了 ranking metric」}
</callout>
<hr/>
# 第一章、{章节标题}
> 📌 {一句话锚定}
## 🔍 为什么需要它？
{场景故事}
## 🧩 核心拆解
{文字+表格+callout}
## ⚠️ 边学边踩坑
{踩坑表格}
## 🔗 关联章节
{双向织网表}
## 📌 本章最该记住的一句话
> {一句话}
## 💬 面试准备
<callout emoji="💬" background-color="blue">{Q&A}</callout>
<hr/>
{...后续章节...}

## 📎 下载链接
{根据文章类型选择对应格式}
```

#### 下载链接格式（按文章类型区分）

**arXiv 论文：**
```xml
<h1>📎 下载链接</h1>
<p>📄 <a href="https://arxiv.org/pdf/{ID}">PDF 全文</a> | 📋 <a href="https://arxiv.org/abs/{ID}">arXiv 页面</a> | 💻 <a href="{github_url}">GitHub 代码</a></p>
```
- 三个入口都有就全放，缺哪个就不放哪个，别凑数

**博客文章（Anthropic/OpenAI/Google 等）：**
```xml
<h1>📎 原文链接</h1>
<p>📄 <a href="{original_url}">原文</a> | 📥 <a href="{pdf_url}">PDF 离线版</a> | 💻 <a href="{related_github}">相关代码/ Cookbook</a></p>
```
- 原文必放，PDF 离线版必生成（用 `scripts/html2pdf.py`），相关代码/ Cookbook 有就放，没有就不放
- PDF 上传到飞书云空间，链接填入文档

### PDF 生成（所有文章类型通用）

```bash
# 将文章内容转为 PDF
python3 scripts/html2pdf.py /tmp/papers/article.txt /tmp/papers/article.pdf --title "中文标题"
```

- arXiv 论文：`fetch_paper.py` 已自动下载 PDF（`{ID}.pdf`），直接上传
- 博客文章：用 `html2pdf.py` 从抓取的文本内容生成 PDF
- 生成后上传到飞书云空间，将下载链接填入文档的「📎 下载链接」章节

**判断逻辑：**
- URL 含 `arxiv.org` → arXiv 论文格式
- 其他 → 博客文章格式

### 执行步骤

> ⚠️ **第 0 步（强制）**：收到下载请求后，必须先执行 `ls scripts/` 确认可用脚本，再按以下步骤操作。禁止凭记忆手动 curl/python 提取。下载必须用 `fetch_paper.py`，生成文档内容必须用 `render_paper_doc.py`。如脚本缺失，先报告用户再手动补全。

0. **检查工具链**：`ls scripts/` → 确认 `fetch_paper.py`、`render_paper_doc.py`、`html2pdf.py`、`scripts/convert_xml_to_md.py` 存在
1. **下载论文**：`python3 scripts/fetch_paper.py <ID> -o /tmp/papers` → 自动三路 fallback
2. **获取元数据**：从 `{ID}.result.json` 读取 title/authors/abstract
3. **翻译标题**：将英文标题翻译为中文（保留 CoRe、DPO 等专有名词），用于文档命名
4. **生成文档内容**：构造 JSON（必须包含 `quick_explain` 字段：what=大白话、analogy=类比、why_matters=价值）→ `python3 scripts/render_paper_doc.py -i data.json --date $(date +%Y-%m-%d) -o doc.xml`
5. **创建飞书文档**：用 `feishu_lark_cli` 逐章串行追加到指定文件夹（见铁律四~七）
6. **生成 PDF**：用 `html2pdf.py` 生成离线 PDF 文件
7. **上传 PDF**：上传到飞书云空间，获取下载链接
8. **下载 PDF 到本地**（强制步骤，见下方「PDF 批量下载」章节）：批量下载论文库文件夹中所有 PDF，打包发送给用户
9. **导出 Markdown 压缩包发飞书**（强制步骤，见下方「本地 Markdown 导出」章节）：批量 fetch 文档内容转 Markdown，打包发送给用户
10. **推送通知**：告知用户文档已创建 + 两个压缩包已发送，附飞书链接 + 解压命令

### 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/fetch_paper.py` | arXiv 论文下载（三路 fallback） |
| `scripts/render_paper_doc.py` | JSON → 飞书 DocxXML（按 writing-guidelines 模板渲染） |
| `scripts/html2pdf.py` | 文章文本/Markdown → PDF 离线版 |
| `scripts/convert_xml_to_md.py` | 飞书 DocxXML → Markdown 转换 |

#### render_paper_doc.py 用法

```bash
# 输入 JSON 文件，输出飞书 XML
python3 scripts/render_paper_doc.py -i paper_data.json -o doc.xml

# 仅校验 JSON 格式
python3 scripts/render_paper_doc.py -i paper_data.json --validate
```

JSON 输入格式见脚本内 docstring，核心字段：`title`, `arxiv_id`, `authors`, `source_url`, `one_liner`, `quick_explain{what,analogy,why_matters}`, `sections[]`。每个 section 包含 `title`, `anchor`, `why`, `core`, `pitfalls[]`, `related[]`, `remember`, `interview_qa[]`。

**`quick_explain` 字段要求（铁律）**：必须用大白话写，禁止出现任何术语。读者应该是「完全不了解这个领域的人」。

### 输出文件（本地临时）

| 文件 | 内容 |
|------|------|
| `{ID}.html.txt` | HTML 全文文本 |
| `{ID}-source.tar.gz` | LaTeX 源码压缩包 |
| `{ID}-src/*.tex` | 解压后的 .tex 文件 |
| `{ID}.latex.txt` | 提取的 LaTeX 纯文本 |
| `{ID}.pdf` | PDF 原文件 |
| `{ID}.result.json` | 元数据 + 下载结果 JSON |

### ⚠️ 飞书 API 铁律（防坑）

#### 铁律四：XML 属性一律用单引号

飞书 DocxXML 的 callout 等标签属性必须用**单引号**，不能用双引号：
- ✅ `<callout emoji='💡' background-color='orange'>`
- ❌ `<callout emoji="💡" background-color="orange">`

原因：双引号在 JSON 序列化时产生 `\"` 转义，导致 `feishu_lark_cli` 的 args 被识别为 string 而非 array，报 `args: must be array` 错误。

#### 铁律五：append 必须串行，禁止并行

`feishu_lark_cli docs +update --command append` 的 API **不保证并行调用的写入顺序**。
- ✅ 逐章顺序调用：第 1 章 append → 等返回 → 第 2 章 append → 等返回 → ...
- ❌ 同时发出多个 append 请求

违反此规则会导致章节顺序乱掉。

#### 铁律六：单次 append 不超过 1 章

单次 append 的内容过长会被截断或丢失格式。每次 append 只传**一个章节**的完整内容（含所有子模块：锚定/为什么/核心拆解/踩坑/关联/面试）。如果一章内容仍然太长，拆分为“核心拆解”和“踩坑+关联+面试”两次 append。

#### 铁律七：overwrite 前先确认

使用 `--command overwrite` 会**清空整个文档**。仅在以下场景使用：
- 文档刚创建，只有骨架需要重写
- 用户明确要求重写
- 不要在有内容的文档上 overwrite

#### 铁律八：PDF 生成必须验证中文（⚠️ 2026-07-13 新增）

`html2pdf.py` 使用 PyMuPDF 内置 `china-s` 字体渲染中文。生成 PDF 后**必须验证**：
```bash
python3 -c "import fitz; doc=fitz.open('output.pdf'); text=doc[0].get_text(); assert '?' not in text[:100], '中文变问号了！'; print('✅ 验证通过')"
```
- 如果出现问号，说明字体渲染失败，禁止上传
- ⛔ 禁止使用 `helv`/`courier` 等纯英文字体渲染中文内容

#### 铁律九：禁止自行新增脚本替代现有工具链

遇到工具缺失时：
1. **先报告用户**，说明缺少什么工具、需要什么功能
2. 用户确认后才可新增脚本
3. 新增脚本必须经过完整测试（含中文、边界情况）
4. ⛔ 禁止「自己判断该怎么做」然后悄悄实现——这是 Agent 可靠性的大敌
