# -*- coding: utf-8 -*-
"""
AI 总结（可选）：读取最新 data/news_*.json，调用 OpenAI 兼容接口生成每日综述。

- 未配置 AI_API_KEY  -> 直接跳过，不影响构建（此时页面使用抽取式摘要）。
- 配置了但调用失败  -> 打印错误并跳过，不中断流水线。
- 产物              -> data/summary_YYYY-MM-DD.md

用法：python summarize.py
"""
import sys
import os
import json
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import AI_API_KEY, AI_API_BASE, AI_MODEL

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def get_latest_news():
    files = sorted(DATA_DIR.glob("news_*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def build_prompt(news):
    lines = []
    for it in news["items"][:30]:
        lines.append(f"- [{it['category']}] {it['title']}（{it['source']}）\n  摘要：{it['summary'][:120]}")
    body = "\n".join(lines)
    return (
        "你是资深中文新闻编辑。请根据下面抓取的新闻，写一份《今日要闻综述》：\n"
        "1. 先写 2-3 句总体概览；\n"
        "2. 按「科技」「综合」分类，每类下列出最重要的 3-6 条，每条一句话，含来源；\n"
        "3. 用 Markdown 格式（## 作为分类标题，- 作为条目）；\n"
        "4. 控制在 600 字以内，直接输出正文，不要寒暄。\n\n"
        f"新闻日期：{news['date']}\n\n"
        f"原始新闻：\n{body}"
    )


def call_ai(key, base, model, prompt):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一名严谨、简洁的中文新闻编辑。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1200,
    }
    url = base.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def main():
    news = get_latest_news()
    if not news or not news.get("items"):
        print("没有可总结的新闻数据，跳过 AI 总结。")
        return

    key = os.environ.get("AI_API_KEY") or AI_API_KEY
    base = os.environ.get("AI_API_BASE") or AI_API_BASE
    model = os.environ.get("AI_MODEL") or AI_MODEL

    if not key:
        print("AI_API_KEY 未配置，跳过 AI 总结（页面将使用抽取式摘要）。")
        return

    try:
        content = call_ai(key, base, model, build_prompt(news))
    except Exception as exc:
        print(f"[警告] AI 总结调用失败，跳过：{exc}")
        return

    out = DATA_DIR / f"summary_{news['date']}.md"
    out.write_text(content.strip(), encoding="utf-8")
    print(f"AI 总结完成，已保存 -> {out}")


if __name__ == "__main__":
    main()
