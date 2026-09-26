# -*- coding: utf-8 -*-
"""每日简报配置：中文来源、栏目、数量与免费规则。"""

# RSS 来源只承担事实与专业内容；公共热榜由 fetch_news.py 单独抓取。
NEWS_FEEDS = {
    "中国新闻网": ("https://www.chinanews.com.cn/rss/scroll-news.xml", "社会与民生"),
    "BBC 中文": ("https://feeds.bbci.co.uk/zhongwen/simp/rss.xml", "世界与中国"),
    "少数派": ("https://sspai.com/feed", "工作与科技"),
    "IT之家": ("https://www.ithome.com/rss/", "工作与科技"),
    "Solidot": ("https://www.solidot.org/index.rss", "工作与科技"),
    "量子位": ("https://www.qbitai.com/feed", "工作与科技"),
}

CATEGORY_ORDER = [
    "今日热议",
    "社会与民生",
    "钱包与消费",
    "吃喝住行",
    "健康教育家庭",
    "工作与科技",
    "文娱与体育",
    "世界与中国",
]

CATEGORY_HINTS = {
    "健康教育家庭": "留意健康、教育、养老、育儿或家庭生活中的实际影响。",
    "钱包与消费": "留意它对价格、收入、资产安全或消费选择的影响。",
    "吃喝住行": "它与饮食、住房、交通、旅行或城市生活直接相关。",
    "文娱与体育": "它正在影响大众文化、休闲选择或公共讨论。",
    "工作与科技": "重点不是参数，而是它会怎样改变工作方法和日常工具。",
    "世界与中国": "关注外部变化对中国用户、市场和出行可能带来的影响。",
    "社会与民生": "关注公共服务、社会规则以及普通人的真实处境。",
    "今日热议": "这是公共平台上的热度线索；事实细节仍需结合可靠报道判断。",
}

MAX_ITEMS_PER_FEED = 12
MAX_ITEMS_TOTAL = 28
MUST_READ_COUNT = 8
MAX_AGE_HOURS = 48
EXTRACT_SENTENCES = 2
FETCH_TIMEOUT = 18
TZ_OFFSET_HOURS = 8
