# -*- coding: utf-8 -*-
"""把每日数据构建成桌面端优先、无需 JavaScript 的静态简报。"""

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
    return f'''<section class="feed">{stories}</section>'''


def offer_href(date=None):
    base = "https://dawanglin.github.io/youhui-pages/"
    return f"{base}?date={esc(date)}" if date else base


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


def load_latest_business():
    """读取最新的商业建设观察数据；没有则返回 None（今日暂无）。"""
    files = sorted(DATA_DIR.glob("business_*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:
        return None


def biz_html(item):
    title = esc(item.get("title", "未命名线索"))
    url = esc(item.get("source_url") or "")
    source = esc(item.get("source_name") or item.get("source") or "来源未标注")
    published = esc(item.get("published_at") or item.get("date") or "")
    status = item.get("verify_status")
    status_html = f'<span class="biz-status {"" if status == "已查证" else "pending"}">{esc(status)}</span>' if status else ""
    summary = esc(item.get("scenario") or item.get("summary") or "")
    title_tag = (f'<a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'
                 if url else f'<span class="biz-title-plain">{title}</span>')
    summary_html = f'<p class="biz-summary">{summary}</p>' if summary else ""
    return f'''
      <article class="biz">
        <h3 class="biz-title">{title_tag}</h3>
        <p class="biz-meta">{source}{" · " + published if published else ""}{status_html}</p>
        {summary_html}
      </article>'''


def build_business(business):
    empty = ('<p class="biz-empty">今日暂无商业观察。只收录能追溯到原始来源的线索，宁缺毋滥；信息不足时不凑数。</p>')
    if not business or not business.get("items"):
        return empty
    cards = "".join(biz_html(item) for item in business["items"])
    note = ('<p class="biz-note">本栏为人工整理的商业线索：只收录官方文档、产品更新、开源项目或可核实的报道，每条标注来源。</p>')
    return cards + note


PAGE_TEMPLATE = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#f6f4ee"><meta name="description" content="每日情报简报：筛掉政治造势，留下能理解、能尝试、能落地的信息。"><title>[[TITLE]]</title>
<style>
:root {
  color-scheme: light;
  --page: #f6f4ee;
  --panel: #fbfaf6;
  --ink: #24313c;
  --body: #38454f;
  --muted: #6c7984;
  --line: #dfe4e6;
  --news: #2f7d66;
  --news-soft: #e2eee9;
  --biz: #a5672f;
  --biz-soft: #f3eadb;
  --focus: #2f7d66;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--page);
  color: var(--ink);
  font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", "WenQuanYi Micro Hei", sans-serif;
  font-size: 16px;
  line-height: 1.72;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
::selection { background: var(--news); color: #fff; }
a { color: inherit; }
.mast { padding: 34px 40px 22px; border-bottom: 1px solid var(--line); }
.mast-inner, .page, .footer-inner { width: min(100% - 64px, 1200px); margin-inline: auto; }
.mast-top { display: flex; justify-content: space-between; align-items: center; gap: 24px; }
.mast-links { display: inline-flex; align-items: center; gap: 22px; font-size: 14px; }
.mast-links a { text-decoration: none; color: var(--muted); padding: 6px 2px; border-bottom: 2px solid transparent; }
.mast-links a:hover { color: var(--ink); border-bottom-color: var(--news); }
.mast h1 { margin: 26px 0 4px; font-size: 34px; line-height: 1.15; letter-spacing: -.01em; }
.mast .subtitle { margin: 0 0 12px; font-size: 17px; color: var(--body); }
.mast .meta { margin: 0; font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
.mast .direction { margin: 18px 0 0; color: var(--body); font-size: 14px; border-left: 3px solid var(--news); padding-left: 12px; }
.layout { display: block; padding: 30px 0 20px; }
.section-heading { display: flex; justify-content: space-between; align-items: baseline; gap: 18px; padding: 0 0 12px; border-bottom: 1px solid var(--line); margin-bottom: 6px; }
.section-heading h2 { margin: 0; font-size: 18px; line-height: 1.3; letter-spacing: -.01em; }
.section-heading > span { color: var(--muted); font-size: 12px; }
.head-right { display: inline-flex; align-items: baseline; gap: 14px; }
.quick-jump { color: var(--biz); font-weight: 650; text-decoration: none; }
.quick-jump:hover { text-decoration: underline; }
.story { padding: 20px 0 22px; border-bottom: 1px solid var(--line); }
.story-title { display: block; font-size: 19px; font-weight: 680; line-height: 1.5; text-decoration: none; overflow-wrap: anywhere; }
.story-title:hover { color: var(--news); }
.story-title::after { content: "↗"; display: inline-block; margin-left: .3em; color: var(--news); font-size: .72em; font-weight: 500; transform: translateY(-.05em); }
.story-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 10px; margin: 10px 0 0; color: var(--muted); font-size: 12px; line-height: 1.55; }
.story-meta .topic { padding: 1px 8px; border-radius: 999px; background: var(--news-soft); color: #1f5c4a; font-weight: 600; }
.story-meta .lens { color: var(--news); font-weight: 600; }
.story-meta .source, .story-meta .published { font-variant-numeric: tabular-nums; }
.confidence { color: var(--muted); }
.confidence.verified { color: var(--news); }
.confidence.signal { color: var(--biz); }
.story-summary { margin: 11px 0 0; color: var(--body); font-size: 15px; line-height: 1.82; overflow-wrap: anywhere; }
.story-why { display: grid; grid-template-columns: auto 1fr; gap: 10px; margin: 13px 0 0; color: var(--body); font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
.story-why strong { align-self: start; color: var(--news); font-size: 12px; font-weight: 650; white-space: nowrap; }
.archive-link { margin-top: 22px; }
.archive-link a { color: var(--news); font-size: 13px; }
.col-business { margin-top: 44px; padding-top: 26px; border-top: 1px solid var(--line); }
.col-business .section-heading { border-bottom-color: #e6dcc9; }
.col-business h2 { color: var(--biz); }
.biz { margin: 0 0 22px; padding: 20px 0 22px; border-bottom: 1px solid var(--line); }
.biz-title { margin: 0; font-size: 19px; font-weight: 680; line-height: 1.5; }
.biz-title a { text-decoration: none; }
.biz-title a::after { content: "↗"; display: inline-block; margin-left: .3em; color: var(--biz); font-size: .72em; font-weight: 500; transform: translateY(-.05em); }
.biz-title a:hover { color: var(--biz); }
.biz-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 10px; margin: 10px 0 0; color: var(--muted); font-size: 12px; line-height: 1.55; font-variant-numeric: tabular-nums; }
.biz-status { margin-left: 8px; padding: 1px 6px; border-radius: 999px; background: var(--news-soft); color: #1f5c4a; font-size: 11px; }
.biz-status.pending { background: var(--biz-soft); color: #7c4c24; }
.biz-summary { margin: 11px 0 0; color: var(--body); font-size: 15px; line-height: 1.82; overflow-wrap: anywhere; }
.biz-empty, .biz-note { color: var(--muted); font-size: 13px; line-height: 1.7; }
.biz-note { margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--line); }
footer { padding: 26px 40px 40px; border-top: 1px solid var(--line); background: var(--panel); color: var(--muted); font-size: 12px; line-height: 1.8; }
.footer-note { margin-top: 9px; }
.archive-panel h2 { margin: 20px 0 8px; font-size: 21px; }
.archive-intro { margin: 0 0 8px; color: var(--muted); font-size: 13px; }
.archive-list { list-style: none; padding: 0; margin: 0; }
.archive-list li { padding: 20px 0; border-top: 1px solid var(--line); }
.archive-list a { display: block; min-height: 44px; text-decoration: none; font-size: 16px; line-height: 1.65; }
.archive-list .issue { display: block; margin-bottom: 3px; color: var(--news); font-weight: 700; font-variant-numeric: tabular-nums; }
.edition-meta { display: block; margin-top: 5px; color: var(--muted); font-size: 12px; }
.back { display: inline-block; margin: 20px 0 8px; color: var(--news); text-decoration: none; font-size: 14px; }
a:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; border-radius: 3px; }
html { scroll-behavior: smooth; }
@media (hover: hover) { .mast-links a:hover, .story-title:hover, .biz-title a:hover { color: var(--news); } }
@media (max-width: 960px) { .mast, footer { padding-left: 22px; padding-right: 22px; } .mast-inner, .page, .footer-inner { width: min(100% - 32px, 1200px); } }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
</style></head><body>
<header class="mast"><div class="mast-inner"><div class="mast-top"><nav class="mast-links" aria-label="栏目导航"><a href="#news">新闻情报</a><a href="[[ARCHIVE_HREF]]">历史新闻</a><a href="#business">商业建设观察</a><a href="[[OFFERS_HREF]]" target="_blank" rel="noopener noreferrer">生活优惠</a></nav></div><h1>每日情报简报</h1><p class="subtitle">今日动态与可落地线索</p><p class="meta">[[DATE]] · [[STATS]]</p><p class="direction">筛掉政治造势，留下能理解、能尝试、能落地的信息。</p></div></header>
<main class="page"><div class="layout"><section id="news" class="col-news"><div class="section-heading"><h2>新闻情报</h2><span class="head-right">[[NEWS_COUNT]] 条 · 按阅读价值排序<a class="quick-jump" href="#business">直达商业观察</a></span></div>[[STREAM]]<p class="archive-link"><a href="[[ARCHIVE_HREF]]">查看往期简报</a></p></section><section id="business" class="col-business"><div class="section-heading"><h2>商业建设观察</h2><span>高德与地图能力 · 可落地线索</span></div>[[BUSINESS]]</section></div></main>
<footer><div class="footer-inner">[[SOURCES]]<div class="footer-note">不使用 AI 大模型生成摘要。用户评价只作为体验线索；政治外交与泛国际冲突默认排除。商业建设观察为人工整理的商业线索，来源可追溯。</div></div></footer></body></html>'''


def render_daily(news, archive_href, offer_date=None, business=None):
    date = news["date"]
    offer_date = offer_date or date
    parsed = datetime.datetime.strptime(date, "%Y-%m-%d")
    date_cn = f"{parsed.year}年{parsed.month}月{parsed.day}日 {WEEKDAYS[parsed.weekday()]}"
    items = news.get("items", [])
    stream = build_stream(items)
    business_html = build_business(business)
    page = PAGE_TEMPLATE
    replacements = {
        "[[TITLE]]": f"每日情报简报 - {date}",
        "[[DATE]]": date_cn,
        "[[STATS]]": f"共 {len(items)} 条",
        "[[NEWS_COUNT]]": str(len(items)),
        "[[OFFERS_HREF]]": offer_href(offer_date),
        "[[ARCHIVE_HREF]]": archive_href,
        "[[STREAM]]": stream,
        "[[BUSINESS]]": business_html,
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
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#f6f4ee"><title>历史目录 - 每日情报简报</title><style>{PAGE_TEMPLATE.split('<style>',1)[1].split('</style>',1)[0]}</style></head><body><header class="mast"><div class="mast-inner"><div class="mast-top"><nav class="mast-links" aria-label="栏目导航"><a href="../">新闻情报</a><a href="../">历史新闻</a><a href="../#business">商业建设观察</a><a href="{esc(offer_href())}" target="_blank" rel="noopener noreferrer">生活优惠</a></nav></div><h1>历史目录</h1><p class="subtitle">每一天保留当时的内容和版式</p></div></header><main class="page"><a class="back" href="../">返回今天</a><section class="archive-panel"><h2>全部简报</h2><p class="archive-intro">每天下午 5:00 后更新，最新一期排在最前面。</p><ul class="archive-list">{body}</ul></section></main></body></html>'''


def main():
    files = sorted(DATA_DIR.glob("news_*.json"))
    if not files:
        raise SystemExit("没有 data/news_*.json，请先运行 python fetch_news.py")
    editions = [json.loads(path.read_text(encoding="utf-8")) for path in reversed(files)]
    latest = editions[0]
    business = load_latest_business()
    (SITE_DIR / ".nojekyll").touch()
    today_cn = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).date().isoformat()
    (SITE_DIR / "index.html").write_text(clean_output(render_daily(latest, "archive/", today_cn, business)), encoding="utf-8")
    for edition in editions:
        daily_path = DAILY_DIR / f"{edition['date']}.html"
        # 历史页是当时规则和版式的快照。只更新今天，过去页面永不重写。
        if edition["date"] == today_cn or not daily_path.exists():
            daily_path.write_text(clean_output(render_daily(edition, "../archive/", edition["date"], business)), encoding="utf-8")
    (ARCHIVE_DIR / "index.html").write_text(clean_output(render_archive(editions)), encoding="utf-8")
    print(f"已生成桌面首页：site/index.html（{len(latest.get('items', []))} 条新闻）")
    print(f"已生成历史目录：site/archive/index.html（{len(editions)} 期）")


if __name__ == "__main__":
    main()
