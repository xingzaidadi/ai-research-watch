# PDF 批量下载流程

每次完成飞书文档创建后，**必须自动执行**此流程，将论文库文件夹中所有 PDF 下载到本地并打包发送给用户。

## 工具链

- `feishu_lark_cli drive files list --params '{"folder_token":"HkPgfPqEhl9Qbpdr4FCcfnTjnxe"}' --as user`
- `feishu_lark_cli drive +download --file-token <token> --as user --output <filename>`
- `tar czf`
- `feishu_lark_cli im +messages-send --user-id ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef --file all-papers-YYYY-MM-DD.tar.gz`

## 执行步骤

1. **列出文件夹内容**：
   ```bash
   feishu_lark_cli drive files list --params '{"folder_token":"HkPgfPqEhl9Qbpdr4FCcfnTjnxe","page_size":"200"}' --as user
   ```
2. **筛选 PDF**：`type: "file"` 且 `name` 以 `.pdf` 结尾
3. **批量下载**：
   - `mkdir -p pdfs`
   - 对每个 PDF：`feishu_lark_cli drive +download --file-token <token> --as user --output <filename>.pdf --overwrite`
   - ⚠️ `--output` 必须用**相对路径**
   - 文件名用英文，避免特殊字符
4. **打包**：`tar czf all-papers-$(date +%Y-%m-%d).tar.gz pdfs/*.pdf`
5. **发送**：`feishu_lark_cli im +messages-send --user-id ou_0f523a90cdfbb1cc84ccf67ba3fcf7ef --file all-papers-$(date +%Y-%m-%d).tar.gz`
6. **推送解压说明**：附文件列表和 `tar xzf all-papers-$(date +%Y-%m-%d).tar.gz`

## 两种压缩包

- `papers-export-YYYY-MM-DD.tar.gz`（Markdown）+ `all-papers-YYYY-MM-DD.tar.gz`（PDF）
- 分两次发送，避免单个文件过大

## 错误处理

| 情况 | 处理 |
|------|------|
| 下载失败 | 跳过该文件，在报告中标注 |
| 文件夹为空 | 跳过 PDF 下载，仅发 Markdown 包 |
| 网络超时 | 自动重试，最多 3 次 |
