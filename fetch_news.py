"""抓取 RSS / Atom 新闻并保存为可追溯 JSON。仅使用 Python 标准库。"""

from __future__ import annotations

import hashlib
import html
import json
import re
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import config

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None, limit: int = 280) -> str:
    text = html.unescape(TAG_RE.sub(" ", value or ""))
    text = SPACE_RE.sub(" ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node.iter():
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in names and child.text:
            return child.text.strip()
    return ""


def entry_link(node: ET.Element) -> str:
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        href = child.attrib.get("href", "").strip()
        rel = child.attrib.get("rel", "alternate")
        if href and rel in ("alternate", ""):
            return href
        if child.text and child.text.strip().startswith("http"):
            return child.text.strip()
    return ""


def normalize_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        parsed = parsedate_to_datetime(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return raw[:40]


def fetch_xml(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NewsDailyBot/1.0 (+https://github.com/dawanglin/news-daily)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=config.REQUEST_TIMEOUT, context=context) as response:
        return response.read(4_000_000)


def parse_feed(xml_bytes: bytes, source: str, category: str) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    nodes = [n for n in root.iter() if n.tag.rsplit("}", 1)[-1].lower() in ("item", "entry")]
    items = []
    for node in nodes[: config.MAX_ITEMS_PER_FEED * 2]:
        title = clean_text(child_text(node, ("title",)), 180)
        link = entry_link(node)
        description = child_text(node, ("description", "summary", "content", "encoded"))
        published = child_text(node, ("pubdate", "published", "updated", "date"))
        if not title or not link or urlparse(link).scheme not in ("http", "https"):
            continue
        items.append(
            {
                "id": hashlib.sha256(link.encode("utf-8")).hexdigest()[:12],
                "title": title,
                "url": link,
                "source": source,
                "category": category,
                "published_at": normalize_date(published),
                "summary": clean_text(description) or "点击查看原文了解详情。",
            }
        )
        if len(items) >= config.MAX_ITEMS_PER_FEED:
            break
    return items


def sort_key(item: dict) -> str:
    return item.get("published_at") or ""


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_items: list[dict] = []
    errors: list[str] = []
    for source, (url, category) in config.NEWS_FEEDS.items():
        try:
            items = parse_feed(fetch_xml(url), source, category)
            all_items.extend(items)
            print(f"[成功] {source}: {len(items)} 条")
        except Exception as exc:  # 单源失败不影响全局
            errors.append(f"{source}: {type(exc).__name__}: {exc}")
            print(f"[失败] {errors[-1]}", file=sys.stderr)

    unique: dict[str, dict] = {}
    for item in all_items:
        key = re.sub(r"\W+", "", item["title"].lower())[:120] or item["url"]
        unique.setdefault(key, item)
    news = sorted(unique.values(), key=sort_key, reverse=True)[: config.MAX_ITEMS_TOTAL]

    now = datetime.now().astimezone()
    payload = {
        "date": now.date().isoformat(),
        "generated_at": now.isoformat(),
        "count": len(news),
        "errors": errors,
        "items": news,
    }
    output = DATA_DIR / f"news_{now.date().isoformat()}.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存 {len(news)} 条新闻：{output}")
    return 0 if news else 1


if __name__ == "__main__":
    raise SystemExit(main())

