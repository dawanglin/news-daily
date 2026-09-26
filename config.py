# -*- coding: utf-8 -*-
"""个人情报流配置：围绕从想法到维护的完整动手过程。"""

NEWS_FEEDS = {
    "量子位": ("https://www.qbitai.com/feed", "想法与概念"),
    "机器之心": ("https://wechat2rss.bestblogs.dev/feed/8d97af31b0de9e48da74558af128a4673d78c9a3.xml", "想法与概念"),
    "InfoQ 中文": ("https://www.infoq.cn/feed", "方法与执行"),
    "开源中国": ("https://www.oschina.net/news/rss", "工具与硬件"),
    "少数派": ("https://sspai.com/feed", "工具与硬件"),
    "IT之家": ("https://www.ithome.com/rss/", "工具与硬件"),
    "Solidot": ("https://www.solidot.org/index.rss", "想法与概念"),
    "科学网·数理科学": ("https://www.sciencenet.cn/xml/paper.aspx?di=7", "测试与成果"),
    "科学网·科普": ("https://www.sciencenet.cn/xml/blog.aspx?di=7", "想法与概念"),
    "前端技术精选": ("https://fed.chanceyu.com/atom.xml", "方法与执行"),
    "阮一峰的网络日志": ("https://www.ruanyifeng.com/blog/atom.xml", "方法与执行"),
}

CATEGORY_ORDER = [
    "行业观察",
    "想法与概念",
    "孵化与转化",
    "工具与硬件",
    "方法与执行",
    "测试与成果",
    "维护与复盘",
]

CATEGORY_HINTS = {
    "行业观察": "观察与你方向有关的公司、产品和开源生态变化。",
    "想法与概念": "先提炼它的新概念，以及它改变了哪个旧认识。",
    "孵化与转化": "判断这个想法能否缩成一个小项目、网页或实验。",
    "工具与硬件": "看它能否成为你的新工具，或降低动手门槛。",
    "方法与执行": "抽取可照着做的步骤、工作流和实现方法。",
    "测试与成果": "查看它怎样验证效果，结果是否经得起复现。",
    "维护与复盘": "留意长期使用中的成本、边界、故障和维护经验。",
}

MAX_ITEMS_PER_FEED = 18
MAX_ITEMS_TOTAL = 18
MUST_READ_COUNT = 6
MAX_AGE_HOURS = 72
EXTRACT_SENTENCES = 2
FETCH_TIMEOUT = 18
TZ_OFFSET_HOURS = 8
