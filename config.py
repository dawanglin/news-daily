# -*- coding: utf-8 -*-
"""
全局配置：新闻源、抓取数量、AI 总结等。
想改内容就在这个文件里改，不需要动其他代码。
"""

# ============ 新闻源 ============
# 格式： "源名称": ("RSS 地址", "分类")
# 分类目前有两种：科技 / 综合。可以按需增删源或分类。
NEWS_FEEDS = {
    "IT之家":     ("https://www.ithome.com/rss/", "科技"),
    "Solidot":    ("https://www.solidot.org/index.rss", "科技"),
    "少数派":     ("https://sspai.com/feed", "科技"),
    "量子位":     ("https://www.qbitai.com/feed", "科技"),
    "Hacker News": ("https://news.ycombinator.com/rss", "科技"),
    "中国新闻网": ("https://www.chinanews.com.cn/rss/scroll-news.xml", "综合"),
    "BBC 中文":   ("https://feeds.bbci.co.uk/zhongwen/simp/rss.xml", "综合"),
    "BBC World":  ("https://feeds.bbci.co.uk/news/world/rss.xml", "综合"),
}

# ============ 抓取数量 ============
MAX_ITEMS_PER_FEED = 10      # 每个源最多保留多少条
MAX_ITEMS_TOTAL = 40         # 每天总共保留多少条
MAX_AGE_HOURS = 48           # 只保留最近 48 小时内的新闻
EXTRACT_SENTENCES = 3        # 免费抽取式摘要：取正文前几句话
FETCH_TIMEOUT = 15           # 每个源抓取超时（秒）

# ============ AI 总结（可选）============
# 留空则跳过 AI 总结，只使用免费抽取式摘要。
# 线上推荐配置在 GitHub Actions 的 Secrets 里（README 有说明），不要写死在代码里：
#   AI_API_KEY  -> 密钥（DeepSeek / OpenAI 等 OpenAI 兼容接口的 key）
#   AI_API_BASE -> 接口地址，默认 https://api.deepseek.com/v1
#   AI_MODEL    -> 模型名，默认 deepseek-chat
AI_API_KEY = ""
AI_API_BASE = "https://api.deepseek.com/v1"
AI_MODEL = "deepseek-chat"

# ============ 展示时区 ============
# 中国大陆无夏令时，固定 UTC+8 即可正确计算“今天”。
TZ_OFFSET_HOURS = 8
