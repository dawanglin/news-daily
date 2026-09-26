# -*- coding: utf-8 -*-
"""抓取中文 RSS 与公共热榜，使用免费规则生成手机简报数据。"""

import datetime
import difflib
import email.utils
import html as html_mod
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from config import (
    CATEGORY_HINTS,
    CATEGORY_ORDER,
    EXTRACT_SENTENCES,
    FETCH_TIMEOUT,
    MAX_AGE_HOURS,
    MAX_ITEMS_PER_FEED,
    MAX_ITEMS_TOTAL,
    MUST_READ_COUNT,
    NEWS_FEEDS,
    TZ_OFFSET_HOURS,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
ATOM_NS = "{http://www.w3.org/2005/Atom}"
TZ = datetime.timezone(datetime.timedelta(hours=TZ_OFFSET_HOURS))
NOW_UTC = datetime.datetime.now(datetime.timezone.utc)
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF]")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")

HOT_ENDPOINTS = {
    "百度热搜": "https://top.baidu.com/board?tab=realtime",
    "头条热榜": "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
    "B站热门": "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all",
}

CATEGORY_KEYWORDS = {
    "健康教育家庭": "医院 医生 医疗 健康 疾病 病毒 药品 食品安全 心理 睡眠 养老 老人 儿童 孩子 育儿 生育 家庭 婚姻 学校 教师 学生 教育 考试 高考 大学 幼儿园".split(),
    "钱包与消费": "价格 涨价 降价 房价 楼市 工资 收入 补贴 养老金 银行 存款 利率 股票 基金 保险 理财 消费 退款 赔偿 维权 诈骗 骗局 直播带货 促销 关税 税".split(),
    "吃喝住行": "食品 餐饮 外卖 做饭 美食 饮料 酒店 住房 租房 装修 家居 物业 高铁 铁路 地铁 公交 航班 机场 自驾 旅游 景区 天气 暴雨 台风 快递 交通 出行".split(),
    "文娱与体育": "电影 电视剧 综艺 明星 演员 歌手 音乐 演唱会 票房 游戏 动漫 体育 足球 篮球 乒乓 球员 比赛 冠军 亚运 奥运 网红 短剧 文物 文化".split(),
    "工作与科技": "AI 人工智能 机器人 芯片 手机 电脑 软件 应用 平台 数据 互联网 科技 数码 苹果 华为 小米 腾讯 阿里 字节 OpenAI 模型 职场 就业 招聘 创业 公司 企业".split(),
    "世界与中国": "美国 欧洲 日本 韩国 俄罗斯 乌克兰 以色列 伊朗 联合国 国际 外交 海外 全球 关税 战争 冲突 总统 首相".split(),
    "社会与民生": "警方 法院 检察院 判决 案件 事故 火灾 救援 社区 农村 农民 城市 政策 民生 公共 社会 调查 公益 失踪 通报 回应".split(),
}

SOURCE_CONFIDENCE = {
    "中国新闻网": ("已核实报道", "verified", 78),
    "BBC 中文": ("已核实报道", "verified", 74),
    "少数派": ("专业来源", "professional", 70),
    "IT之家": ("专业来源", "professional", 68),
    "Solidot": ("专业来源", "professional", 66),
    "量子位": ("专业来源", "professional", 67),
}


def fetch_bytes(url, attempts=2, accept="*/*"):
    last_exc = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
                return response.read(4_000_000)
        except Exception as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(2)
    raise last_exc


def clean_html(raw, limit=360):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(raw))
    text = html_mod.unescape(text)
    text = EMOJI_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def parse_date(value):
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(str(value).strip())
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed
    except Exception:
        pass
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None


def extract_summary(text, n=EXTRACT_SENTENCES, limit=220):
    text = clean_html(text, 500)
    if not text:
        return ""
    parts = [part.strip() for part in re.split(r"(?<=[。！？!?；;])", text) if part.strip()]
    summary = "".join(parts[:n]) if parts else text
    return summary if len(summary) <= limit else summary[: limit - 1].rstrip() + "…"


def has_chinese(text):
    return len(CHINESE_RE.findall(text or "")) >= 2


