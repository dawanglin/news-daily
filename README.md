# 每日新闻速览

每天自动抓取科技互联网与综合热点新闻，生成中文摘要和静态网页，并通过 GitHub Pages 发布。

在线地址：<https://dawanglin.github.io/news-daily/>

## 特点

- 纯 Python 标准库，零第三方依赖
- RSS / Atom 多源抓取；单个来源失败不影响其他来源
- 自动去重、清洗、按日期归档
- GitHub Actions 每天北京时间 08:00 自动运行
- 可选 OpenAI 兼容接口生成“今日要闻综述”

## 本地运行

```bash
python fetch_news.py
python summarize.py
python build_site.py
```

然后用浏览器打开 `site/index.html`。

## 配置

新闻源、分类及数量都在 `config.py`。启用 AI 综述时，在仓库 Settings → Secrets and variables → Actions 中添加：

- `AI_API_KEY`：必填
- `AI_API_BASE`：可选，默认 `https://api.deepseek.com/v1`
- `AI_MODEL`：可选，默认 `deepseek-chat`

不配置密钥时会自动跳过 AI 综述，不影响新闻页面生成。

## 手动更新

打开仓库的 Actions → Daily News Digest → Run workflow。

> 新闻标题、摘要和链接来自公开 RSS，仅用于信息聚合；内容版权归原作者及来源媒体所有。

