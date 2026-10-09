# 每日新闻 + 生活优惠项目交接

更新时间：2026-10-09（北京时间）

## 项目目标

把每天值得了解的新闻线索和实际能用的生活优惠放到同一个信息入口中，方便手机阅读与分享。两类内容由不同流程生产、保留各自来源和历史，不把优惠伪装成新闻，也不把新闻改成促销信息。

- 新闻主站：[dawanglin.github.io/news-daily](https://dawanglin.github.io/news-daily/)
- 优惠详情站：[dawanglin.github.io/youhui-pages](https://dawanglin.github.io/youhui-pages/)
- 新闻仓库：[dawanglin/news-daily](https://github.com/dawanglin/news-daily)
- 优惠仓库：[dawanglin/youhui-pages](https://github.com/dawanglin/youhui-pages)
- 每日联合交接表：[DAILY_HANDOFF_TABLE.md](DAILY_HANDOFF_TABLE.md)
- 豆包优惠专项交接说明：[优惠仓库 DOUBAO_HANDOFF.md](https://github.com/dawanglin/youhui-pages/blob/master/DOUBAO_HANDOFF.md)
- 豆包优惠字段表：[优惠仓库 DOUBAO_DAILY_HANDOFF_TABLE.md](https://github.com/dawanglin/youhui-pages/blob/master/DOUBAO_DAILY_HANDOFF_TABLE.md)

## 两条内容线

| 内容线 | 负责人/来源 | 目标与方向 | 数据入口 | 发布位置 |
|---|---|---|---|---|
| 每日新闻 | news-daily 自动抓取与规则筛选 | 面向个人兴趣的 AI 模型、云服务、Agent、提示词、Skill/插件、编程与网页小游戏、数学物理、数据空间、四川生活等；每天约 20–30 条，当前程序上限 26 条；不使用 AI 大模型生成摘要 | Actions 生成 `data/news_YYYY-MM-DD.json`，无需人工填报 | 新闻主站；由 Actions 构建和部署 |
| 生活优惠 | 豆包负责搜集整理，维护者/仓库程序负责格式校验与发布 | 中国大陆真实可参与的优惠，五类尽量覆盖，目标 20–30 条；官方规则优先，未知条件不猜 | 豆包提交 `youhui-pages/incoming/YYYY-MM-DD.json` | 优惠详情独立页面；新闻站只提供入口，不混入新闻列表 |

## 新闻更新与验收

- 工作流：`.github/workflows/daily.yml`。计划在北京时间 17:07 至 23:07 每小时巡检一次，并可在 GitHub Actions 手动运行。GitHub 定时任务可能延迟或漏跑，不承诺精确到分钟。
- 新闻抓取完成后，工作流会检查当天 JSON 快照是否存在；缺失时任务报错并停止发布，避免把旧页面误当成今日更新。
- 首页/归档由 `build_site.py` 生成。不要直接编辑已生成的 `site/`、归档页或历史 JSON。
- 当天第一次成功生成的新闻快照保留为历史记录；后续巡检不覆盖当天内容。若当天抓取失败，查看 Actions 中抓取步骤和各来源错误。
- 手动验收：检查 Actions 的抓取、快照检查、生成站点、提交和 Pages 部署步骤；再打开手机新闻网址确认日期和条数。绿色状态本身不够，必须确认生成了当天文件。

## 优惠交接与验收

1. 豆包按优惠专项交接文档整理当天内容，生成 `incoming/YYYY-MM-DD.json`，日期使用北京时间。
2. 必须提供可打开的 HTTPS 来源。金额、门槛、地区、截止日期、领取入口不确定时填 `null`；没有来源链接的记录不提交。
3. 五类场景：外卖、本地生活与餐饮；电商购物；出行、旅游与酒店；会员订阅与综合补贴；信用卡优惠。目标约 20–30 条，不够就不凑数。
4. 推送到优惠仓库 `master` 后，由该仓库 Actions 校验、生成当天页面、保存归档并发布。有效豆包条目是当天主要内容；若没有有效交接条目，程序才退回 RSS 线索。
5. 验收 Actions 成功后，打开优惠站核对日期和数量。历史归档按日保存，只修当天文件，不改往期快照。

## 联合日交接怎么填

使用 [每日联合交接表](DAILY_HANDOFF_TABLE.md) 做汇总。新闻是自动流水线的结果，不需要豆包重新抄写新闻列表；优惠是豆包提交的 JSON，需要逐条整理。每天分别记录两个模块的数据日期、数量、工作流状态、线上验收情况。如果某个模块未更新，写明失败步骤和错误，不以另一个模块成功代替。

## 不做的事

- 不覆盖两个仓库自动生成的首页、模板或工作流来提交每日内容。
- 不为了凑条数收录旧闻、政治国际时事、纯促销报道或已过期优惠。
- 不把媒体线索或豆包标注的“已查证”说成本站已独立核实。
- 不修改过去日期的快照来掩盖漏更；历史缺口应如实标记。
- 不把一次 Actions 成功等同于内容已更新；以当天数据文件、网页日期和部署结果三者确认闭环。