def classify(title, summary, default="社会与民生"):
    text = f"{title} {summary}"
    scores = {category: sum(text.count(word) for word in words) for category, words in CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else default


def normalized_title(title):
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", title).lower()[:90]


def is_similar(first, second):
    a, b = normalized_title(first), normalized_title(second)
    if not a or not b:
        return False
    return a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.82


def story(title, link, source, summary, pub, category, score, confidence, confidence_class, rank=0):
    ts = int(pub.timestamp()) if pub else int(NOW_UTC.timestamp())
    return {
        "title": clean_html(title, 160),
        "link": link,
        "source": source,
        "signals": [source],
        "category": category,
        "published": pub.astimezone(TZ).strftime("%m-%d %H:%M") if pub else "",
        "ts": ts,
        "summary": extract_summary(summary) or clean_html(title, 180),
        "why": CATEGORY_HINTS[category],
        "confidence": confidence,
        "confidence_class": confidence_class,
        "score": round(score, 2),
        "rank": rank,
        "must_read": False,
    }


def parse_feed(url):
    raw = fetch_bytes(url, accept="application/rss+xml, application/atom+xml, application/xml, text/xml, */*")
    root = ET.fromstring(raw)
    entries = []
    if root.tag == "rss":
        channel = root.find("channel")
        nodes = channel.findall("item") if channel is not None else []
        for node in nodes:
            entries.append({
                "title": node.findtext("title") or "",
                "link": node.findtext("link") or "",
                "desc": node.findtext("description") or node.findtext("encoded") or "",
                "pub": parse_date(node.findtext("pubDate") or node.findtext("date")),
            })
    elif root.tag == ATOM_NS + "feed":
        for node in root.findall(ATOM_NS + "entry"):
            title_node = node.find(ATOM_NS + "title")
            link_node = node.find(ATOM_NS + "link")
            summary_node = node.find(ATOM_NS + "summary") or node.find(ATOM_NS + "content")
            entries.append({
                "title": "".join(title_node.itertext()) if title_node is not None else "",
                "link": link_node.get("href", "") if link_node is not None else "",
                "desc": "".join(summary_node.itertext()) if summary_node is not None else "",
                "pub": parse_date(node.findtext(ATOM_NS + "published") or node.findtext(ATOM_NS + "updated")),
            })
    else:
        raise ValueError(f"无法识别的 feed 格式：{root.tag}")
    return entries


def fetch_baidu_hot(limit=14):
    text = fetch_bytes(HOT_ENDPOINTS["百度热搜"]).decode("utf-8", errors="ignore")
    match = re.search(r"<!--s-data:(.*?)-->", text, re.S)
    if not match:
        raise ValueError("未找到百度热搜数据")
    payload = json.loads(match.group(1))
    cards = payload.get("data", {}).get("cards", [])
    content = next((card.get("content", []) for card in cards if card.get("component") == "hotList"), [])
    items = []
    for rank, raw in enumerate(content[:limit], 1):
        title = clean_html(raw.get("query"))
        if not title:
            continue
        items.append(story(
            title, raw.get("url") or raw.get("appUrl") or "https://top.baidu.com/board?tab=realtime",
            "百度热搜", raw.get("desc") or title, NOW_UTC, "今日热议", 112 - rank * 2,
            "热度线索", "signal", rank,
        ))
    return items


def fetch_toutiao_hot(limit=14):
    payload = json.loads(fetch_bytes(HOT_ENDPOINTS["头条热榜"]))
    items = []
    for rank, raw in enumerate(payload.get("data", [])[:limit], 1):
        title = clean_html(raw.get("Title"))
        if not title:
            continue
        items.append(story(
            title, raw.get("Url") or "https://www.toutiao.com/",
            "头条热榜", title, NOW_UTC, "今日热议", 108 - rank * 2,
            "热度线索", "signal", rank,
        ))
    return items


def fetch_bilibili_hot(limit=12):
    payload = json.loads(fetch_bytes(HOT_ENDPOINTS["B站热门"]))
    items = []
    for rank, raw in enumerate(payload.get("data", {}).get("list", [])[:limit], 1):
        title = clean_html(raw.get("title"))
        if not title or not has_chinese(title):
            continue
        pub = datetime.datetime.fromtimestamp(raw.get("pubdate", int(NOW_UTC.timestamp())), datetime.timezone.utc)
        items.append(story(
            title, f"https://www.bilibili.com/video/{raw.get('bvid', '')}",
            "B站热门", raw.get("desc") or title, pub, "今日热议", 102 - rank * 1.7,
            "热度线索", "signal", rank,
        ))
    return items


def merge_story(collection, incoming):
    for current in collection:
        if not is_similar(current["title"], incoming["title"]):
            continue
        if incoming["source"] not in current["signals"]:
            current["signals"].append(incoming["source"])
            current["score"] += 7
        if current["confidence_class"] == "signal" and incoming["confidence_class"] != "signal":
            signals, score = current["signals"], current["score"]
            current.update(incoming)
            current["signals"] = list(dict.fromkeys(signals + incoming["signals"]))
            current["score"] = max(score, incoming["score"]) + 4
        if len(current["signals"]) > 1:
            current["why"] += f" 已在 {len(current['signals'])} 个来源或平台出现。"
        return
    collection.append(incoming)


def select_balanced(items):
    caps = {category: (6 if category == "今日热议" else 4) for category in CATEGORY_ORDER}
    selected, remaining = [], []
    counts = {category: 0 for category in CATEGORY_ORDER}
    for item in sorted(items, key=lambda value: (value["score"], value["ts"]), reverse=True):
        category = item["category"]
        if counts.get(category, 0) < caps.get(category, 4) and len(selected) < MAX_ITEMS_TOTAL:
            selected.append(item)
            counts[category] = counts.get(category, 0) + 1
        else:
            remaining.append(item)
    for item in remaining:
        if len(selected) >= MAX_ITEMS_TOTAL:
            break
        selected.append(item)

    chosen_per_category = {}
    must_read = 0
    for item in selected:
        category = item["category"]
        used = chosen_per_category.get(category, 0)
        if must_read < MUST_READ_COUNT and used < 2:
            item["must_read"] = True
            chosen_per_category[category] = used + 1
            must_read += 1
    if must_read < MUST_READ_COUNT:
        for item in selected:
            if must_read >= MUST_READ_COUNT:
                break
            if not item["must_read"]:
                item["must_read"] = True
                must_read += 1
    return selected


def main():
    results = []
    source_stats = {}

    for source, fetcher in (("百度热搜", fetch_baidu_hot), ("头条热榜", fetch_toutiao_hot), ("B站热门", fetch_bilibili_hot)):
        try:
            items = fetcher()
            for item in items:
                merge_story(results, item)
            source_stats[source] = {"status": "成功", "count": len(items), "type": "公共热榜"}
            print(f"[热榜] {source}: {len(items)} 条")
        except Exception as exc:
            source_stats[source] = {"status": "失败", "count": 0, "error": str(exc)[:120], "type": "公共热榜"}
            print(f"[失败] {source}: {exc}")

    for source, (url, default_category) in NEWS_FEEDS.items():
        try:
            raw_items = parse_feed(url)
        except Exception as exc:
            source_stats[source] = {"status": "失败", "count": 0, "error": str(exc)[:120], "type": "媒体来源"}
            print(f"[失败] {source}: {exc}")
            continue
        kept = 0
        confidence, confidence_class, base_score = SOURCE_CONFIDENCE[source]
        for raw in raw_items:
            title = clean_html(raw["title"], 160)
            if not title or not raw["link"] or not has_chinese(title):
                continue
            pub = raw["pub"]
            if pub and NOW_UTC - pub.astimezone(datetime.timezone.utc) > datetime.timedelta(hours=MAX_AGE_HOURS):
                continue
            summary = extract_summary(raw["desc"]) or title
            category = classify(title, summary, default_category)
            age_hours = max(0, (NOW_UTC - pub.astimezone(datetime.timezone.utc)).total_seconds() / 3600) if pub else 24
            score = base_score + max(0, 12 - age_hours / 2)
            merge_story(results, story(
                title, raw["link"], source, summary, pub or NOW_UTC, category, score,
                confidence, confidence_class,
            ))
            kept += 1
            if kept >= MAX_ITEMS_PER_FEED:
                break
        source_stats[source] = {"status": "成功" if kept else "成功(0条)", "count": kept, "type": "媒体来源"}
        print(f"[媒体] {source}: {kept} 条")

    selected = select_balanced(results)
    today = NOW_UTC.astimezone(TZ).strftime("%Y-%m-%d")
    payload = {
        "date": today,
        "generated_at": datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %z"),
        "total": len(selected),
        "method": "公共热榜发现 + 中文媒体核实 + 免费规则分类（未使用 AI）",
        "categories": CATEGORY_ORDER,
        "sources": source_stats,
        "items": selected,
    }
    output = DATA_DIR / f"news_{today}.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n共整理 {len(selected)} 条，已保存 -> {output}")
    if not selected:
        raise SystemExit("今日没有抓到可用内容")


if __name__ == "__main__":
    main()
