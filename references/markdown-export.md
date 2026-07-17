# 本地 Markdown 导出流程

每次完成飞书文档创建后，**必须自动执行**此流程，将文档导出为 Markdown 压缩包发送给用户。

## 工具链

- `feishu_lark_cli docs +fetch --api-version v2 --as user --doc <token> --scope full`
- `scripts/convert_xml_to_md.py`
- `tar czf`
- `feishu_lark_cli im +messages-send --user-id ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef --file papers-export-YYYY-MM-DD.tar.gz`

## 执行步骤

1. **收集文档 token**：从本次创建的所有飞书文档中收集 document_id
2. **批量 fetch + 转换**：每个文档执行 `docs +fetch`，content 传入 `convert_xml_to_md.py`
   - 可并行 fetch（每次最多 5 个，避免限流）
   - 输出命名：`{日期}_{简称}.md`
3. **打包**：`tar czf papers-export-$(date +%Y-%m-%d).tar.gz md/*.md`
4. **发送**：`feishu_lark_cli im +messages-send --user-id ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef --file papers-export-$(date +%Y-%m-%d).tar.gz`
5. **推送解压说明**

## convert_xml_to_md.py 转换规则

- `<title>` → `# 标题`
- `<h1>/<h2>/<h3>` → `# / ## / ###`
- `<b>/<strong>` → `**加粗**`
- `<i>/<em>` → `*斜体*`
- `<a href="url">text</a>` → `[text](url)`
- `<code>` → `` `代码` ``
- `<callout>` → `> blockquote`
- `<table>` → Markdown 表格
- `<hr/>` → `---`
- 清除所有剩余 HTML 标签

## 错误处理

| 情况 | 处理 |
|------|------|
| fetch 失败（429 限流） | 自动重试，最多 3 次，每次间隔 5 秒 |
| fetch 失败（权限问题） | 跳过该文档，在报告中标注 |
| 转换失败 | 保留原始 XML，在报告中标注 |
