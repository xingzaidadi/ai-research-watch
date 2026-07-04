"#!/usr/bin/env python3
\"\"\"
AI Research Watch - \u98de\u4e66\u6587\u6863\u6e32\u67d3\u5668
\u5c06\u8bba\u6587\u5143\u6570\u636e + \u5206\u6790\u5185\u5bb9\u6e32\u67d3\u4e3a\u98de\u4e66 DocxXML \u683c\u5f0f

\u7528\u6cd5\uff1a
 # \u4ece JSON \u6587\u4ef6\u8bfb\u53d6
 python3 render_paper_doc.py --input paper_data.json

 # \u4ece stdin \u8bfb\u53d6
 echo '{\"title\":\"...\",\"sections\":[...]}' | python3 render_paper_doc.py

 # \u8f93\u51fa\u5230\u6587\u4ef6
 python3 render_paper_doc.py --input paper_data.json --output doc_content.xml

JSON \u8f93\u5165\u683c\u5f0f\uff1a
{
 \"date\": \"2026-07-04\",
 \"title\": \"\u8bba\u6587\u6807\u9898\",
 \"arxiv_id\": \"2607.01465\",
 \"authors\": \"Author A, Author B\",
 \"source_url\": \"https://arxiv.org/abs/2607.01465\",
 \"github_url\": \"https://github.com/...\", // \u53ef\u9009
 \"one_liner\": \"\u4e00\u53e5\u8bdd\u7406\u89e3...\",
 \"sections\": [
 {
 \"title\": \"\u7b2c\u4e00\u7ae0\u3001\u7ae0\u8282\u6807\u9898\",
 \"anchor\": \"\u4e00\u53e5\u8bdd\u951a\u5b9a\",
 \"why\": \"\u4e3a\u4ec0\u4e48\u9700\u8981\u5b83\uff1f\uff08\u573a\u666f\u6545\u4e8b\uff09\",
 \"core\": \"\u6838\u5fc3\u62c6\u89e3\u5185\u5bb9\uff08\u652f\u6301 HTML\uff09\",
 \"pitfalls\": [
 {\"problem\": \"\u95ee\u9898\", \"consequence\": \"\u540e\u679c\", \"solution\": \"\u65b9\u6848\"}
 ],
 \"related\": [
 {\"concept\": \"\u6982\u5ff5\", \"chapter\": \"\u5bf9\u5e94\u7ae0\u8282\"}
 ],
 \"remember\": \"\u672c\u7ae0\u6700\u8be5\u8bb0\u4f4f\u7684\u4e00\u53e5\u8bdd\",
 \"interview_qa\": [
 {\"q\": \"\u9762\u8bd5\u5b98\u95ee\u9898\", \"a\": \"\u4f60\u7684\u56de\u7b54\"}
 ]
 }
 ]
}
\"\"\"

import argparse
import json
import sys
import re
from datetime import datetime
from pathlib import Path


