"""将 data 中的每日数据构建成可直接部署的静态站点。"""

from __future__ import annotations

import html
import json
import shutil
from datetime import datetime
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"

CSS = r"""
:root{--bg:#f4f6f8;--card:#fff;--ink:#17202a;--muted:#667085;--line:#e7eaf0;--accent:#ff5a36;--tech:#4f46e5;--hot:#d92d20}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}a{color:inherit}.hero{background:#111827;color:#fff;padding:54px 22px 48px}.hero-inner,.container{max-width:1120px;margin:auto}.eyebrow{color:#fda68a;font-size:12px;font-weight:800;letter-spacing:.18em}.hero h1{margin:10px 0 4px;font-size:clamp(34px,6vw,64px);line-height:1.05;letter-spacing:-.04em}.hero p{margin:12px 0 0;color:#cbd5e1;font-size:17px}.nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:28px}.nav a{border:1px solid #475569;border-radius:999px;padding:7px 14px;text-decoration:none;color:#e2e8f0}.container{padding:30px 22px 60px}.meta{display:flex;justify-content:space-between;gap:16px;align-items:end;margin-bottom:22px}.meta h2{margin:0;font-size:26px}.meta small{color:var(--muted)}.digest{background:linear-gradient(135deg,#fff4ef,#fff);border:1px solid #ffd8ca;border-radius:20px;padding:22px 24px;margin:0 0 26px}.digest h2{margin:0 0 8px}.digest p{margin:.5em 0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;display:flex;flex-direction:column;min-height:230px;box-shadow:0 1px 2px #10182808}.card:hover{transform:translateY(-2px);box-shadow:0 12px 28px #10182814;transition:.2s}.top{display:flex;justify-content:space-between;gap:10px;color:var(--muted);font-size:12px}.tag{font-weight:700;color:var(--tech)}.tag.hot{color:var(--hot)}.card h3{font-size:20px;line-height:1.4;margin:14px 0 10px}.card p{color:#475467;margin:0 0 16px}.card .open{margin-top:auto;color:var(--accent);font-weight:700;text-decoration:none}.footer{border-top:1px solid var(--line);padding:28px 22px;text-align:center;color:var(--muted)}.archive{display:flex;flex-wrap:wrap;gap:10px}.archive a{background:#fff;border:1px solid var(--line);border-radius:12px;padding:9px 13px;text-decoration:none}@media(max-width:720px){.hero{padding-top:38px}.grid{grid-template-columns:1fr}.meta{align-items:start;flex-direction:column}.card{min-height:0}}
"""


def md_to_html(text: str) -> str:
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h3>{html.escape(line[3:])}</h3>")
        elif line.startswith("# "):
            out.append(f"<h3>{html.escape(line[2:])}</h3>")
        elif line.startswith("- "):
            out.append(f"<p>• {html.escape(line[2:])}</p>")
        else:
            out.append(f"<p>{html.escape(line)}</p>")
    return "\n".join(out)


def render_day(payload: dict, summary: str = "") -> str:
    date_value = payload["date"]
    cards = []
    for item in payload["items"]:
        category = html.escape(item["category"])
        hot = " hot" if category == "综合热点" else ""
        cards.append(
            f'''<article class="card" data-news-id="{html.escape(item['id'])}" data-news-url="{html.escape(item['url'], quote=True)}" data-news-source="{html.escape(item['source'], quote=True)}" data-news-time="{html.escape(item['published_at'], quote=True)}" data-news-title="{html.escape(item['title'], quote=True)}" data-news-summary="{html.escape(item['summary'], quote=True)}">
<div class="top"><span class="tag{hot}">{category}</span><span>{html.escape(item['source'])}</span></div>
<h3>{html.escape(item['title'])}</h3><p>{html.escape(item['summary'])}</p>
<a class="open" href="{html.escape(item['url'], quote=True)}" target="_blank" rel="noopener noreferrer">查看原文 →</a></article>'''
        )
    digest = f'<section class="digest"><h2>今日要闻综述</h2>{md_to_html(summary)}</section>' if summary else ""
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="每天自动更新的科技互联网与综合热点新闻摘要"><title>{config.SITE_TITLE} · {date_value}</title><link rel="stylesheet" href="styles.css"></head><body>
<header class="hero"><div class="hero-inner"><div class="eyebrow">DAILY SIGNAL</div><h1>{config.SITE_TITLE}</h1><p>{config.SITE_SUBTITLE} · 每天 08:00 自动更新</p><nav class="nav"><a href="index.html">今日</a><a href="archive.html">往期存档</a><a href="https://github.com/dawanglin/news-daily">GitHub</a></nav></div></header>
<main class="container"><div class="meta"><h2>{date_value}</h2><small>收录 {payload['count']} 条 · 更新时间 {html.escape(payload['generated_at'][:19].replace('T',' '))}</small></div>{digest}<section class="grid">{''.join(cards)}</section></main>
<footer class="footer">信息来自公开 RSS，版权归原作者与来源媒体所有。</footer></body></html>'''


def archive_page(dates: list[str]) -> str:
    links = "".join(f'<a href="{d}.html">{d}</a>' for d in dates)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>往期存档 · {config.SITE_TITLE}</title><link rel="stylesheet" href="styles.css"></head><body><header class="hero"><div class="hero-inner"><div class="eyebrow">ARCHIVE</div><h1>往期存档</h1><p>按日期回看每日新闻</p><nav class="nav"><a href="index.html">返回今日</a></nav></div></header><main class="container"><div class="archive">{links or '<p>暂无存档</p>'}</div></main></body></html>'''


def main() -> int:
    files = sorted(DATA_DIR.glob("news_*.json"), reverse=True)
    if not files:
        raise SystemExit("没有 data/news_*.json，请先运行 fetch_news.py")
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "styles.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    dates = []
    for news_file in files:
        payload = json.loads(news_file.read_text(encoding="utf-8"))
        day = payload["date"]
        dates.append(day)
        summary_file = DATA_DIR / f"summary_{day}.md"
        summary = summary_file.read_text(encoding="utf-8") if summary_file.exists() else ""
        page = render_day(payload, summary)
        (SITE_DIR / f"{day}.html").write_text(page, encoding="utf-8")
    shutil.copyfile(SITE_DIR / f"{dates[0]}.html", SITE_DIR / "index.html")
    (SITE_DIR / "archive.html").write_text(archive_page(dates), encoding="utf-8")
    (SITE_DIR / ".nojekyll").touch()
    print(f"站点已生成：{SITE_DIR / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

