#!/usr/bin/env python3
"""
将 Markdown/纯文本文章转换为排版整齐的 PDF
用法: python3 html2pdf.py input.txt output.pdf [--title "文章标题"]

中文字体：使用 PyMuPDF 内置 china-s（宋体），确保中文不出现问号。
"""
import fitz  # PyMuPDF
import re
import sys
import argparse


# 中文字体名（PyMuPDF 内置）
CJK_FONT = "china-s"
CJK_FONT_BOLD = "china-s"


def is_cjk(ch: str) -> bool:
    """检测单个字符是否为 CJK 字符"""
    cp = ord(ch)
    return (
        (0x4E00 <= cp <= 0x9FFF) or
        (0x3400 <= cp <= 0x4DBF) or
        (0x20000 <= cp <= 0x2A6DF) or
        (0x2A700 <= cp <= 0x2B73F) or
        (0x2B740 <= cp <= 0x2B81F) or
        (0xF900 <= cp <= 0xFAFF) or
        (0x2F800 <= cp <= 0x2FA1F) or
        (0x3000 <= cp <= 0x303F) or  # CJK 标点
        (0xFF00 <= cp <= 0xFFEF)     # 全角字符
    )


def has_cjk(text: str) -> bool:
    """检测文本是否包含 CJK 字符"""
    return any(is_cjk(ch) for ch in text)


def get_font(text: str) -> str:
    """根据文本内容选择字体"""
    return CJK_FONT if has_cjk(text) else "helv"


def clean_markdown(text: str) -> str:
    """清理 Markdown 格式"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'!\[.*?\]\([^\)]+\)', '', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def wrap_text(text: str, max_chars: int = 65) -> list:
    """按最大字符数换行，处理中英文混排"""
    lines = []
    current = ""
    for ch in text:
        current += ch
        limit = max_chars // 2 if is_cjk(ch) else max_chars
        if len(current) >= limit and ch in ' ，。、；：！？\n,.:;!?\t':
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines


def render_markdown_to_pdf(input_path: str, output_path: str, title: str = None):
    """将 Markdown 文件渲染为 PDF"""
    with open(input_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    text = clean_markdown(raw)
    doc = fitz.open()

    # --- 封面页 ---
    page = doc.new_page(width=595, height=842)  # A4
    if title:
        title_font = get_font(title)
        title_rect = fitz.Rect(60, 200, 535, 300)
        page.insert_textbox(title_rect, title, fontsize=22, fontname=title_font,
                           align=fitz.TEXT_ALIGN_CENTER, color=(0.1, 0.1, 0.1))
        line_rect = fitz.Rect(60, 310, 535, 312)
        page.draw_rect(line_rect, color=(0.8, 0.8, 0.8), fill=(0.8, 0.8, 0.8))
        source_text = "AI Research Watch · 论文全文"
        source_font = get_font(source_text)
        source_rect = fitz.Rect(60, 330, 535, 380)
        page.insert_textbox(source_rect, source_text, fontsize=11,
                           fontname=source_font, align=fitz.TEXT_ALIGN_CENTER,
                           color=(0.5, 0.5, 0.5))

    # --- 正文页 ---
    lines = text.split('\n')
    page = doc.new_page(width=595, height=842)
    y = 60
    margin_left = 60
    margin_right = 60
    page_width = 595 - margin_left - margin_right

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            y += 8
            if y > 780:
                page = doc.new_page(width=595, height=842)
                y = 60
            continue

        # 标题 (# ## ###)
        if line_stripped.startswith('# ') and not line_stripped.startswith('## '):
            y += 16
            if y > 780:
                page = doc.new_page(width=595, height=842)
                y = 60
            text_content = line_stripped[2:].strip()
            font = get_font(text_content)
            rect = fitz.Rect(margin_left, y, 595 - margin_right, y + 30)
            page.insert_textbox(rect, text_content, fontsize=16, fontname=font,
                               color=(0.1, 0.1, 0.1))
            y += 34
        elif line_stripped.startswith('## '):
            y += 12
            if y > 780:
                page = doc.new_page(width=595, height=842)
                y = 60
            text_content = line_stripped[3:].strip()
            font = get_font(text_content)
            rect = fitz.Rect(margin_left, y, 595 - margin_right, y + 22)
            page.insert_textbox(rect, text_content, fontsize=13, fontname=font,
                               color=(0.2, 0.2, 0.2))
            y += 26
        elif line_stripped.startswith('### '):
            y += 8
            if y > 780:
                page = doc.new_page(width=595, height=842)
                y = 60
            text_content = line_stripped[4:].strip()
            font = get_font(text_content)
            rect = fitz.Rect(margin_left, y, 595 - margin_right, y + 18)
            page.insert_textbox(rect, text_content, fontsize=11, fontname=font,
                               color=(0.3, 0.3, 0.3))
            y += 22
        elif line_stripped.startswith('> '):
            if y > 760:
                page = doc.new_page(width=595, height=842)
                y = 60
            bg_rect = fitz.Rect(margin_left - 5, y - 2, 595 - margin_right, y + 16)
            page.draw_rect(bg_rect, color=(0.92, 0.92, 0.92), fill=(0.92, 0.92, 0.92))
            text_content = line_stripped[2:].strip()
            font = get_font(text_content)
            rect = fitz.Rect(margin_left + 5, y, 595 - margin_right, y + 14)
            page.insert_textbox(rect, text_content, fontsize=9, fontname=font,
                               color=(0.4, 0.4, 0.4))
            y += 20
        elif line_stripped.startswith('- ') or line_stripped.startswith('* '):
            if y > 780:
                page = doc.new_page(width=595, height=842)
                y = 60
            text_content = line_stripped[2:].strip()
            font = get_font(text_content)
            rect = fitz.Rect(margin_left + 10, y, 595 - margin_right, y + 14)
            page.insert_textbox(rect, f"• {text_content}", fontsize=10, fontname=font,
                               color=(0.2, 0.2, 0.2))
            y += 18
        elif line_stripped.startswith('---'):
            y += 6
            if y > 780:
                page = doc.new_page(width=595, height=842)
                y = 60
            line_rect = fitz.Rect(margin_left, y, 595 - margin_right, y + 1)
            page.draw_rect(line_rect, color=(0.8, 0.8, 0.8), fill=(0.8, 0.8, 0.8))
            y += 12
        else:
            if y > 780:
                page = doc.new_page(width=595, height=842)
                y = 60
            font = get_font(line_stripped)
            rect = fitz.Rect(margin_left, y, 595 - margin_right, y + 200)
            try:
                rc = page.insert_textbox(rect, line_stripped, fontsize=10, fontname=font,
                                        color=(0.15, 0.15, 0.15))
                y += max(14, 200 - rc.height if hasattr(rc, 'height') else 14)
            except:
                y += 14

    doc.save(output_path)
    doc.close()
    print(f"✅ PDF 已生成: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Markdown/文本 → PDF（支持中文）')
    parser.add_argument('input', help='输入文件路径')
    parser.add_argument('output', help='输出 PDF 路径')
    parser.add_argument('--title', help='文档标题', default=None)
    args = parser.parse_args()

    render_markdown_to_pdf(args.input, args.output, title=args.title)


if __name__ == '__main__':
    main()
