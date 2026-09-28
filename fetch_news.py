# -*- coding: utf-8 -*-
"""抓取中文专业来源，用免费规则整理成个人项目情报流。"""

import datetime
import difflib
import email.utils
import html as html_mod
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from config import (
    CATEGORY_HINTS, CATEGORY_ORDER, EXTRACT_SENTENCES, FETCH_TIMEOUT,
    MAX_AGE_HOURS, MAX_ITEMS_PER_FEED, MAX_ITEMS_TOTAL, NEWS_FEEDS,
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

# 主目录是“从想法到维护”的阶段；主题作为第二层标签。
STAGE_KEYWORDS = {
    "行业观察": "行业 市场 公司 团队 生态 竞争 融资 收购 商业 产品线 路线图 开发者生态 开源生态 用户增长 订阅".split(),
    "想法与概念": "概念 理论 原理 发现 研究 论文 猜想 定理 模型 趋势 观点 范式 数学 物理 量子 空间 因果 不确定性".split(),
    "孵化与转化": "创意 灵感 原型 Demo 项目 产品 应用 场景 方案 孵化 转化 独立开发 小游戏 网页 游戏开发 交互".split(),
    "工具与硬件": "工具 软件 插件 平台 框架 库 SDK API IDE 编辑器 开源 硬件 芯片 机器人 电脑 设备 浏览器".split(),
    "方法与执行": "教程 指南 实践 实现 开发 构建 编程 代码 工作流 步骤 方法 部署 自动化 训练 微调 提示词".split(),
    "测试与成果": "测试 评测 基准 跑分 验证 实验 结果 成果 性能 效果 纪录 发布 上线 复现 对比".split(),
    "维护与复盘": "维护 故障 漏洞 安全 隐私 成本 优化 修复 升级 兼容 稳定 复盘 争议 边界 版权 许可证".split(),
}

TOPIC_KEYWORDS = {
    "AI模型": "AI 人工智能 大模型 模型 Agent 智能体 OpenAI Claude Anthropic DeepSeek Gemini GPT 推理 多模态 RAG MCP token 智谱 通义 Kimi 豆包 Llama".split(),
    "网页小游戏": "网页 前端 HTML CSS JavaScript TypeScript WebGL Canvas Three.js 浏览器 小游戏 游戏开发 交互 动画 像素 Unity Godot Phaser React Vue Svelte 小程序".split(),
    "编程工具": "编程 代码 开源 GitHub 软件 开发者 API SDK IDE 数据库 Python Rust Go Java Docker Linux 自动化 插件 框架".split(),
    "数学物理": "数学 物理 定理 猜想 几何 概率 统计 算法 量子 粒子 材料 天文 宇宙 科学家 证明 方程 理论 实验 分子 原子 晶体 导电 磁场 光学 声学 能量 同素异形体 神经系统".split(),
    "数据空间": "数据 数据科学 可视化 地图 地理 空间 GIS 遥感 坐标 图谱 网络 关系 因果 预测 不确定性 模糊 聚类 时序 拓扑 数字孪生 知识图谱".split(),
    "四川生活": "四川 成都 重庆 西南 本地 天气 地震 交通 地铁 高铁 政务 医保 教育 住房 数字生活".split(),
}

# 默认排除政治外交、战争、泛国际冲突和纯娱乐体育。
HARD_NEGATIVE = "习近平 特朗普 总统 首相 外交 联合国 北约 乌克兰 俄罗斯 伊朗 以色列 沙特 军事 战争 冲突 制裁 关税 峰会 会晤 国事访问 中美关系 国际局势 亚运 奥运 冠军 明星 演唱会".split()
LOCAL_STRONG = "四川 成都 重庆 西南".split()
LOW_VALUE = "财报 手机发布 新车上市 新车 车型 万元起 续航 交付 售价 开售 促销 爆料 传闻 接待 活动".split()
CLICKBAIT = "闯大祸 离谱 炸裂 杀疯了 震惊 惊呆 失控 猛料 神器 梅西终结者 夯爆了 卷疯了 啥题啊 能干崩".split()

SOURCE_MAX_AGE = {
    "科学网·数理科学": 240,
    "科学网·科普": 168,
    "前端技术精选": 192,
    "阮一峰的网络日志": 336,
}

SOURCE_CONFIDENCE = {
    "量子位": ("AI 专业来源", "professional", 78),
    "机器之心": ("AI 专业来源", "professional", 79),
    "InfoQ 中文": ("开发专业来源", "professional", 78),
    "开源中国": ("开源社区来源", "professional", 76),
    "少数派": ("数字生活来源", "professional", 70),
    "IT之家": ("科技资讯来源", "professional", 62),
    "Solidot": ("科技社区来源", "professional", 66),
    "科学网·数理科学": ("学术专业来源", "professional", 80),
    "科学网·科普": ("科学科普来源", "verified", 73),
    "前端技术精选": ("前端专业精选", "professional", 75),
    "阮一峰的网络日志": ("开发者一手文章", "professional", 77),
}


def fetch_bytes(url, attempts=2, accept="*/*"):
    last_exc = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
                return response.read(5_000_000)
        except Exception as exc:
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(2)
    raise last_exc


def clean_html(raw, limit=420):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(raw))
    text = html_mod.unescape(text)
    text = EMOJI_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def parse_date(value):
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(str(value).strip())
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        pass
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None


