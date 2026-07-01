#!/usr/bin/env python3
"""
AI Research Watch - 文章评分器
基于 sources.yml 和 eval_keywords.yml 的确定性评分
"""
import json
import sys
import re
from pathlib import Path

REFS_DIR = Path(__file__).parent.parent / "references"

def load_keywords():
    """加载关键词评分配置（简化版，直接内嵌）"""
    return {
        "high": {  # +3
            "eval", "evaluation", "benchmark", "system card", "safety report",
            "capability assessment", "model evaluation"
        },
        "medium": {  # +2
            "agent", "reasoning", "alignment", "safety", "chain of thought",
            "tool use", "function calling", "multi-agent", "planning", "reflection"
        },
        "low": {  # +1
            "swe-bench", "humaneval", "mmlu", "math", "gsm8k", "agentbench",
            "webarena", "τ-bench", "pass@k", "red teaming", "adversarial",
            "robustness", "hallucination", "grounding"
        }
    }

def score_article(title, description, url, source_name):
    """
    确定性评分：基于规则，不依赖 LLM
    返回 (score, reasons)
    """
    score = 0
    reasons = []

    # === 正分：来源类型 ===
    title_lower = (title + " " + description).lower()

    # 官方研究 / Publication (+5)
    research_signals = ["research", "paper", "study", "arxiv", "publication"]
    if any(s in url.lower() for s in ["/research/", "/papers/", "arxiv.org"]):
        score += 5
        reasons.append("官方Research/论文 (+5)")
    elif any(s in title_lower for s in research_signals):
        score += 5
        reasons.append("研究类内容 (+5)")

    # Benchmark / System Card / Eval (+4)
    bench_signals = ["benchmark", "system card", "eval", "evaluation", "assessment"]
    if any(s in title_lower for s in bench_signals):
        score += 4
        reasons.append("Benchmark/Eval/System Card (+4)")

    # Agent / Reasoning / Alignment / Safety (+3)
    agent_signals = ["agent", "reasoning", "alignment", "safety", "chain of thought",
                     "tool use", "planning", "reflection", "autonomy"]
    if any(s in title_lower for s in agent_signals):
        score += 3
        reasons.append("Agent/Reasoning/Safety (+3)")

    # 模型发布 / 技术说明 (+2)
    model_signals = ["introducing", "release", "launch", "new model", "gpt-", "claude", "o3", "o4"]
    if any(s in title_lower for s in model_signals):
        score += 2
        reasons.append("模型发布/技术说明 (+2)")

    # === 正分：关键词匹配 ===
    keywords = load_keywords()
    for kw in keywords["high"]:
        if kw.lower() in title_lower:
            score += 3
            reasons.append(f"关键词匹配 [{kw}] (+3)")
    for kw in keywords["medium"]:
        if kw.lower() in title_lower:
            score += 2
            reasons.append(f"关键词匹配 [{kw}] (+2)")
    for kw in keywords["low"]:
        if kw.lower() in title_lower:
            score += 1
            reasons.append(f"关键词匹配 [{kw}] (+1)")

    # === 负分：噪音过滤 ===
    # 纯营销 / 招聘 / 合作新闻稿 (-3)
    spam_signals = ["hiring", "job opening", "career", "partnership announcement",
                    "press release", "we're hiring", "join our team"]
    if any(s in title_lower for s in spam_signals):
        score -= 3
        reasons.append("营销/招聘/合作 (-3)")

    # 非官方二手转述 (-5)
    secondary_signals = ["says", "according to", "reportedly", "analysis of",
                         "reaction to", "what we learned from"]
    if any(s in title_lower for s in secondary_signals):
        # 但如果来自官方源则不扣分
        official_domains = ["openai.com", "anthropic.com", "arxiv.org", "huggingface.co"]
        if not any(d in url.lower() for d in official_domains):
            score -= 5
            reasons.append("二手转述 (-5)")

    # 非技术内容 (-2)
    non_tech = ["office", "expansion", "funding", "valuation", "ipo", "hire"]
    if any(s in title_lower for s in non_tech):
        score -= 2
        reasons.append("非技术内容 (-2)")

    return score, reasons

def classify_article(title, description):
    """分类文章类型"""
    text = (title + " " + description).lower()
    if any(s in text for s in ["benchmark", "eval", "system card"]):
        return "Benchmark/Eval"
    if any(s in text for s in ["research", "paper", "study"]):
        return "Research"
    if any(s in text for s in ["safety", "alignment", "red team"]):
        return "Safety"
    if any(s in text for s in ["model", "release", "introducing", "gpt", "claude"]):
        return "Model Release"
    if any(s in text for s in ["agent", "tool", "orchestrat"]):
        return "Agent"
    if any(s in text for s in ["engineering", "infrastructure", "system"]):
        return "Engineering"
    return "Other"

def main():
    """命令行入口：接收 JSON 输入，输出评分结果"""
    if len(sys.argv) > 1:
        # 从文件读取
        with open(sys.argv[1]) as f:
            articles = json.load(f)
    else:
        # 从 stdin 读取
        articles = json.load(sys.stdin)

    results = []
    for art in articles:
        score, reasons = score_article(
            art.get("title", ""),
            art.get("description", ""),
            art.get("url", ""),
            art.get("source", "")
        )
        results.append({
            "title": art.get("title", ""),
            "url": art.get("url", ""),
            "source": art.get("source", ""),
            "score": score,
            "reasons": reasons,
            "type": classify_article(art.get("title", ""), art.get("description", "")),
            "description": art.get("description", "")
        })

    # 按分数排序
    results.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
