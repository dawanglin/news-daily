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

from config import (EXTRACT_SENTENCES, FETCH_TIMEOUT, MAX_AGE_HOURS,
                    MAX_ITEMS_PER_FEED, MAX_ITEMS_TOTAL, NEWS_FEEDS,
                    TZ_OFFSET_HOURS)

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

TOPIC_KEYWORDS = {
    "云服务器": "云服务器 云主机 VPS Serverless 容器 Docker Kubernetes 部署 运维 域名 CDN 托管 云计算 数据中心 阿里云 腾讯云 华为云 AWS Azure".split(),
    "AI模型": "AI 人工智能 大模型 模型 OpenAI Claude Anthropic DeepSeek Gemini GPT 推理 多模态 RAG MCP token 智谱 通义 Kimi 豆包 Llama".split(),
    "提示词": "提示词 Prompt 上下文 system prompt 提示工程 越狱 指令 模板".split(),
    "Agent": "Agent 智能体 代理 多智能体 工作流 MCP function calling 工具调用 记忆 规划 自主执行".split(),
    "Skill与插件": "Skill 技能 插件 plugin extension 应用商店 marketplace connector 连接器 浏览器插件".split(),
    "网页小游戏": "网页 前端 HTML CSS JavaScript TypeScript WebGL Canvas Three.js 浏览器 小游戏 游戏开发 像素 Unity Godot Phaser React Vue Svelte 小程序".split(),
    "编程工具": "编程 代码 开源 GitHub 软件 开发者 API SDK IDE 数据库 Python Rust Go Java Docker Linux 自动化 插件 框架".split(),
    "数学物理": "数学 物理 定理 猜想 几何 概率 统计 算法 量子 粒子 材料 天文 宇宙 科学家 证明 方程 理论 实验 分子 原子 晶体 导电 磁场 光学 声学 能量 同素异形体 神经系统".split(),
    "数据空间": "数据科学 可视化 地图 地理 空间 GIS 遥感 坐标 图谱 网络 关系 因果 预测 不确定性 模糊 聚类 时序 拓扑 数字孪生 知识图谱".split(),
    "四川生活": "四川 成都 重庆 西南 本地 天气 地震 交通 地铁 高铁 政务 医保 教育 住房 数字生活".split(),
}

LENS_KEYWORDS = {
    "实测评价": "实测 体验 评测 测评 对比 踩坑 好用 难用 值得 推荐 评价 反馈 吐槽 试用 稳定 价格 成本".split(),
    "教程方法": "教程 指南 入门 上手 如何 步骤 实践 实现 构建 部署 配置 安装 训练 微调 工作流 方法".split(),
    "专家观点": "专家 访谈 观点 演讲 教授 博士 研究员 创始人 开发者 作者 团队 负责人 解读".split(),
    "案例复盘": "案例 复盘 故障 事故 迁移 优化 维护 漏洞 安全 隐私 争议 边界 版权 许可证".split(),
    "工具发布": "发布 上线 更新 版本 开源 工具 软件 插件 框架 库 SDK API IDE 平台".split(),
    "概念科普": "概念 原理 科普 理论 研究 论文 定理 猜想 发现 解释 为什么".split(),
}

# 默认排除政治外交、战争、泛国际冲突和纯娱乐体育。
HARD_NEGATIVE = "习近平 特朗普 总统 首相 外交 联合国 北约 乌克兰 俄罗斯 伊朗 以色列 沙特 军事 战争 冲突 制裁 关税 峰会 会晤 国事访问 中美关系 国际局势 亚运 奥运 冠军 明星 演唱会 3A大作 3A 大作 高级技术动画师 游戏招聘 丹麦人口数据库".split()
LOCAL_STRONG = "四川 成都 重庆 西南".split()
LOW_VALUE = "财报 手机发布 新车上市 新车 车型 万元起 续航 交付 售价 开售 促销 爆料 传闻 接待 活动 迷你电脑 准系统".split()
CLICKBAIT = "闯大祸 离谱 炸裂 杀疯了 震惊 惊呆 失控 猛料 神器 梅西终结者 夯爆了 卷疯了 啥题啊 能干崩".split()