def extract_summary(text, n=EXTRACT_SENTENCES, limit=240):
    text = clean_html(text, 600)
    parts = [part.strip() for part in re.split(r"(?<=[。！？!?；;])", text) if part.strip()]
    summary = "".join(parts[:n]) if parts else text
    return summary if len(summary) <= limit else summary[:limit - 1].rstrip() + "…"


def has_chinese(text):
    return len(CHINESE_RE.findall(text or "")) >= 2


def keyword_score(text, words, title):
    low_text, low_title = text.lower(), title.lower()
    return sum((3 if word.lower() in low_title else 1) * low_text.count(word.lower()) for word in words)


def classify(title, summary, default_stage):
    text = f"{title} {summary}"
    if any(word in text for word in HARD_NEGATIVE) and not any(word in text for word in LOCAL_STRONG):
        return None
    if any(word in title for word in CLICKBAIT):
        return None
    topic_scores = {name: keyword_score(text, words, title) for name, words in TOPIC_KEYWORDS.items()}
    topic = max(topic_scores, key=topic_scores.get)
    relevance = topic_scores[topic]
    if relevance < 2:
        return None
    stage_scores = {name: keyword_score(text, words, title) for name, words in STAGE_KEYWORDS.items()}
    stage = max(stage_scores, key=stage_scores.get)
    if stage_scores[stage] == 0:
        stage = default_stage
    relevance -= sum(2 for word in LOW_VALUE if word in text)
    if topic in {"AI模型", "网页小游戏", "数据空间"}:
        relevance += 3
    if relevance < 3:
        return None
    return stage, topic, relevance


def make_why(stage, topic, title, summary):
    text = f"{title} {summary}".lower()
    if stage == "行业观察":
        action = "看它会怎样改变你可选择的模型、工具或创作机会，不追逐与方向无关的商业热闹。"
    elif stage == "想法与概念":
        action = "先写下它的新概念、关键变量，以及它改变了哪个旧认识。"
    elif stage == "孵化与转化":
        action = "尝试把它缩成一个当天能开始的网页、小工具或验证性实验。"
    elif stage == "工具与硬件":
        action = "检查它能替代哪一步现有操作，再决定是否实际安装或接入。"
    elif stage == "方法与执行":
        action = "抽出可复现的步骤，选其中最小的一步亲手执行。"
    elif stage == "测试与成果":
        action = "重点看测试条件、比较对象和失败情况，而不只看最终数字。"
    else:
        action = "记录长期成本、故障边界和维护办法，避免只看到发布时的效果。"
    if topic == "AI模型" and any(word in text for word in ("成本", "价格", "token", "开源", "本地")):
        return "可比较模型成本、开放程度和本地使用门槛。" + action
    if topic == "网页小游戏":
        return "可拆出一个界面、交互或游戏机制。" + action
    if topic == "数据空间":
        return "可练习把位置、数据和模糊关系连接起来。" + action
    if any(word in text for word in ("破解", "安全", "漏洞", "隐私")):
        return "它触及你正在使用的软件和代码边界。" + action
    return f"它与“{topic}”方向直接相关。{action}"


def normalized_title(title):
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", title).lower()[:100]


