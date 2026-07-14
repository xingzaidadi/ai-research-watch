#!/usr/bin/env python3
"""飞书 DocxXML → Markdown 转换器"""
import re, sys, os

def xml_to_md(xml_content):
    """将飞书 DocxXML 转为 Markdown"""
    text = xml_content
    
    # 提取 title
    title_m = re.search(r'<title>(.*?)</title>', text)
    title = title_m.group(1) if title_m else "untitled"
    
    # 基本标签转换
    text = re.sub(r'<h1>(.*?)</h1>', r'\n# \1\n', text)
    text = re.sub(r'<h2>(.*?)</h2>', r'\n## \1\n', text)
    text = re.sub(r'<h3>(.*?)</h3>', r'\n### \1\n', text)
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text)
    text = re.sub(r'<i>(.*?)</i>', r'*\1*', text)
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text)
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text)
    text = re.sub(r'<a href="(.*?)">(.*?)</a>', r'[\2](\1)', text)
    text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<hr\s*/?>', '\n---\n', text)
    
    # callout → blockquote
    text = re.sub(r'<callout[^>]*>(.*?)</callout>', lambda m: '\n> ' + m.group(1).replace('\n', '\n> ').replace('<br/>', '\n> ').replace('<p>', '').replace('</p>', '') + '\n', text, flags=re.DOTALL)
    
    # blockquote
    text = re.sub(r'<blockquote>(.*?)</blockquote>', lambda m: '\n> ' + m.group(1).replace('\n', '\n> ').replace('<p>', '').replace('</p>', '') + '\n', text, flags=re.DOTALL)
    
    # 表格转 Markdown
    def convert_table(match):
        table_html = match.group(0)
        rows = re.findall(r'<tr>(.*?)</tr>', table_html, re.DOTALL)
        if not rows:
            return table_html
        md_rows = []
        for i, row in enumerate(rows):
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            md_rows.append('| ' + ' | '.join(cells) + ' |')
            if i == 0:
                md_rows.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')
        return '\n' + '\n'.join(md_rows) + '\n'
    
    text = re.sub(r'<table>.*?</table>', convert_table, text, flags=re.DOTALL)
    
    # 清理剩余 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    # 添加标题
    text = f'# {title}\n\n{text}'
    
    return text

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python3 convert_xml_to_md.py input.xml output.md")
        sys.exit(1)
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        xml = f.read()
    
    md = xml_to_md(xml)
    
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write(md)
    
    print(f"✅ 转换完成: {sys.argv[2]} ({len(md)} chars)")
