#!/usr/bin/env python3
"""
AI Research Watch - RSS 抓取器
解析 OpenAI RSS feed，提取最新文章
"""
import json
import sys
import re
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.error import URLError
from datetime import datetime

RSS_URLS = [
    "https://openai.com/news/rss.xml",
]

def fetch_rss(url, timeout=30, retries=2):
    """抓取并解析 RSS feed（带重试）"""
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "AI-Research-Watch/1.0"})
            with urlopen(req, timeout=timeout) as resp:
                xml_data = resp.read().decode("utf-8")
            return parse_rss(xml_data)
        except Exception as e:
            if attempt < retries:
                import time
                time.sleep(2 * (attempt + 1))
                continue
            return {"error": str(e), "items": []}

def parse_rss(xml_data):
    """解析 RSS XML"""
    items = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            desc = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            category = item.findtext("category", "").strip()

            if title and link:
                items.append({
                    "title": title,
                    "url": link,
                    "description": desc,
                    "pub_date": pub_date,
                    "category": category
                })
    except ET.ParseError as e:
        return {"error": f"XML parse error: {e}", "items": []}

    return {"items": items}

def main():
    """命令行入口：接收 URL 列表，输出文章 JSON"""
    urls = sys.argv[1:] if len(sys.argv) > 1 else RSS_URLS

    all_items = []
    for url in urls:
        result = fetch_rss(url)
        if "error" in result:
            print(f"⚠️ Error fetching {url}: {result['error']}", file=sys.stderr)
        for item in result.get("items", []):
            item["source_url"] = url
            item["source"] = "OpenAI"
            all_items.append(item)

    print(json.dumps(all_items, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
