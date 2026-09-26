# -*- coding: utf-8 -*-
"""
抓取 RSS 新闻 -> data/news_YYYY-MM-DD.json
纯标准库实现，零第三方依赖，Windows / GitHub Actions 均可直接运行。

用法：python fetch_news.py
"""
import sys
import re
import time
import html as html_mod
import json
import datetime
import email.utils
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import (
    NEWS_FEEDS, MAX_ITEMS_PER_FEED, MAX_ITEMS_TOTAL,
    MAX_AGE_HOURS, EXTRACT_SENTENCES, FETCH_TIMEOUT, TZ_OFFSET_HOURS,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

ATOM_NS = "{http://www.w3.org/2005/Atom}"

TZ = datetime.timezone(datetime.timedelta(hours=TZ_OFFSET_HOURS))
NOW_UTC = datetime.datetime.now(datetime.timezone.utc)


def fetch_bytes(url, attempts=2):
    """抓取 RSS 原始字节，带 UA、超时和一次重试（应对偶发网络抖动）。"""
    last_exc = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
                return resp.read()
        except Exception as exc:
            last_exc = exc
            if i < attempts - 1:
                time.sleep(3)
    raise last_exc


EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF]")


def clean_html(raw):
    """去掉 HTML 标签、反转义、压缩空白，并清除新闻原文中的 emoji 字符。"""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", "", raw)
    text = html_mod.unescape(text)
    text = EMOJI_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(value):
    """解析 RSS 的 pubDate / Atom 的 published，返回带时区的 datetime 或 None。"""
    if not value:
        return None
    value = str(value).strip()
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        pass
    try:
        dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return None


def extract_summary(text, n=EXTRACT_SENTENCES, limit=300):
    """抽取式摘要：取正文前 n 句话，最多 limit 字。"""
    text = clean_html(text)
    if not text:
        return ""
    parts = re.split(r"(?<=[。！？!?；;])", text)
    parts = [p.strip() for p in parts if p.strip()]
    summary = "".join(parts[:n]) if len(parts) > n else text
    return summary[:limit]


def parse_feed(feed_name, url, category):
    """解析单个 RSS/Atom 源，返回条目列表。失败抛异常由调用方处理。"""
    raw = fetch_bytes(url)
    root = ET.fromstring(raw)  # 尊重 XML 声明的编码
    items = []

    if root.tag == "rss":
        channel = root.find("channel")
        nodes = channel.findall("item") if channel is not None else []
        for node in nodes:
            title = node.findtext("title") or ""
            link = node.findtext("link") or ""
            desc = node.findtext("description") or node.findtext("encoded") or ""
            pub = parse_date(node.findtext("pubDate") or node.findtext("date"))
            items.append({"title": title, "link": link, "desc": desc, "pub": pub})
    elif root.tag == ATOM_NS + "feed":
        for entry in root.findall(ATOM_NS + "entry"):
            title = ""
            t = entry.find(ATOM_NS + "title")
            if t is not None:
                title = "".join(t.itertext())
            link_el = entry.find(ATOM_NS + "link")
            link = link_el.get("href") if link_el is not None else ""
            desc = ""
            for tag in ("summary", "content"):
                el = entry.find(ATOM_NS + tag)
                if el is not None:
                    desc = "".join(el.itertext())
                    break
            pub = parse_date((entry.findtext(ATOM_NS + "published")
                              or entry.findtext(ATOM_NS + "updated")))
            items.append({"title": title, "link": link, "desc": desc, "pub": pub})
    else:
        raise ValueError(f"无法识别的 feed 格式：{root.tag}")

    return items


def main():
    results = []
    seen = set()
    feed_stats = {}

    for feed_name, (url, category) in NEWS_FEEDS.items():
        try:
            items = parse_feed(feed_name, url, category)
        except Exception as exc:
            feed_stats[feed_name] = {"url": url, "status": "失败", "count": 0, "error": str(exc)[:120]}
            print(f"[失败] {feed_name}: {exc}")
            continue

        kept = 0
        for it in items:
            title = clean_html(it["title"])
            if not title or not it["link"]:
                continue
            key = re.sub(r"\s+", "", title).lower()[:40]
            if key in seen:
                continue
            pub = it["pub"]
            if pub is not None and (NOW_UTC - pub) > datetime.timedelta(hours=MAX_AGE_HOURS):
                continue
            summary = extract_summary(it["desc"], EXTRACT_SENTENCES)
            if not summary:
                summary = title
            seen.add(key)
            results.append({
                "title": title,
                "link": it["link"],
                "source": feed_name,
                "category": category,
                "published": pub.strftime("%Y-%m-%d %H:%M %z") if pub else "",
                "ts": int(pub.timestamp()) if pub else 0,
                "summary": summary,
            })
            kept += 1
            if kept >= MAX_ITEMS_PER_FEED:
                break

        feed_stats[feed_name] = {"url": url, "status": "成功" if kept else "成功(0条)", "count": kept}
        print(f"[成功] {feed_name}: {kept} 条")

    # 按时间倒序；无时间的排最后
    results.sort(key=lambda x: x["ts"], reverse=True)
    results = results[:MAX_ITEMS_TOTAL]

    today = NOW_UTC.astimezone(TZ).strftime("%Y-%m-%d")
    payload = {
        "date": today,
        "generated_at": datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %z"),
        "total": len(results),
        "sources": feed_stats,
        "items": results,
    }
    out = DATA_DIR / f"news_{today}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n共抓取 {len(results)} 条，已保存 -> {out}")
    if not results:
        print("警告：今日没有任何新闻被抓取，请检查网络或新闻源。")


if __name__ == "__main__":
    main()