def is_similar(first, second):
    a, b = normalized_title(first), normalized_title(second)
    return bool(a and b) and (a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.82)


def parse_feed(url):
    root = ET.fromstring(fetch_bytes(url, accept="application/rss+xml, application/atom+xml, application/xml, text/xml, */*"))
    entries = []
    if root.tag == "rss" or root.tag.endswith("rss"):
        channel = root.find("channel")
        for node in channel.findall("item") if channel is not None else []:
            encoded = next((child.text for child in node if child.tag.endswith("encoded")), "")
            entries.append({"title": node.findtext("title") or "", "link": node.findtext("link") or "",
                            "desc": node.findtext("description") or encoded or "",
                            "pub": parse_date(node.findtext("pubDate") or node.findtext("date"))})
    elif root.tag == ATOM_NS + "feed":
        for node in root.findall(ATOM_NS + "entry"):
            title_node, link_node = node.find(ATOM_NS + "title"), node.find(ATOM_NS + "link")
            summary_node = node.find(ATOM_NS + "summary")
            if summary_node is None:
                summary_node = node.find(ATOM_NS + "content")
            entries.append({"title": "".join(title_node.itertext()) if title_node is not None else "",
                            "link": link_node.get("href", "") if link_node is not None else "",
                            "desc": "".join(summary_node.itertext()) if summary_node is not None else "",
                            "pub": parse_date(node.findtext(ATOM_NS + "published") or node.findtext(ATOM_NS + "updated"))})
    return entries


def make_story(title, link, source, summary, pub, default_stage, base_score, confidence, confidence_class):
    result = classify(title, summary, default_stage)
    if not result:
        return None
    stage, topic, relevance = result
    age_hours = max(0, (NOW_UTC - pub.astimezone(datetime.timezone.utc)).total_seconds() / 3600) if pub else 24
    return {
        "title": clean_html(title, 170), "link": link, "source": source, "signals": [source],
        "category": stage, "topic": topic,
        "published": pub.astimezone(TZ).strftime("%m-%d %H:%M") if pub else "",
        "ts": int(pub.timestamp()) if pub else int(NOW_UTC.timestamp()),
        "summary": extract_summary(summary) or clean_html(title, 200),
        "why": make_why(stage, topic, title, summary), "confidence": confidence,
        "confidence_class": confidence_class,
        "score": round(base_score + relevance * 5 + max(0, 8 - age_hours / 3), 2),
        "relevance": relevance,
    }


def merge_story(collection, incoming):
    if not incoming:
        return
    for current in collection:
        if is_similar(current["title"], incoming["title"]):
            if incoming["source"] not in current["signals"]:
                current["signals"].append(incoming["source"])
                current["score"] += 5
            return
    collection.append(incoming)


def hot_candidates():
    raw_candidates = []
    text = fetch_bytes(HOT_ENDPOINTS["百度热搜"]).decode("utf-8", errors="ignore")
    match = re.search(r"<!--s-data:(.*?)-->", text, re.S)
    if match:
        payload = json.loads(match.group(1))
        cards = payload.get("data", {}).get("cards", [])
        content = next((card.get("content", []) for card in cards if card.get("component") == "hotList"), [])
        raw_candidates.extend(("百度热搜", clean_html(x.get("query")), x.get("desc") or x.get("query"), x.get("url") or HOT_ENDPOINTS["百度热搜"], NOW_UTC) for x in content[:25])
    payload = json.loads(fetch_bytes(HOT_ENDPOINTS["头条热榜"]))
    raw_candidates.extend(("头条热榜", clean_html(x.get("Title")), x.get("Title"), x.get("Url") or "https://www.toutiao.com/", NOW_UTC) for x in payload.get("data", [])[:25])
    payload = json.loads(fetch_bytes(HOT_ENDPOINTS["B站热门"]))
    for x in payload.get("data", {}).get("list", [])[:30]:
        pub = datetime.datetime.fromtimestamp(x.get("pubdate", int(NOW_UTC.timestamp())), datetime.timezone.utc)
        raw_candidates.append(("B站热门", clean_html(x.get("title")), x.get("desc") or x.get("title"), f"https://www.bilibili.com/video/{x.get('bvid', '')}", pub))
    accepted = []
    for source, title, summary, link, pub in raw_candidates:
        merge_story(accepted, make_story(title, link, source, summary, pub, "孵化与转化", 38, "兴趣线索", "signal"))
    return accepted


