"""每日新闻速览配置。所有敏感信息只从环境变量读取。"""

import os

SITE_TITLE = "每日新闻速览"
SITE_SUBTITLE = "科技互联网 · 综合热点"
MAX_ITEMS_PER_FEED = 8
MAX_ITEMS_TOTAL = 40
REQUEST_TIMEOUT = 20

# 名称: (RSS / Atom 地址, 分类)
NEWS_FEEDS = {
    "少数派": ("https://sspai.com/feed", "科技互联网"),
    "Solidot": ("https://www.solidot.org/index.rss", "科技互联网"),
    "IT之家": ("https://www.ithome.com/rss/", "科技互联网"),
    "TechCrunch": ("https://techcrunch.com/feed/", "科技互联网"),
    "The Verge": ("https://www.theverge.com/rss/index.xml", "科技互联网"),
    "Ars Technica": ("https://feeds.arstechnica.com/arstechnica/index", "科技互联网"),
    "Hacker News": ("https://hnrss.org/frontpage", "科技互联网"),
    "GitHub Blog": ("https://github.blog/feed/", "科技互联网"),
    "BBC 中文": ("https://feeds.bbci.co.uk/zhongwen/simp/rss.xml", "综合热点"),
    "BBC World": ("https://feeds.bbci.co.uk/news/world/rss.xml", "综合热点"),
    "NPR World": ("https://feeds.npr.org/1004/rss.xml", "综合热点"),
}

AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_API_BASE = os.getenv("AI_API_BASE", "https://api.deepseek.com/v1").rstrip("/")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")
