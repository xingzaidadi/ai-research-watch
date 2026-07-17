#!/usr/bin/env python3
"""
AI Research Watch - 飞书文档渲染器
将论文元数据 + 分析内容渲染为飞书 DocxXML 格式

用法：
  # 从 JSON 文件读取
  python3 render_paper_doc.py --input paper_data.json

  # 从 stdin 读取
  echo '{"title":"...","sections":[...]}' | python3 render_paper_doc.py

  # 输出到文件
  python3 render_paper_doc.py --input paper_data.json --output doc_content.xml

JSON 输入格式：
{
  "date": "2026-07-04",
  "title": "论文标题",
  "arxiv_id": "2607.01465",
  "authors": "Author A, Author B",
  "source_url": "https://arxiv.org/abs/2607.01465",
  "github_url": "https://github.com/...",  // 可选
  "one_liner": "一句话理解...",
  "quick_explain": {
    "what": "这东西在干嘛（大白话，禁止术语）",
    "analogy": "打个比方（生活化类比）",
    "why_matters": "为什么重要（一句话说清价值）"
  },
  "sections": [
    {
      "title": "第一章、章节标题",
      "anchor": "一句话锚定",
      "why": "为什么需要它？（场景故事）",
      "core": "核心拆解内容（支持 HTML）",
      "pitfalls": [
        {"problem": "问题", "consequence": "后果", "solution": "方案"}
      ],
      "related": [
        {"concept": "概念", "chapter": "对应章节"}
      ],
      "remember": "本章最该记住的一句话",
      "interview_qa": [
        {"q": "面试官问题", "a": "你的回答"}
      ]
    }
  ]
}
"""

import argparse
import json
import sys
import re
from datetime import datetime
from pathlib import Path


def escape_xml(text: str) -> str:
    """转义 XML 特殊字符"""
    if not text:
        return ""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def render_section(section: dict, index: int) -> str:
    """渲染一个章节为飞书 XML"""
    lines = []

    # 章节标题
    title = section.get("title", f"第{index}章")
    lines.append(f'<h1>{escape_xml(title)}</h1>')

    # 一句话锚定
    anchor = section.get("anchor", "")
    if anchor:
        lines.append(f'<blockquote>📌 {escape_xml(anchor)}</blockquote>')

    # 为什么需要它
    why = section.get("why", "")
    if why:
        lines.append('<h2>🔍 为什么需要它？</h2>')
        # 支持多段落（用 \n\n 分隔）
        for para in why.split("\n\n"):
            para = para.strip()
            if para:
                lines.append(f'<p>{escape_xml(para)}</p>')

    # 核心拆解
    core = section.get("core", "")
    if core:
        lines.append('<h2>🧩 核心拆解</h2>')
        # core 可以包含 HTML 标签（table, callout 等），不转义
        lines.append(core)

    # 踩坑表格
    pitfalls = section.get("pitfalls", [])
    if pitfalls:
        lines.append('<h2>⚠️ 边学边踩坑</h2>')
        lines.append('<table><tr><th>问题</th><th>后果</th><th>方案</th></tr>')
        for p in pitfalls:
            lines.append(f'<tr><td>{escape_xml(p.get("problem", ""))}</td>'
                        f'<td>{escape_xml(p.get("consequence", ""))}</td>'
                        f'<td>{escape_xml(p.get("solution", ""))}</td></tr>')
        lines.append('</table>')

    # 关联章节
    related = section.get("related", [])
    if related:
        lines.append('<h2>🔗 关联章节</h2>')
        lines.append('<table><tr><th>概念</th><th>对应章节</th></tr>')
        for r in related:
            lines.append(f'<tr><td>{escape_xml(r.get("concept", ""))}</td>'
                        f'<td>{escape_xml(r.get("chapter", ""))}</td></tr>')
        lines.append('</table>')

    # 本章最该记住的一句话
    remember = section.get("remember", "")
    if remember:
        lines.append('<h2>📌 本章最该记住的一句话</h2>')
        lines.append(f'<blockquote>{escape_xml(remember)}</blockquote>')

    # 面试准备
    qa_list = section.get("interview_qa", [])
    if qa_list:
        lines.append('<h2>💬 面试准备</h2>')
        qa_text = ""
        for qa in qa_list:
            qa_text += f'Q: {escape_xml(qa.get("q", ""))}<br/>A: {escape_xml(qa.get("a", ""))}<br/><br/>'
        lines.append(f'<callout emoji="💬" background-color="blue"><b>面试官可能这么问：</b><br/>{qa_text}</callout>')

    # 分割线
    lines.append('<hr/>')

    return "\n".join(lines)


