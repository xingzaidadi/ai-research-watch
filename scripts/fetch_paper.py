#!/usr/bin/env python3
"""
AI Research Watch - 论文抓取器
三路 fallback 从 arXiv 下载论文全文

策略优先级：
  1. arXiv HTML（experimental）→ 可读全文文本
  2. arXiv LaTeX 源码 → 含公式/代码的完整内容
  3. arXiv PDF → 最后兜底

用法：
  python3 fetch_paper.py <arxiv_id_or_url> [--output-dir DIR]

示例：
  python3 fetch_paper.py 2606.31174
  python3 fetch_paper.py https://arxiv.org/abs/2606.30850
"""

import argparse
import json
import os
import re
import sys
import tarfile
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def extract_arxiv_id(input_str: str) -> str:
    """从 URL 或纯 ID 中提取 arXiv ID"""
    m = re.search(r'(\d{4}\.\d{4,5})(v\d+)?', input_str)
    if m:
        return m.group(1)
    m = re.search(r'arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})', input_str)
    if m:
        return m.group(1)
    m = re.search(r'arxiv\.org/e-print/(\d{4}\.\d{4,5})', input_str)
    if m:
        return m.group(1)
    return input_str.strip()


def fetch_url(url: str, timeout: int = 60) -> bytes | None:
    req = Request(url, headers={'User-Agent': 'PaperFetcher/1.0 (academic research)'})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (URLError, HTTPError, TimeoutError) as e:
        print(f"  ✗ {url} → {e}", file=sys.stderr)
        return None


def fetch_text(url: str, timeout: int = 60) -> str | None:
    data = fetch_url(url, timeout)
    if data is None:
        return None
    try:
        return data.decode('utf-8', errors='replace')
    except Exception:
        return None


def save_file(path: Path, content: bytes | str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.encode('utf-8')
    path.write_bytes(content)


def extract_latex_text(source_dir: Path) -> str:
    """从 LaTeX 源码目录提取纯文本（去掉命令，保留内容）"""
    texts = []
    for tex_file in sorted(source_dir.glob('*.tex')):
        try:
            content = tex_file.read_text(encoding='utf-8', errors='replace')
            content = re.sub(r'(?m)^%.*$', '', content)
            content = re.sub(r'\\(?:begin|end)\{[^}]*\}', '', content)
            content = re.sub(r'\\(?:cite|ref|label|input|include)\{[^}]*\}', '', content)
            content = re.sub(r'\\footnote\{[^}]*\}', '', content)
            content = re.sub(r'\\[a-zA-Z]+\*?(\[[^\]]*\])?\{([^}]*)\}', r'\2', content)
            content = re.sub(r'\\[a-zA-Z]+', '', content)
            content = re.sub(r'\$[^$]*\$', '', content)
            content = re.sub(r'\n{3,}', '\n\n', content)
            texts.append(f"=== {tex_file.name} ===\n{content.strip()}")
        except Exception as e:
            print(f"  ⚠ 无法解析 {tex_file.name}: {e}", file=sys.stderr)
    return '\n\n'.join(texts)


def fetch_arxiv_html(arxiv_id: str, out_dir: Path) -> dict | None:
    """策略1：arXiv HTML（experimental）"""
    print(f"[1/3] 尝试 arXiv HTML...")
    for suffix in ['v1', '']:
        url = f"https://arxiv.org/html/{arxiv_id}{suffix}"
        text = fetch_text(url, timeout=30)
        if text and len(text) > 1000 and 'No HTML' not in text[:500]:
            save_file(out_dir / f"{arxiv_id}.html.txt", text)
            print(f"  ✓ HTML 获取成功 ({len(text)//1024}KB)")
            return {"strategy": "html", "path": str(out_dir / f"{arxiv_id}.html.txt"), "size": len(text)}
    print(f"  ✗ HTML 不可用")
    return None


def fetch_arxiv_source(arxiv_id: str, out_dir: Path) -> dict | None:
    """策略2：arXiv LaTeX 源码"""
    print(f"[2/3] 尝试 arXiv LaTeX 源码...")
    url = f"https://arxiv.org/e-print/{arxiv_id}"
    data = fetch_url(url, timeout=60)
    if data is None:
        print(f"  ✗ 源码下载失败")
        return None

    src_path = out_dir / f"{arxiv_id}-source.tar.gz"
    save_file(src_path, data)
    print(f"  ✓ 源码下载成功 ({len(data)//1024}KB)")

    extract_dir = out_dir / f"{arxiv_id}-src"
    try:
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path) as tf:
                tf.extractall(extract_dir)
            print(f"  ✓ 解压到 {extract_dir}")
        else:
            extract_dir.mkdir(parents=True, exist_ok=True)
            (extract_dir / f"{arxiv_id}.tex").write_bytes(data)
            print(f"  ✓ 单文件保存")
    except Exception as e:
        print(f"  ⚠ 解压失败: {e}", file=sys.stderr)
        extract_dir.mkdir(parents=True, exist_ok=True)
        (extract_dir / f"{arxiv_id}.tex").write_bytes(data)

    text = extract_latex_text(extract_dir)
    if text:
        txt_path = out_dir / f"{arxiv_id}.latex.txt"
        save_file(txt_path, text)
        print(f"  ✓ LaTeX 文本提取完成 ({len(text)//1024}KB)")

    return {
        "strategy": "latex",
        "source_path": str(src_path),
        "extract_dir": str(extract_dir),
        "text": text
    }


