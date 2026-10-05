# -*- coding: utf-8 -*-
"""个人情报流配置：围绕能理解、能试用、能落地的信息。"""

NEWS_FEEDS = {
    "量子位": ("https://www.qbitai.com/feed", "专业报道"),
    "机器之心": ("https://wechat2rss.bestblogs.dev/feed/8d97af31b0de9e48da74558af128a4673d78c9a3.xml", "专业报道"),
    "InfoQ 中文": ("https://www.infoq.cn/feed", "技术实践"),
    "开源中国": ("https://www.oschina.net/news/rss", "工具发布"),
    "少数派": ("https://sspai.com/feed", "使用体验"),
    "小众软件": ("https://feed.appinn.com", "使用体验"),
    "IT之家": ("https://www.ithome.com/rss/", "科技资讯"),
    "Solidot": ("https://www.solidot.org/index.rss", "社区观察"),
    "科学网·数理科学": ("https://www.sciencenet.cn/xml/paper.aspx?di=7", "研究成果"),
    "科学网·科普": ("https://www.sciencenet.cn/xml/blog.aspx?di=7", "概念科普"),
    "前端技术精选": ("https://fed.chanceyu.com/atom.xml", "技术实践"),
    "阮一峰的网络日志": ("https://www.ruanyifeng.com/blog/atom.xml", "技术实践"),
    "V2EX·技术": ("https://www.v2ex.com/feed/tab/tech.xml", "用户讨论"),
    "V2EX·创造": ("https://www.v2ex.com/feed/tab/creative.xml", "用户作品"),
}

MAX_ITEMS_PER_FEED = 18
MAX_ITEMS_TOTAL = 26
MAX_AGE_HOURS = 72
EXTRACT_SENTENCES = 2
FETCH_TIMEOUT = 18
TZ_OFFSET_HOURS = 8
