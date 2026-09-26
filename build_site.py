# -*- coding: utf-8 -*-
"""
根据 data/news_*.json 和（可选的）data/summary_*.md 生成静态站点：
  site/index.html                 最新一期（GitHub Pages 首页）
  site/daily/YYYY-MM-DD.html      每日归档页
  site/archive/index.html         历史归档索引

用法：python build_site.py
"""
import sys
import re
import json
import html as html_mod
import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import NEWS_FEEDS, TZ_OFFSET_HOURS

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SITE_DIR = BASE_DIR / "site"
DAILY_DIR = SITE_DIR / "daily"
ARCHIVE_DIR = SITE_DIR / "archive"
DAILY_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
CATEGORY_TAG = {"科技": "tag-tech", "综合": "tag-news"}


def esc(text):
    return html_mod.escape(str(text), quote=True)


def inline_md(text):
    """处理行内 Markdown：**加粗**、`代码`、[文字](链接)。"""
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


def md_to_html(md):
    """极简 Markdown -> HTML（支持 #、##、-、数字列表、段落）。"""
    lines = md.splitlines()
    out = []
    in_list = False
    for line in lines:
        s = line.strip()
        if not s:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if s.startswith("##"):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f'<h3 class="digest-h3">{inline_md(s.lstrip("#").strip())}</h3>')
        elif s.startswith("###"):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f'<h4 class="digest-h4">{inline_md(s.lstrip("#").strip())}</h4>')
        elif s.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_md(s[2:].strip())}</li>")
        elif re.match(r"^\d+[.、)]\s+", s):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_md(re.sub(r'^\\d+[.、)]\\s+', '', s))}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{inline_md(s)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def build_sections(items):
    """按分类生成新闻区块 HTML。"""
    cats = {}
    for it in items:
        cats.setdefault(it["category"], []).append(it)
    order = [c for c in ("科技", "综合") if c in cats] + [c for c in cats if c not in ("科技", "综合")]

    blocks = []
    for cat in order:
        tag_class = CATEGORY_TAG.get(cat, "tag-other")
        cards = []
        for it in cats[cat]:
            time_short = it.get("published", "")[:16]
            cards.append(f"""
              <article class="card">
                <a class="card-title" href="{esc(it['link'])}" target="_blank" rel="noopener">{esc(it['title'])}</a>
                <div class="meta">
                  <span class="tag {tag_class}">{esc(cat)}</span>
                  <span class="src">{esc(it['source'])}</span>
                  <span class="time">{esc(time_short)}</span>
                </div>
                <p class="summary">{esc(it['summary'])}</p>
              </article>""")
        blocks.append(f"""
        <section class="section">
          <h2 class="section-title"><span class="dot {tag_class}"></span>{esc(cat)}<span class="count">{len(cats[cat])} 条</span></h2>
          <div class="grid">{"".join(cards)}</div>
        </section>""")
    return "\n".join(blocks)


def build_sources_footer():
    links = " · ".join(
        f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(name)}</a>'
        for name, (url, _cat) in NEWS_FEEDS.items()
    )
    return f"数据来源：{links}"


def build_stats(news):
    items = news.get("items", [])
    n_src = len(news.get("sources", {}))
    return f"""
      <span class="chip">共 {len(items)} 条新闻</span>
      <span class="chip">{n_src} 个来源</span>
      <span class="chip">生成于 {esc(news.get('generated_at', ''))}</span>"""


def empty_notice():
    return """
      <div class="notice">今日暂无新闻数据。可能原因：网络异常、新闻源失效或抓取失败。
      可在 GitHub Actions 页面手动触发 workflow 重试，或检查 config.py 中的新闻源。</div>"""


