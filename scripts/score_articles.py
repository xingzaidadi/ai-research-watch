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

def score_article(title, description, url, source_name, pub_date=None):
    """
    确定性评分：基于规则，不依赖 LLM
    返回 (score, reasons)
    pub_date: 发布日期字符串（用于时效性加权）
    """
    score = 0
    reasons = []

    # === 时效性加权（最重要！） ===
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    if pub_date:
        try:
            # 清理日期字符串（去掉时区后缀如 GMT/UTC）
            import re
            clean_date = re.sub(r'\s+(GMT|UTC|[+-]\d{4})$', '', pub_date.strip())
            # 尝试解析多种日期格式
            for fmt in ["%a, %d %b %Y %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    pub_dt = datetime.strptime(clean_date[:len(fmt)+5], fmt)
                    break
                except ValueError:
                    continue
            else:
                pub_dt = None

            if pub_dt:
                age_days = (now - pub_dt).days
                if age_days <= 1:
                    score += 10
                    reasons.append(f"🔥 今日发布 ({age_days}天前) (+10)")
                elif age_days <= 3:
                    score += 8
                    reasons.append(f"⚡ 近3天 ({age_days}天前) (+8)")
                elif age_days <= 7:
                    score += 5
                    reasons.append(f"📅 本周 ({age_days}天前) (+5)")
                elif age_days <= 30:
                    score += 2
                    reasons.append(f"📆 近期 ({age_days}天前) (+2)")
                else:
                    score -= 10
                    reasons.append(f"⏰ 超过30天 ({age_days}天前) (-10)")
        except Exception:
            pass

    # === 正分：来源类型 ===
    title_lower = (title + " " + description).lower()

    # 模型发布 / 重大产品更新 (+6) — 提升权重！
    model_signals = ["introducing", "release", "launch", "new model", "gpt-", "claude", "o3", "o4"]
    if any(s in title_lower for s in model_signals):
        score += 6
        reasons.append("模型发布/重大更新 (+6)")

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
            art.get("source", ""),
            art.get("pub_date", "")
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

    # 硬性时间窗口：超过 MAX_AGE_DAYS 天的直接过滤
    MAX_AGE_DAYS = 14
    filtered = []
    for r in results:
        age_str = [x for x in r["reasons"] if "天前" in x]
        if age_str:
            import re
            m = re.search(r'(\d+)天前', age_str[0])
            if m and int(m.group(1)) > MAX_AGE_DAYS:
                continue  # 跳过超龄文章
        filtered.append(r)

    print(json.dumps(filtered, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
