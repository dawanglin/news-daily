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
        <a class="story-title" href="{esc(item.get('link'))}" target="_blank" rel="noopener noreferrer">{esc(item['title'])}</a>
        <div class="story-meta">
          <span class="topic">{esc(item.get('topic'))}</span>
          <span class="lens">{esc(item.get('lens'))}</span>
          <span class="source">{esc(source_text)}</span>
          <span class="published">{esc(item.get('published'))}</span>
          <span class="confidence {esc(item['confidence_class'])}">{esc(item['confidence'])}</span>
        </div>
        <p class="story-summary">{esc(item['summary'])}</p>
        <p class="story-why"><strong>可以怎么用</strong><span>{esc(item['why'])}</span></p>
      </article>'''


def build_stream(items):
    stories = "".join(story_html(item) for item in items)
    return f'''<section class="feed"><div class="section-heading"><h2>今日更新</h2><span>{len(items)} 条，按阅读价值排序</span></div>{stories}</section>'''


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
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#f7f8f4"><meta name="description" content="每天发现能理解、能试用、能落地的新东西"><title>[[TITLE]]</title>
<style>
:root {
  color-scheme: light;
  --page: #f7f8f4;
  --paper: #fdfefa;
  --ink: #18241e;
  --body: #34443b;
  --muted: #66766d;
  --line: #d9e1da;
  --accent: #2d684f;
  --accent-soft: #dde8e0;
  --warm: #9a6a32;
  --focus: #b97a31;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--page);
  color: var(--ink);
  font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  font-size: 16px;
  line-height: 1.72;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
::selection { background: var(--accent); color: var(--paper); }
a { color: inherit; text-decoration-thickness: 1px; text-underline-offset: .22em; }
.mast {
  padding: calc(18px + env(safe-area-inset-top)) max(18px, env(safe-area-inset-left)) 26px;
  background: var(--paper);
  border-bottom: 1px solid var(--line);
}
.mast-inner, .page, .footer-inner { width: min(100%, 720px); margin-inline: auto; }
.mast-top { display: flex; justify-content: space-between; align-items: center; gap: 18px; color: var(--muted); font-size: 13px; }
.mast-top a, .back { min-height: 44px; display: inline-flex; align-items: center; color: var(--accent); font-weight: 650; text-decoration: underline; }
.mast h1 { max-width: 12em; margin: 20px 0 9px; font-size: clamp(29px, 8vw, 44px); line-height: 1.17; letter-spacing: -.03em; text-wrap: balance; }
.mast p { margin: 0; color: var(--muted); font-size: 14px; font-variant-numeric: tabular-nums; }
.method { display: block; margin-top: 13px; color: var(--accent); font-size: 13px; font-weight: 600; }
.page { padding: 8px max(18px, env(safe-area-inset-right)) 64px max(18px, env(safe-area-inset-left)); }
.section-heading { display: flex; justify-content: space-between; align-items: baseline; gap: 20px; padding: 25px 0 15px; border-bottom: 1px solid var(--ink); }
.section-heading h2 { margin: 0; font-size: 20px; line-height: 1.2; letter-spacing: -.02em; }
.section-heading > span { color: var(--muted); font-size: 12px; text-align: right; }
.story { padding: 25px 0 27px; border-bottom: 1px solid var(--line); }
.story-title { display: block; font-size: clamp(18px, 4.9vw, 21px); font-weight: 720; line-height: 1.48; letter-spacing: -.015em; text-decoration: none; text-wrap: pretty; overflow-wrap: anywhere; }
.story-title::after { content: "↗"; display: inline-block; margin-left: .35em; color: var(--accent); font-size: .75em; font-weight: 500; transform: translateY(-.06em); }
.story-title:active { color: var(--accent); }
.story-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 9px; margin: 11px 0 0; color: var(--muted); font-size: 12px; line-height: 1.55; }
.story-meta .topic { padding: 2px 8px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-weight: 650; }
.story-meta .lens { color: var(--accent); font-weight: 600; }
.story-meta .source, .story-meta .published { font-variant-numeric: tabular-nums; }
.confidence { color: var(--muted); }
.confidence.verified { color: var(--accent); }
.confidence.signal { color: var(--warm); }
.story-summary { margin: 13px 0 0; color: var(--body); font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif; font-size: 16px; line-height: 1.85; overflow-wrap: anywhere; }
.story-why { display: grid; grid-template-columns: auto 1fr; gap: 10px; margin: 15px 0 0; color: var(--body); font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
.story-why strong { align-self: start; padding: 1px 7px; border: 1px solid #bdd0c3; border-radius: 5px; color: var(--accent); font-size: 12px; font-weight: 650; white-space: nowrap; }
footer { padding: 27px max(18px, env(safe-area-inset-right)) calc(34px + env(safe-area-inset-bottom)) max(18px, env(safe-area-inset-left)); border-top: 1px solid var(--line); background: var(--paper); color: var(--muted); font-size: 12px; line-height: 1.8; }
.footer-note { margin-top: 9px; }
.archive-panel h2 { margin: 20px 0 8px; font-size: 21px; }
.archive-intro { margin: 0 0 8px; color: var(--muted); font-size: 13px; }
.archive-list { list-style: none; padding: 0; margin: 0; }
.archive-list li { padding: 20px 0; border-top: 1px solid var(--line); }
.archive-list a { display: block; min-height: 44px; text-decoration: none; font-size: 16px; line-height: 1.65; }
.archive-list .issue { display: block; margin-bottom: 3px; color: var(--accent); font-weight: 700; font-variant-numeric: tabular-nums; }
.edition-meta { display: block; margin-top: 5px; color: var(--muted); font-size: 12px; }
a:focus-visible { outline: 3px solid var(--focus); outline-offset: 4px; border-radius: 3px; }
@media (hover: hover) { .story-title:hover, .mast-top a:hover, .back:hover { color: var(--accent); } }
@media (min-width: 760px) {
  .mast { padding-top: 29px; padding-bottom: 31px; }
  .page { padding-left: 0; padding-right: 0; }
  .story { padding: 29px 0 31px; }
  .story-why { grid-template-columns: 86px 1fr; }
}
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
@media (prefers-color-scheme: dark) {
  :root { color-scheme: dark; --page: #111813; --paper: #18211b; --ink: #edf3ee; --body: #cbd6ce; --muted: #a5b2aa; --line: #36443b; --accent: #84c5a5; --accent-soft: #243a2e; --warm: #dfb477; --focus: #e0ad6e; }
  .story-why strong { border-color: #426453; }
}
</style></head><body>
<header class="mast"><div class="mast-inner"><div class="mast-top"><span>每日个人情报流</span><a href="[[ARCHIVE_HREF]]">查看往期</a></div><h1>今天，有什么可以拿来用</h1><p>[[DATE]] · [[STATS]]</p><span class="method">筛掉政治噪声，留下能理解、能尝试、能落地的信息</span></div></header>
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
    today_cn = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).date().isoformat()
    for edition in editions:
        daily_path = DAILY_DIR / f"{edition['date']}.html"
        # 历史页是当时规则和版式的快照。只更新今天，过去页面永不重写。
        if edition["date"] == today_cn or not daily_path.exists():
            daily_path.write_text(clean_output(render_daily(edition, "../archive/")), encoding="utf-8")
    (ARCHIVE_DIR / "index.html").write_text(clean_output(render_archive(editions)), encoding="utf-8")
    print(f"已生成手机首页：site/index.html（{len(latest.get('items', []))} 条）")
    print(f"已生成历史目录：site/archive/index.html（{len(editions)} 期）")


if __name__ == "__main__":
    main()