def select_balanced(items):
    stage_caps = {stage: 4 for stage in CATEGORY_ORDER}
    topic_caps = {"AI模型": 6, "网页小游戏": 4, "编程工具": 4, "数学物理": 4, "数据空间": 3, "四川生活": 2}
    source_counts, topic_counts = {}, {}
    stage_counts, selected = {stage: 0 for stage in CATEGORY_ORDER}, []
    ordered = sorted(items, key=lambda value: (value["score"], value["ts"]), reverse=True)

    def can_add(item):
        source, stage, topic = item["source"], item["category"], item["topic"]
        source_cap = 4 if item["confidence_class"] != "signal" else 2
        return not (source_counts.get(source, 0) >= source_cap or stage_counts[stage] >= stage_caps[stage]
                    or topic_counts.get(topic, 0) >= topic_caps.get(topic, 3))

    def add(item):
        source, stage, topic = item["source"], item["category"], item["topic"]
        selected.append(item)
        source_counts[source] = source_counts.get(source, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        stage_counts[stage] += 1

    # 先让信息流的每个阶段各有一条，再按个人相关度补足。
    for stage in CATEGORY_ORDER:
        candidate = next((item for item in ordered if item["category"] == stage and can_add(item)), None)
        if candidate:
            add(candidate)

    for item in ordered:
        if item in selected or not can_add(item):
            continue
        add(item)
        if len(selected) >= MAX_ITEMS_TOTAL:
            break
    return selected


def main():
    today = NOW_UTC.astimezone(TZ).strftime("%Y-%m-%d")
    output = DATA_DIR / f"news_{today}.json"
    if output.exists() and os.environ.get("FORCE_REFRESH") != "1":
        print(f"{output.name} 已存在，作为历史快照保留；如需本地重抓请设置 FORCE_REFRESH=1")
        return

    results, source_stats = [], {}
    try:
        hot = hot_candidates()
        for item in hot:
            merge_story(results, item)
        source_stats["个人兴趣热榜筛选"] = {"status": "成功", "count": len(hot), "type": "兴趣线索"}
        print(f"[兴趣热榜] 通过过滤 {len(hot)} 条")
    except Exception as exc:
        source_stats["个人兴趣热榜筛选"] = {"status": "失败", "count": 0, "error": str(exc)[:120], "type": "兴趣线索"}
        print(f"[失败] 兴趣热榜: {exc}")

    for source, (url, default_stage) in NEWS_FEEDS.items():
        try:
            raw_items = parse_feed(url)
        except Exception as exc:
            source_stats[source] = {"status": "失败", "count": 0, "error": str(exc)[:120], "type": "专业来源"}
            print(f"[失败] {source}: {exc}")
            continue
        accepted = 0
        confidence, confidence_class, base_score = SOURCE_CONFIDENCE[source]
        for raw in raw_items:
            title = clean_html(raw["title"], 170)
            if not title or not raw["link"] or not has_chinese(title):
                continue
            pub = raw["pub"] or NOW_UTC
            max_age = SOURCE_MAX_AGE.get(source, MAX_AGE_HOURS)
            if NOW_UTC - pub.astimezone(datetime.timezone.utc) > datetime.timedelta(hours=max_age):
                continue
            item = make_story(title, raw["link"], source, extract_summary(raw["desc"]) or title,
                              pub, default_stage, base_score, confidence, confidence_class)
            if item:
                merge_story(results, item)
                accepted += 1
            if accepted >= MAX_ITEMS_PER_FEED:
                break
        source_stats[source] = {"status": "成功", "count": accepted, "type": "专业来源"}
        print(f"[专业来源] {source}: 通过过滤 {accepted} 条")

    selected = select_balanced(results)
    payload = {
        "date": today, "generated_at": datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %z"),
        "total": len(selected), "method": "个人兴趣过滤 + 项目阶段归纳 + 免费规则整理（未使用 AI）",
        "categories": CATEGORY_ORDER, "sources": source_stats, "items": selected,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n共筛出 {len(selected)} 条，已保存 -> {output}")
    if not selected:
        raise SystemExit("今日没有符合个人兴趣的内容")


if __name__ == "__main__":
    main()