def render_page(title, date_cn, stats, digest, body, sources_footer, archive_link=""):
    template = PAGE_TEMPLATE
    for key, value in {
        "[[TITLE]]": title,
        "[[DATE]]": date_cn,
        "[[STATS]]": stats,
        "[[DIGEST]]": digest,
        "[[BODY]]": body,
        "[[SOURCES]]": sources_footer,
        "[[ARCHIVE]]": archive_link,
    }.items():
        template = template.replace(key, value)
    return template


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>[[TITLE]]</title>
<link rel="icon" href='data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="18" fill="%231a3a5c"/><rect x="22" y="26" width="56" height="9" rx="4.5" fill="white"/><rect x="22" y="43" width="56" height="9" rx="4.5" fill="white" opacity="0.85"/><rect x="22" y="60" width="34" height="9" rx="4.5" fill="white" opacity="0.65"/></svg>'>
<style>
  :root {
    --ink: #1f2328;
    --muted: #6b7280;
    --line: #e3e6ea;
    --bg: #f4f5f7;
    --card: #ffffff;
    --brand: #1a3a5c;
    --tech: #1e6fd9;
    --news: #0e8a5f;
    --amber: #b9791f;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", "Segoe UI", system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--ink); line-height: 1.6; font-size: 15px;
  }
  .wrap { max-width: 980px; margin: 0 auto; padding: 0 20px 60px; }
  header.site {
    background: linear-gradient(135deg, #16324f 0%, #1a3a5c 55%, #24506f 100%);
    color: #fff; padding: 34px 0 26px; margin-bottom: 26px;
  }
  .head-inner { max-width: 980px; margin: 0 auto; padding: 0 20px; }
  .head-row { display: flex; flex-wrap: wrap; align-items: baseline; gap: 12px; }
  .site-title { font-size: 26px; font-weight: 700; letter-spacing: 1px; }
  .site-sub { font-size: 13px; opacity: 0.75; }
  .date-badge {
    margin-left: auto; background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.25);
    padding: 4px 14px; border-radius: 999px; font-size: 14px; font-weight: 600;
  }
  .stats { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
  .chip {
    background: rgba(255,255,255,0.12); border-radius: 999px; padding: 3px 12px;
    font-size: 12.5px; color: #e8eef5;
  }
  .digest {
    background: #fffbf0; border: 1px solid #f0e0b8; border-left: 5px solid var(--amber);
    border-radius: 10px; padding: 18px 22px; margin-bottom: 26px;
  }
  .digest-title { font-size: 17px; font-weight: 700; color: #8a5b10; margin-bottom: 10px; }
  .digest p { margin: 6px 0; }
  .digest ul { margin: 6px 0 6px 22px; }
  .digest li { margin: 4px 0; }
  .digest-h3 { font-size: 14.5px; color: #6b4c0d; margin: 10px 0 4px; }
  .digest-h4 { font-size: 13.5px; color: #7a5a14; margin: 8px 0 2px; }
  .digest code { background: #f6ead0; border-radius: 4px; padding: 1px 5px; font-size: 13px; }
  .digest a { color: #8a5b10; }
  .section { margin-bottom: 30px; }
  .section-title {
    display: flex; align-items: center; gap: 10px; font-size: 19px; font-weight: 700;
    color: var(--brand); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 2px solid var(--line);
  }
  .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
  .tag-tech { background: var(--tech); }
  .tag-news { background: var(--news); }
  .tag-other { background: var(--amber); }
  .count { margin-left: auto; font-size: 13px; font-weight: 500; color: var(--muted); }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card {
    background: var(--card); border: 1px solid var(--line); border-radius: 10px;
    padding: 14px 16px; transition: box-shadow .15s ease, transform .15s ease;
  }
  .card:hover { box-shadow: 0 6px 18px rgba(26,58,92,.10); transform: translateY(-1px); }
  .card-title { font-size: 15px; font-weight: 600; color: #14304e; text-decoration: none; display: block; }
  .card-title:hover { color: var(--tech); text-decoration: underline; }
  .meta { display: flex; align-items: center; gap: 8px; margin: 8px 0 6px; flex-wrap: wrap; }
  .tag { color: #fff; font-size: 11px; padding: 1px 8px; border-radius: 999px; font-weight: 600; }
  .src { font-size: 12.5px; color: var(--muted); }
  .time { font-size: 12px; color: #9aa1ab; }
  .summary { font-size: 13.5px; color: #4b5563; }
  .notice {
    background: #fef2f2; border: 1px solid #f3c8c8; color: #9a3b3b;
    border-radius: 10px; padding: 16px 20px; margin-bottom: 26px; font-size: 14px;
  }
  .archive-panel {
    background: #f8f7f3; border: 1px solid #d8dde3; border-radius: 18px;
    padding: 26px 30px 22px; box-shadow: 0 14px 32px rgba(26,58,92,.07);
  }
  .archive-panel h2 {
    color: #20262d; font-size: 21px; letter-spacing: .04em;
    padding-bottom: 12px; border-bottom: 1px solid #d8dde3;
  }
  .archive-intro { color: var(--muted); font-size: 13px; margin: 10px 0 6px; }
  .archive-list { list-style: none; }
  .archive-list li { position: relative; padding: 14px 0 14px 24px; border-bottom: 1px solid #e4e6e8; }
  .archive-list li:last-child { border-bottom: 0; }
  .archive-list li::before {
    content: ""; position: absolute; left: 2px; top: 26px; width: 6px; height: 6px;
    border-radius: 50%; background: #39434c;
  }
  .archive-list a {
    color: #20262d; font-size: 17px; line-height: 1.75; text-decoration: none;
    text-underline-offset: 4px;
  }
  .archive-list a:hover, .archive-list a:focus-visible { color: var(--tech); text-decoration: underline; }
  .archive-list .issue { font-weight: 700; color: var(--brand); }
  .archive-list .current a, .archive-list .current .issue { color: var(--tech); }
  .archive-list .edition-meta { color: var(--muted); font-size: 12px; margin-left: 8px; white-space: nowrap; }
  footer.site {
    margin-top: 30px; padding-top: 16px; border-top: 1px solid var(--line);
    color: var(--muted); font-size: 12.5px;
  }
  footer.site .srcs { line-height: 2; }
  footer.site .srcs a { color: var(--tech); text-decoration: none; white-space: nowrap; margin-right: 10px; }
  footer.site .srcs a:hover { text-decoration: underline; }
  footer.site .note { margin-top: 2px; }
  .back { margin-bottom: 16px; display: inline-block; color: var(--tech); text-decoration: none; font-size: 14px; }
  @media (max-width: 720px) {
    .grid { grid-template-columns: 1fr; }
    .site-title { font-size: 21px; }
    .date-badge { margin-left: 0; }
    .archive-panel { padding: 20px 20px 16px; border-radius: 14px; }
    .archive-list a { font-size: 16px; }
    .archive-list .edition-meta { display: block; margin: 2px 0 0; }
  }
</style>
</head>
<body>
<header class="site">
  <div class="head-inner">
    <div class="head-row">
      <span class="site-title">每日新闻速览</span>
      <span class="site-sub">Daily News Digest</span>
      <span class="date-badge">[[DATE]]</span>
    </div>
    <div class="stats">[[STATS]]</div>
  </div>
</header>
<main class="wrap">
  [[ARCHIVE]]
  [[DIGEST]]
  [[BODY]]
  <footer class="site">
    <div class="srcs">[[SOURCES]]</div>
    <div class="note">由 GitHub Actions 每日自动抓取生成，仅供个人参考</div>
  </footer>
</main>
</body>
</html>
"""


def main():
    files = sorted(DATA_DIR.glob("news_*.json"))
    if not files:
        print("没有 data/news_*.json，请先运行 python fetch_news.py")
        sys.exit(1)

    news = json.loads(files[-1].read_text(encoding="utf-8"))
    date = news["date"]
    items = news.get("items", [])

    dt = datetime.datetime.strptime(date, "%Y-%m-%d")
    date_cn = f"{dt.year}年{dt.month}月{dt.day}日 {WEEKDAYS[dt.weekday()]}"
    title = f"每日新闻速览 - {date}"

    # AI 综述（可选）
    digest = ""
    summary_file = DATA_DIR / f"summary_{date}.md"
    if summary_file.exists():
        digest = f'<div class="digest"><div class="digest-title">今日要闻综述（AI）</div>{md_to_html(summary_file.read_text(encoding="utf-8"))}</div>'

    body = build_sections(items) if items else empty_notice()
    stats = build_stats(news)
    sources_footer = build_sources_footer()

    archive_link = '<a class="back" href="archive/">历史存档 →</a>'
    page = render_page(title, date_cn, stats, digest, body, sources_footer, archive_link)

    (SITE_DIR / "index.html").write_text(page, encoding="utf-8")
    (DAILY_DIR / f"{date}.html").write_text(page, encoding="utf-8")

    # 归档索引：每一期显示日期和当天第一条代表性新闻。
    news_files = sorted(DATA_DIR.glob("news_*.json"), reverse=True)
    rows = []
    for index, f in enumerate(news_files):
        edition = json.loads(f.read_text(encoding="utf-8"))
        d = edition["date"]
        compact_date = d.replace("-", "")
        edition_items = edition.get("items", [])
        headline = edition_items[0]["title"] if edition_items else "当日新闻速览"
        current_class = ' class="current"' if index == 0 else ""
        rows.append(
            f'<li{current_class}><a href="../daily/{d}.html">'
            f'<span class="issue">【每日新闻速览{compact_date}】</span>{esc(headline)}'
            f'</a><span class="edition-meta">{len(edition_items)} 条</span></li>'
        )
    archive_body = (
        '<section class="archive-panel"><h2>每日目录</h2>'
        '<p class="archive-intro">按日期回看，每一期标题取自当天头条。</p>'
        '<ul class="archive-list">' + "".join(rows) + "</ul></section>"
    )
    archive_page = render_page(
        "历史存档", f"共 {len(rows)} 期", "",
        "", archive_body, sources_footer,
        '<a class="back" href="../">返回最新一期 →</a>',
    )
    (ARCHIVE_DIR / "index.html").write_text(archive_page, encoding="utf-8")

    print(f"已生成：site/index.html（最新一期）")
    print(f"已生成：site/daily/{date}.html（归档）")
    print(f"已生成：site/archive/index.html（{len(rows)} 期历史索引）")


if __name__ == "__main__":
    main()