SOURCE_MAX_AGE = {
    "科学网·数理科学": 240,
    "科学网·科普": 168,
    "前端技术精选": 192,
    "阮一峰的网络日志": 336,
    "小众软件": 240,
    "V2EX·技术": 120,
    "V2EX·创造": 120,
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
    "小众软件": ("工具体验来源", "professional", 72),
    "V2EX·技术": ("用户讨论线索", "signal", 58),
    "V2EX·创造": ("用户作品线索", "signal", 60),
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


def classify(title, summary, default_lens):
    text = f"{title} {summary}"
    if any(word in text for word in HARD_NEGATIVE) and not any(word in text for word in LOCAL_STRONG):
        return None
    if any(word in title for word in CLICKBAIT):
        return None
    topic_scores = {name: keyword_score(text, words, title) for name, words in TOPIC_KEYWORDS.items()}
    title_lower = title.lower()
    if any(word in title_lower for word in ("skill", "插件", "plugin", "connector", "连接器")):
        topic_scores["Skill与插件"] += 7
    if any(word in title_lower for word in ("prompt", "提示词", "提示工程")):
        topic_scores["提示词"] += 7
    if any(word in title_lower for word in ("agent", "智能体", "多智能体")):
        topic_scores["Agent"] += 6
    if any(word in title_lower for word in ("云服务器", "云主机", "vps", "serverless", "数据中心")):
        topic_scores["云服务器"] += 6
    topic = max(topic_scores, key=topic_scores.get)
    relevance = topic_scores[topic]
    if relevance < 2:
        return None
    lens_scores = {name: keyword_score(text, words, title) for name, words in LENS_KEYWORDS.items()}
    lens = max(lens_scores, key=lens_scores.get)
    if lens_scores[lens] == 0:
        lens = default_lens
    relevance -= sum(2 for word in LOW_VALUE if word in text)
    if topic in {"AI模型", "提示词", "Agent", "Skill与插件", "云服务器", "网页小游戏", "数据空间"}:
        relevance += 3
    if relevance < 3:
        return None
    return lens, topic, relevance


def make_why(lens, topic, title, summary):
    text = f"{title} {summary}".lower()
    if lens == "实测评价":
        action = "把它当作真实使用信号，重点核对测试条件、评论分歧和长期成本。"
    elif lens == "教程方法":
        action = "抽出最小可复现步骤，亲手做一遍，再记录卡点。"
    elif lens == "专家观点":
        action = "分开看结论、证据和预测，再和自己的实际使用对照。"
    elif lens == "案例复盘":
        action = "保存失败条件和解决办法，遇到同类问题时可直接查。"
    elif lens == "工具发布":
        action = "先确认权限、价格和维护状态，再决定是否安装或接入。"
    else:
        action = "先弄清核心概念和适用边界，再找一个小例子验证。"
    if topic == "云服务器":
        return "比较部署难度、月度成本和数据位置，优先试最小可运行方案。" + action
    if topic == "AI模型":
        return "比较能力、价格、上下文和本地运行门槛，不只看榜单。" + action
    if topic == "提示词":
        return "保存可复用的提示结构，用同一输入做一次前后对比。" + action
    if topic == "Agent":
        return "看清它调用了哪些工具、怎样记忆和规划，复现其中一条执行链。" + action
    if topic == "Skill与插件":
        return "确认它解决哪一步、需要哪些权限，以及停止维护后能否替换。" + action
    if topic == "网页小游戏":
        return "可拆出一个界面、交互或游戏机制。" + action
    if topic == "数据空间":
        return "可练习把位置、数据和模糊关系连接起来。" + action
    if any(word in text for word in ("破解", "安全", "漏洞", "隐私")):
        return "它触及你正在使用的软件和代码边界。" + action
    return action


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


def make_story(title, link, source, summary, pub, default_lens, base_score, confidence, confidence_class):
    result = classify(title, summary, default_lens)
    if not result:
        return None
    lens, topic, relevance = result
    age_hours = max(0, (NOW_UTC - pub.astimezone(datetime.timezone.utc)).total_seconds() / 3600) if pub else 24
    return {
        "title": clean_html(title, 170), "link": link, "source": source, "signals": [source],
        "category": "今日信息流", "topic": topic, "lens": lens,
        "published": pub.astimezone(TZ).strftime("%m-%d %H:%M") if pub else "",
        "ts": int(pub.timestamp()) if pub else int(NOW_UTC.timestamp()),
        "summary": extract_summary(summary) or clean_html(title, 200),
        "why": make_why(lens, topic, title, summary), "confidence": confidence,
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
        merge_story(accepted, make_story(title, link, source, summary, pub, "用户讨论", 38, "兴趣线索", "signal"))
    return accepted


def select_balanced(items):
    topic_caps = {"AI模型": 6, "Agent": 5, "Skill与插件": 5, "提示词": 3, "云服务器": 4,
                  "网页小游戏": 4, "编程工具": 5, "数学物理": 4, "数据空间": 3, "四川生活": 2}
    source_counts, topic_counts = {}, {}
    selected = []
    ordered = sorted(items, key=lambda value: (value["score"], value["ts"]), reverse=True)

    def can_add(item):
        source, topic = item["source"], item["topic"]
        source_cap = 4 if item["confidence_class"] != "signal" else 3
        return not (source_counts.get(source, 0) >= source_cap
                    or topic_counts.get(topic, 0) >= topic_caps.get(topic, 3))

    def add(item):
        source, topic = item["source"], item["topic"]
        selected.append(item)
        source_counts[source] = source_counts.get(source, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    # 先保留用户最关心方向中的高分内容，再按相关度补足。
    priority_topics = ["AI模型", "Agent", "Skill与插件", "云服务器", "提示词", "网页小游戏", "数学物理", "数据空间"]
    for topic in priority_topics:
        candidate = next((item for item in ordered if item["topic"] == topic and can_add(item)), None)
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
    now_local = NOW_UTC.astimezone(TZ)
    not_before_hour = int(os.environ.get("NOT_BEFORE_HOUR", "0"))
    if now_local.hour < not_before_hour:
        print(f"北京时间尚未到 {not_before_hour:02d}:00，本次仅巡检，不生成快照")
        return

    today = now_local.strftime("%Y-%m-%d")
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
            summary = extract_summary(raw["desc"]) or title
            if summary in {"点击查看原文>", "点击查看原文", "查看原文>"}:
                summary = title
            item = make_story(title, raw["link"], source, summary,
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
        "total": len(selected), "method": "个人兴趣过滤 + 用途提示 + 免费规则整理（未使用 AI）",
        "sources": source_stats, "items": selected,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n共筛出 {len(selected)} 条，已保存 -> {output}")
    if not selected:
        raise SystemExit("今日没有符合个人兴趣的内容")


if __name__ == "__main__":
    main()