def fetch_arxiv_pdf(arxiv_id: str, out_dir: Path) -> dict | None:
    """策略3：arXiv PDF"""
    print(f"[3/3] 下载 arXiv PDF...")
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    data = fetch_url(url, timeout=120)
    if data is None:
        print(f"  ✗ PDF 下载失败")
        return None
    pdf_path = out_dir / f"{arxiv_id}.pdf"
    save_file(pdf_path, data)
    print(f"  ✓ PDF 保存成功 ({len(data)//1024}KB)")
    return {"strategy": "pdf", "path": str(pdf_path), "size": len(data)}


def fetch_metadata(arxiv_id: str) -> dict | None:
    """通过 arXiv API 获取元数据"""
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    text = fetch_text(url, timeout=15)
    if not text:
        return None
    meta = {}
    m = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
    if m:
        raw = m.group(1).strip().replace('\n', ' ')
        # arXiv API 返回的 title 前面有 "arXiv:xxxx.xxxxx" 前缀，去掉
        raw = re.sub(r'^arXiv:\d+\.\d+\s*', '', raw)
        meta['title'] = raw
    m = re.search(r'<summary>(.*?)</summary>', text, re.DOTALL)
    if m:
        meta['abstract'] = m.group(1).strip().replace('\n', ' ')[:800]
    authors = re.findall(r'<name>(.*?)</name>', text)
    if authors:
        meta['authors'] = authors
    cats = re.findall(r'<category[^>]*term="([^"]*)"', text)
    if cats:
        meta['categories'] = cats
    published = re.search(r'<published>(.*?)</published>', text)
    if published:
        meta['published'] = published.group(1)[:10]
    return meta if meta else None


def main():
    parser = argparse.ArgumentParser(description='论文抓取器 — 三路 fallback')
    parser.add_argument('paper', help='arXiv ID 或 URL')
    parser.add_argument('--output-dir', '-o', default=None, help='输出目录')
    parser.add_argument('--skip-pdf', action='store_true', help='跳过 PDF 下载')
    args = parser.parse_args()

    arxiv_id = extract_arxiv_id(args.paper)
    out_dir = Path(args.output_dir) if args.output_dir else Path('/tmp/papers')
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📄 论文抓取: {arxiv_id}")
    print(f"📁 输出目录: {out_dir}\n")

    results = {"arxiv_id": arxiv_id, "strategies": {}}

    # 获取元数据
    print("📋 获取元数据...")
    meta = fetch_metadata(arxiv_id)
    if meta:
        results["metadata"] = meta
        print(f"  ✓ {meta.get('title', 'N/A')}")
        print(f"    作者: {', '.join(meta.get('authors', [])[:5])}")
    print()

    # 策略1: HTML
    r = fetch_arxiv_html(arxiv_id, out_dir)
    if r:
        results["strategies"]["html"] = r
    print()

    # 策略2: LaTeX 源码
    r = fetch_arxiv_source(arxiv_id, out_dir)
    if r:
        results["strategies"]["latex"] = r
    print()

    # 策略3: PDF
    if not args.skip_pdf:
        r = fetch_arxiv_pdf(arxiv_id, out_dir)
        if r:
            results["strategies"]["pdf"] = r
        print()

    # 汇总
    strategies = list(results["strategies"].keys())
    if strategies:
        best = strategies[0]
        results["best_strategy"] = best
        print(f"✅ 成功！最佳策略: {best}, 已获取 {len(strategies)} 种格式")
    else:
        results["best_strategy"] = "failed"
        print("❌ 所有策略均失败")

    # 保存结果 JSON
    result_path = out_dir / f"{arxiv_id}.result.json"
    with open(result_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📊 结果: {result_path}")
    # 输出 JSON 供调用方解析
    print("===RESULT_JSON===")
    print(json.dumps(results, ensure_ascii=False))
    print("===END===")


if __name__ == '__main__':
    main()
