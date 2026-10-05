# -*- coding: utf-8 -*-
"""把每日数据构建成手机优先、无需 JavaScript 的静态简报。"""

import datetime
import html as html_mod
import json
import sys
from pathlib import Path

from config import NEWS_FEEDS

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SITE_DIR = BASE_DIR / "site"
DAILY_DIR = SITE_DIR / "daily"
ARCHIVE_DIR = SITE_DIR / "archive"
DAILY_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
def esc(value):
    return html_mod.escape(str(value or ""), quote=True)


def clean_output(value):
    """避免模板缩进留下行尾空格，保持生成文件稳定。"""
    return "\n".join(line.rstrip() for line in value.splitlines()) + "\n"


def item_defaults(item):
    item = dict(item)
    item.setdefault("why", "先判断它是否能解决你的实际问题，再决定是否动手尝试。")
    item.setdefault("confidence", "来源报道")
    item.setdefault("confidence_class", "professional")
    item.setdefault("topic", "")
    item.setdefault("lens", "来源报道")
    item.setdefault("signals", [item.get("source", "")])
    item.setdefault("published", "")
    item.setdefault("summary", item.get("title", ""))
    return item


def story_html(item):
    item = item_defaults(item)
    signals = "、".join(dict.fromkeys(filter(None, item.get("signals", []))))
    source_text = signals or item.get("source", "")
    return f'''
      <article class="story" data-news-title="{esc(item['title'])}" data-news-url="{esc(item.get('link'))}" data-news-source="{esc(source_text)}" data-news-time="{esc(item.get('published'))}" data-news-summary="{esc(item['summary'])}">
        <div class="story-body">
          <a class="story-title" href="{esc(item.get('link'))}" target="_blank" rel="noopener noreferrer">{esc(item['title'])}</a>
          <div class="story-meta"><span class="topic">{esc(item.get('topic'))}</span><span class="lens">{esc(item.get('lens'))}</span><span>{esc(source_text)}</span><span>{esc(item.get('published'))}</span><span class="confidence {esc(item['confidence_class'])}">{esc(item['confidence'])}</span></div>
          <p class="story-summary">{esc(item['summary'])}</p>
          <p class="story-why"><strong>落地入口：</strong>{esc(item['why'])}</p>
        </div>
      </article>'''


def build_stream(items):
    stories = "".join(story_html(item) for item in items)
    return f'''<section class="feed"><div class="section-heading"><h2>今日更新</h2><span>{len(items)} 条</span></div>{stories}</section>'''


def source_footer(news):
    stats = news.get("sources", {})
    hot = [name for name, value in stats.items() if value.get("type") == "兴趣线索" and value.get("status") == "成功"]
    media = [name for name, value in stats.items() if value.get("type") != "兴趣线索" and value.get("status", "").startswith("成功")]
    if not hot and not media:
        media = list(NEWS_FEEDS)
    parts = []
    if hot:
        parts.append(f"兴趣发现：{'、'.join(hot)}")
    if media:
        parts.append(f"专业来源：{'、'.join(media)}")
    return "<br>".join(esc(part) for part in parts)