def render_download_links(data: dict) -> str:
    """渲染下载链接"""
    lines = ['<h1>📎 下载链接</h1>']

    arxiv_id = data.get("arxiv_id", "")
    github_url = data.get("github_url", "")
    source_url = data.get("source_url", "")

    if arxiv_id:
        parts = [f'📄 <a href="https://arxiv.org/pdf/{arxiv_id}">PDF 全文</a>',
                f'📋 <a href="https://arxiv.org/abs/{arxiv_id}">arXiv 页面</a>']
        if github_url:
            parts.append(f'💻 <a href="{escape_xml(github_url)}">GitHub 代码</a>')
        lines.append(f'<p>{" | ".join(parts)}</p>')
    elif source_url:
        parts = [f'📄 <a href="{escape_xml(source_url)}">原文</a>']
        if github_url:
            parts.append(f'💻 <a href="{escape_xml(github_url)}">相关代码</a>')
        lines.append(f'<p>{" | ".join(parts)}</p>')

    return "\n".join(lines)


def render_document(data: dict, date_override: str = None) -> str:
    """渲染完整飞书文档 XML"""
    date = date_override or data.get("date", datetime.now().strftime("%Y-%m-%d"))
    title = data.get("title", "未命名论文")
    authors = data.get("authors", "")
    source_url = data.get("source_url", "")
    one_liner = data.get("one_liner", "")
    sections = data.get("sections", [])

    lines = []

    # 标题
    doc_title = f"{date}_{title}"
    lines.append(f'<title>{escape_xml(doc_title)}</title>')

    # 一句话理解 callout
    if one_liner:
        lines.append(f'<callout emoji="💡" background-color="orange"><b>一句话理解</b>：{escape_xml(one_liner)}</callout>')

    # 来源信息
    source_parts = []
    if source_url:
        source_parts.append(f'来源：<a href="{escape_xml(source_url)}">{escape_xml(source_url)}</a>')
    if authors:
        source_parts.append(f'作者：{escape_xml(authors)}')
    if source_parts:
        lines.append(f'<p><i>{" | ".join(source_parts)}</i></p>')

    lines.append('<hr/>')

    # 30秒速懂（给非专业人士的直觉解释）
    quick = data.get("quick_explain", {})
    if quick:
        what = quick.get("what", "")
        analogy = quick.get("analogy", "")
        why_matters = quick.get("why_matters", "")
        if what or analogy or why_matters:
            lines.append('<callout emoji="🧪" background-color="green"><b>30秒速懂</b>（给非专业人士的直觉解释）')
            if what:
                lines.append(f'• <b>这东西在干嘛</b>：{escape_xml(what)}')
            if analogy:
                lines.append(f'• <b>打个比方</b>：{escape_xml(analogy)}')
            if why_matters:
                lines.append(f'• <b>为什么重要</b>：{escape_xml(why_matters)}')
            lines.append('</callout>')
            lines.append('<hr/>')

    # 各章节
    for i, section in enumerate(sections, 1):
        lines.append(render_section(section, i))

    # 下载链接
    lines.append(render_download_links(data))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='飞书文档渲染器 — 论文内容 → DocxXML')
    parser.add_argument('--input', '-i', help='JSON 输入文件（不传则从 stdin 读取）')
    parser.add_argument('--output', '-o', help='输出文件（不传则输出到 stdout）')
    parser.add_argument('--date', '-d', help='覆盖文档日期（默认用 JSON 中的 date 字段）')
    parser.add_argument('--validate', action='store_true', help='仅校验 JSON 格式')
    args = parser.parse_args()

    # 读取输入
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    # 校验
    if args.validate:
        required = ["title"]
        missing = [k for k in required if k not in data]
        if missing:
            print(f"❌ 缺少必填字段: {missing}", file=sys.stderr)
            sys.exit(1)
        print("✅ JSON 格式校验通过")
        sys.exit(0)

    # 渲染
    xml_content = render_document(data, date_override=args.date)

    # 输出
    if args.output:
        Path(args.output).write_text(xml_content, encoding='utf-8')
        print(f"✅ 已输出到 {args.output} ({len(xml_content)} bytes)", file=sys.stderr)
    else:
        print(xml_content)


if __name__ == '__main__':
    main()