def escape_xml(text: str) -> str:
 \"\"\"\u8f6c\u4e49 XML \u7279\u6b8a\u5b57\u7b26\"\"\"
 if not text:
 return \"\"
 text = text.replace(\"&\", \"&amp;\")
 text = text.replace(\"<\", \"&lt;\")
 text = text.replace(\">\", \"&gt;\")
 text = text.replace('\"', \"&quot;\")
 text = text.replace(\"'\", \"&apos;\")
 return text


def render_section(section: dict, index: int) -> str:
 \"\"\"\u6e32\u67d3\u4e00\u4e2a\u7ae0\u8282\u4e3a\u98de\u4e66 XML\"\"\"
 lines = []

 # \u7ae0\u8282\u6807\u9898
 title = section.get(\"title\", f\"\u7b2c{index}\u7ae0\")
 lines.append(f'<h1>{escape_xml(title)}</h1>')

 # \u4e00\u53e5\u8bdd\u951a\u5b9a
 anchor = section.get(\"anchor\", \"\")
 if anchor:
 lines.append(f'<blockquote>\ud83d\udccc {escape_xml(anchor)}</blockquote>')

 # \u4e3a\u4ec0\u4e48\u9700\u8981\u5b83
 why = section.get(\"why\", \"\")
 if why:
 lines.append('<h2>\ud83d\udd0d \u4e3a\u4ec0\u4e48\u9700\u8981\u5b83\uff1f</h2>')
 # \u652f\u6301\u591a\u6bb5\u843d\uff08\u7528 \n\n \u5206\u9694\uff09
 for para in why.split(\"\n\n\"):
 para = para.strip()
 if para:
 lines.append(f'<p>{escape_xml(para)}</p>')

 # \u6838\u5fc3\u62c6\u89e3
 core = section.get(\"core\", \"\")
 if core:
 lines.append('<h2>\ud83e\udde9 \u6838\u5fc3\u62c6\u89e3</h2>')
 # core \u53ef\u4ee5\u5305\u542b HTML \u6807\u7b7e\uff08table, callout \u7b49\uff09\uff0c\u4e0d\u8f6c\u4e49
 lines.append(core)

 # \u8e29\u5751\u8868\u683c
 pitfalls = section.get(\"pitfalls\", [])
 if pitfalls:
 lines.append('<h2>\u26a0\ufe0f \u8fb9\u5b66\u8fb9\u8e29\u5751</h2>')
 lines.append('<table><tr><th>\u95ee\u9898</th><th>\u540e\u679c</th><th>\u65b9\u6848</th></tr>')
 for p in pitfalls:
 lines.append(f'<tr><td>{escape_xml(p.get(\"problem\", \"\"))}</td>'
 f'<td>{escape_xml(p.get(\"consequence\", \"\"))}</td>'
 f'<td>{escape_xml(p.get(\"solution\", \"\"))}</td></tr>')
 lines.append('</table>')

 # \u5173\u8054\u7ae0\u8282
 related = section.get(\"related\", [])
 if related:
 lines.append('<h2>\ud83d\udd17 \u5173\u8054\u7ae0\u8282</h2>')
 lines.append('<table><tr><th>\u6982\u5ff5</th><th>\u5bf9\u5e94\u7ae0\u8282</th></tr>')
 for r in related:
 lines.append(f'<tr><td>{escape_xml(r.get(\"concept\", \"\"))}</td>'
 f'<td>{escape_xml(r.get(\"chapter\", \"\"))}</td></tr>')
 lines.append('</table>')

 # \u672c\u7ae0\u6700\u8be5\u8bb0\u4f4f\u7684\u4e00\u53e5\u8bdd
 remember = section.get(\"remember\", \"\")
 if remember:
 lines.append('<h2>\ud83d\udccc \u672c\u7ae0\u6700\u8be5\u8bb0\u4f4f\u7684\u4e00\u53e5\u8bdd</h2>')
 lines.append(f'<blockquote>{escape_xml(remember)}</blockquote>')

 # \u9762\u8bd5\u51c6\u5907
 qa_list = section.get(\"interview_qa\", [])
 if qa_list:
 lines.append('<h2>\ud83d\udcac \u9762\u8bd5\u51c6\u5907</h2>')
 qa_text = \"\"
 for qa in qa_list:
 qa_text += f'Q: {escape_xml(qa.get(\"q\", \"\"))}<br/>A: {escape_xml(qa.get(\"a\", \"\"))}<br/><br/>'
 lines.append(f'<callout emoji=\"\ud83d\udcac\" background-color=\"blue\"><b>\u9762\u8bd5\u5b98\u53ef\u80fd\u8fd9\u4e48\u95ee\uff1a</b><br/>{qa_text}</callout>')

 # \u5206\u5272\u7ebf
 lines.append('<hr/>')

 return \"\n\".join(lines)


def render_download_links(data: dict) -> str:
 \"\"\"\u6e32\u67d3\u4e0b\u8f7d\u94fe\u63a5\"\"\"
 lines = ['<h1>\ud83d\udcce \u4e0b\u8f7d\u94fe\u63a5</h1>']

 arxiv_id = data.get(\"arxiv_id\", \"\")
 github_url = data.get(\"github_url\", \"\")
 source_url = data.get(\"source_url\", \"\")

 if arxiv_id:
 parts = [f'\ud83d\udcc4 <a href=\"https://arxiv.org/pdf/{arxiv_id}\">PDF \u5168\u6587</a>',
 f'\ud83d\udccb <a href=\"https://arxiv.org/abs/{arxiv_id}\">arXiv \u9875\u9762</a>']
 if github_url:
 parts.append(f'\ud83d\udcbb <a href=\"{escape_xml(github_url)}\">GitHub \u4ee3\u7801</a>')
 lines.append(f'<p>{\" | \".join(parts)}</p>')
 elif source_url:
 parts = [f'\ud83d\udcc4 <a href=\"{escape_xml(source_url)}\">\u539f\u6587</a>']
 if github_url:
 parts.append(f'\ud83d\udcbb <a href=\"{escape_xml(github_url)}\">\u76f8\u5173\u4ee3\u7801</a>')
 lines.append(f'<p>{\" | \".join(parts)}</p>')

 return \"\n\".join(lines)


def render_document(data: dict) -> str:
 \"\"\"\u6e32\u67d3\u5b8c\u6574\u98de\u4e66\u6587\u6863 XML\"\"\"
 date = data.get(\"date\", datetime.now().strftime(\"%Y-%m-%d\"))
 title = data.get(\"title\", \"\u672a\u547d\u540d\u8bba\u6587\")
 authors = data.get(\"authors\", \"\")
 source_url = data.get(\"source_url\", \"\")
 one_liner = data.get(\"one_liner\", \"\")
 sections = data.get(\"sections\", [])

 lines = []

 # \u6807\u9898
 doc_title = f\"{date}_{title}\"
 lines.append(f'<title>{escape_xml(doc_title)}</title>')

 # \u4e00\u53e5\u8bdd\u7406\u89e3 callout
 if one_liner:
 lines.append(f'<callout emoji=\"\ud83d\udca1\" background-color=\"orange\"><b>\u4e00\u53e5\u8bdd\u7406\u89e3</b>\uff1a{escape_xml(one_liner)}</callout>')

 # \u6765\u6e90\u4fe1\u606f
 source_parts = []
 if source_url:
 source_parts.append(f'\u6765\u6e90\uff1a<a href=\"{escape_xml(source_url)}\">{escape_xml(source_url)}</a>')
 if authors:
 source_parts.append(f'\u4f5c\u8005\uff1a{escape_xml(authors)}')
 if source_parts:
 lines.append(f'<p><i>{\" | \".join(source_parts)}</i></p>')

 lines.append('<hr/>')

 # \u5404\u7ae0\u8282
 for i, section in enumerate(sections, 1):
 lines.append(render_section(section, i))

 # \u4e0b\u8f7d\u94fe\u63a5
 lines.append(render_download_links(data))

 return \"\n\".join(lines)


def main():
 parser = argparse.ArgumentParser(description='\u98de\u4e66\u6587\u6863\u6e32\u67d3\u5668 \u2014 \u8bba\u6587\u5185\u5bb9 \u2192 DocxXML')
 parser.add_argument('--input', '-i', help='JSON \u8f93\u5165\u6587\u4ef6\uff08\u4e0d\u4f20\u5219\u4ece stdin \u8bfb\u53d6\uff09')
 parser.add_argument('--output', '-o', help='\u8f93\u51fa\u6587\u4ef6\uff08\u4e0d\u4f20\u5219\u8f93\u51fa\u5230 stdout\uff09')
 parser.add_argument('--validate', action='store_true', help='\u4ec5\u6821\u9a8c JSON \u683c\u5f0f')
 args = parser.parse_args()

 # \u8bfb\u53d6\u8f93\u5165
 if args.input:
 with open(args.input, 'r', encoding='utf-8') as f:
 data = json.load(f)
 else:
 data = json.load(sys.stdin)

 # \u6821\u9a8c
 if args.validate:
 required = [\"title\"]
 missing = [k for k in required if k not in data]
 if missing:
 print(f\"\u274c \u7f3a\u5c11\u5fc5\u586b\u5b57\u6bb5: {missing}\", file=sys.stderr)
 sys.exit(1)
 print(\"\u2705 JSON \u683c\u5f0f\u6821\u9a8c\u901a\u8fc7\")
 sys.exit(0)

 # \u6e32\u67d3
 xml_content = render_document(data)

 # \u8f93\u51fa
 if args.output:
 Path(args.output).write_text(xml_content, encoding='utf-8')
 print(f\"\u2705 \u5df2\u8f93\u51fa\u5230 {args.output} ({len(xml_content)} bytes)\", file=sys.stderr)
 else:
 print(xml_content)


if __name__ == '__main__':
 main()
"
