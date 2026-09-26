"""可选：调用 OpenAI 兼容接口生成今日要闻综述。"""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def latest_news_file() -> Path | None:
    files = sorted(DATA_DIR.glob("news_*.json"), reverse=True)
    return files[0] if files else None


def main() -> int:
    if not config.AI_API_KEY:
        print("未配置 AI_API_KEY，跳过 AI 综述。")
        return 0
    news_file = latest_news_file()
    if not news_file:
        print("没有新闻数据，跳过 AI 综述。")
        return 0

    payload = json.loads(news_file.read_text(encoding="utf-8"))
    lines = [f"- [{item['category']}] {item['title']}（{item['source']}）" for item in payload["items"][:30]]
    prompt = (
        "你是一名严谨的中文新闻编辑。请根据下面的标题写一份 350-500 字的今日要闻综述，"
        "分为“今日焦点”“趋势观察”“值得留意”三个小节。不得编造标题之外的事实，"
        "不得使用 Markdown 表格。\n\n" + "\n".join(lines)
    )
    body = json.dumps(
        {
            "model": config.AI_MODEL,
            "messages": [
                {"role": "system", "content": "输出简体中文，保持客观、简洁、信息密度高。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{config.AI_API_BASE}/chat/completions",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {config.AI_API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        result = json.load(response)
    content = result["choices"][0]["message"]["content"].strip()
    output = DATA_DIR / f"summary_{payload.get('date', date.today().isoformat())}.md"
    output.write_text(content + "\n", encoding="utf-8")
    print(f"AI 综述已保存：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