PAGE_TEMPLATE = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#f3f6f2"><meta name="description" content="每天发现能理解、能试用、能落地的新东西"><title>[[TITLE]]</title>
<style>
:root{color-scheme:light;--page:#f3f6f2;--paper:#fbfcfa;--ink:#18211d;--muted:#617068;--line:#d8e0da;--accent:#2f6d57;--accent-soft:#e2eee8;--blue:#315d73;--amber:#9a6226;--signal:#8a5a21;--shadow:0 12px 32px rgba(28,54,42,.07)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--page);color:var(--ink);font-family:"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",system-ui,sans-serif;font-size:16px;line-height:1.72;-webkit-font-smoothing:antialiased}a{color:inherit}.mast{padding:calc(22px + env(safe-area-inset-top)) 20px 23px;border-bottom:1px solid var(--line);background:var(--paper)}.mast-inner,.page,.footer-inner{width:min(100%,720px);margin:auto}.mast-top{display:flex;justify-content:space-between;align-items:center;color:var(--muted);font-size:13px}.mast-top a{min-height:44px;display:inline-flex;align-items:center;color:var(--accent);text-decoration:none}.mast h1{font-size:clamp(28px,8vw,42px);line-height:1.18;letter-spacing:-.035em;margin:15px 0 8px}.mast p{margin:0;color:var(--muted);font-size:14px}.method{display:inline-block;margin-top:12px;padding:4px 9px;background:var(--accent-soft);color:var(--accent);border-radius:6px;font-size:12px}.page{padding:18px 16px 56px}.feed{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:0 16px}.section-heading{display:flex;justify-content:space-between;align-items:center;min-height:60px;border-bottom:1px solid var(--line)}.section-heading h2{margin:0;font-size:20px;letter-spacing:-.015em}.section-heading>span{color:var(--muted);font-size:12px}.story{padding:20px 0;border-bottom:1px solid var(--line)}.story:last-child{border-bottom:0}.story-body{min-width:0}.story-title{display:block;font-size:18px;font-weight:700;line-height:1.48;text-decoration:none;text-wrap:pretty}.story-title:active{color:var(--accent)}.story-title,.story-summary,.story-why{overflow-wrap:anywhere}.story-meta{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin:9px 0;color:var(--muted);font-size:12px}.story-meta .topic,.story-meta .lens{padding:1px 7px;border-radius:5px;background:var(--accent-soft);color:var(--accent)}.story-meta .lens{background:#edf0eb;color:#59665f}.confidence{padding:1px 7px;border-radius:5px}.confidence.verified{background:#dfeee5;color:#276044}.confidence.professional{background:#e5edf1;color:#315d73}.confidence.signal{background:#f4eadb;color:#81541e}.story-summary{margin:7px 0 0;color:#394740;font-size:15px}.story-why{margin:10px 0 0;padding:9px 11px;border-left:3px solid var(--accent);background:var(--accent-soft);color:#35473e;font-size:13px}.story-why strong{color:var(--accent)}footer{border-top:1px solid var(--line);padding:24px 20px calc(30px + env(safe-area-inset-bottom));color:var(--muted);font-size:12px}.footer-note{margin-top:8px}.back{display:inline-flex;min-height:44px;align-items:center;color:var(--accent);text-decoration:none}.archive-panel{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:4px 16px}.archive-panel h2{font-size:21px;margin:16px 0 10px}.archive-intro{color:var(--muted);font-size:13px}.archive-list{list-style:none;padding:0;margin:0}.archive-list li{padding:17px 0;border-top:1px solid var(--line)}.archive-list a{text-decoration:none;font-size:16px;line-height:1.65}.archive-list .issue{display:block;color:var(--accent);font-weight:700}.edition-meta{display:block;color:var(--muted);font-size:12px;margin-top:4px}a:focus-visible{outline:3px solid var(--amber);outline-offset:3px}@media(min-width:760px){.page{padding-left:0;padding-right:0}.feed{padding:0 24px}.story{padding:22px 0}.story-title{font-size:19px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media(prefers-color-scheme:dark){:root{color-scheme:dark;--page:#121815;--paper:#18201c;--ink:#e8eee9;--muted:#a8b4ad;--line:#334039;--accent:#74b798;--accent-soft:#22362c;--blue:#8ab5c8;--amber:#d5a363;--signal:#d5a363;--shadow:none}.mast{background:var(--paper)}.story-meta .lens{background:#2b332f;color:#b8c3bd}.story-summary{color:#c7d1cb}.story-why{color:#c9d8d0}.confidence.verified{background:#244332;color:#9bd3b3}.confidence.professional{background:#263c47;color:#a9c9d6}.confidence.signal{background:#46361f;color:#e0ba82}}
</style></head><body>
<header class="mast"><div class="mast-inner"><div class="mast-top"><span>每日个人情报流</span><a href="[[ARCHIVE_HREF]]">历史目录</a></div><h1>今天，有什么可以拿来用</h1><p>[[DATE]]　[[STATS]]</p><span class="method">兴趣过滤 · 用途提示 · 免费规则整理</span></div></header>
<main class="page">[[STREAM]]</main>
<footer><div class="footer-inner">[[SOURCES]]<div class="footer-note">不使用 AI 大模型。用户评价只作为体验线索；政治外交与泛国际冲突默认排除。</div></div></footer></body></html>'''


def render_daily(news, archive_href):
    date = news["date"]
    parsed = datetime.datetime.strptime(date, "%Y-%m-%d")
    date_cn = f"{parsed.year}年{parsed.month}月{parsed.day}日 {WEEKDAYS[parsed.weekday()]}"
    items = news.get("items", [])
    stream = build_stream(items)
    page = PAGE_TEMPLATE
    replacements = {
        "[[TITLE]]": f"每日个人情报流 - {date}",
        "[[DATE]]": date_cn,
        "[[STATS]]": f"共 {len(items)} 条",
        "[[ARCHIVE_HREF]]": archive_href,
        "[[STREAM]]": stream,
        "[[SOURCES]]": source_footer(news),
    }
    for key, value in replacements.items():
        page = page.replace(key, value)
    return page


def render_archive(editions):
    rows = []
    for index, edition in enumerate(editions):
        items = edition.get("items", [])
        top = items[0] if items else {"title": "当日简报"}
        date = edition["date"]
        rows.append(
            f'<li><a href="../daily/{date}.html"><span class="issue">第 {len(editions)-index} 期 · {date}</span>'
            f'{esc(top.get("title"))}</a><span class="edition-meta">{len(items)} 条个人情报</span></li>'
        )
    body = "".join(rows) or "<li>暂无历史简报</li>"
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#f3f6f2"><title>历史目录</title><style>{PAGE_TEMPLATE.split('<style>',1)[1].split('</style>',1)[0]}</style></head><body><header class="mast"><div class="mast-inner"><div class="mast-top"><span>每日个人情报流</span></div><h1>历史目录</h1><p>每一天保留当时的内容和版式</p></div></header><main class="page"><a class="back" href="../">返回今天</a><section class="archive-panel"><h2>全部简报</h2><p class="archive-intro">每天下午 5:00 后更新，最新一期排在最前面。</p><ul class="archive-list">{body}</ul></section></main></body></html>'''


def main():
    files = sorted(DATA_DIR.glob("news_*.json"))
    if not files:
        raise SystemExit("没有 data/news_*.json，请先运行 python fetch_news.py")
    editions = [json.loads(path.read_text(encoding="utf-8")) for path in reversed(files)]
    latest = editions[0]
    (SITE_DIR / ".nojekyll").touch()
    (SITE_DIR / "index.html").write_text(clean_output(render_daily(latest, "archive/")), encoding="utf-8")
    for edition in editions:
        daily_path = DAILY_DIR / f"{edition['date']}.html"
        # 历史页是当时规则和版式的快照。只更新今天，过去页面永不重写。
        if edition["date"] == latest["date"] or not daily_path.exists():
            daily_path.write_text(clean_output(render_daily(edition, "../archive/")), encoding="utf-8")
    (ARCHIVE_DIR / "index.html").write_text(clean_output(render_archive(editions)), encoding="utf-8")
    print(f"已生成手机首页：site/index.html（{len(latest.get('items', []))} 条）")
    print(f"已生成历史目录：site/archive/index.html（{len(editions)} 期）")


if __name__ == "__main__":
    main()
