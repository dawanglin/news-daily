#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动采集商业观察素材，生成当天 data/business_YYYY-MM-DD.json。
- 若当天文件已存在（人工整理优先）则跳过，不覆盖。
- 来源：arXiv（空间智能/3DGS/GeoAI 新论文）、高德开放平台公告、MCP 官方规范、PostGIS 新闻。
- 自动采集条目 verify_status=待核实；人工整理条目保持已查证。
- 单源失败不影响其他源；整体失败不影响新闻发布（workflow 内容错）。
"""
import datetime, json, os, re, ssl, sys, urllib.parse, urllib.request
from html import unescape

UA = {"User-Agent": "Mozilla/5.0 (compatible; doubao-news-daily/1.0)"}
TZ_OFFSET = datetime.timedelta(hours=8)  # Asia/Shanghai
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def http_get(url, timeout=25):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read().decode("utf-8", "ignore")


def clean(s):
    if not s:
        return ""
    return re.sub(r"\s+", " ", unescape(s)).strip()


def fetch_arxiv(limit=12):
    """arXiv 近 7 天与空间智能/GeoAI/MCP 相关论文"""
    q = 'all:"3D Gaussian Splatting" OR all:"spatial intelligence" OR all:"geospatial" OR all:"visual grounding" OR all:"POI matching" OR all:"entity resolution" OR all:"street view"'
    url = ("http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q)
           + "&sortBy=submittedDate&sortOrder=descending&max_results=" + str(limit))
    xml = http_get(url)
    items, now = [], datetime.datetime.now(datetime.timezone.utc).date()
    for m in re.finditer(r"<entry>(.*?)</entry>", xml, re.S):
        e = m.group(1)
        t = re.search(r"<title>(.*?)</title>", e, re.S)
        i = re.search(r"<id>(.*?)</id>", e, re.S)
        p = re.search(r"<published>(.*?)</published>", e, re.S)
        if not (t and i and p):
            continue
        pub = clean(p.group(1))[:10]
        try:
            pub_d = datetime.date.fromisoformat(pub)
        except ValueError:
            continue
        if (now - pub_d).days > 7:
            continue
        items.append({
            "title": clean(t.group(1))[:120],
            "source_name": "arXiv（论文）",
            "source_url": clean(i.group(1)),
            "published_at": pub,
            "scenario": "arXiv 新论文（空间智能/GIS 方向），标题与摘要需人工复核后收录。",
            "verify_status": "待核实",
        })
    return items


def fetch_amap_news(limit=6):
    """高德开放平台公告中心（官方动态，高德仅保留少量）"""
    html = http_get("https://lbs.amap.com/news")
    items, now = [], datetime.datetime.now(datetime.timezone.utc).date()
    # 公告列表常见结构：日期 + 标题
    for m in re.finditer(r"(20\d\d)[-/年](\d{1,2})[-/月](\d{1,2})[日]?[^<]{0,60}?<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>([^<]{6,80})</a>", html):
        y, mo, d, href, title = m.groups()
        try:
            pub_d = datetime.date(int(y), int(mo), int(d))
        except ValueError:
            continue
        if (now - pub_d).days > 7:
            continue
        if not href.startswith("http"):
            href = "https://lbs.amap.com" + href
        items.append({
            "title": clean(title),
            "source_name": "高德开放平台 · 公告中心",
            "source_url": href,
            "published_at": f"{y}-{int(mo):02d}-{int(d):02d}",
            "scenario": "高德官方公告，关注与 MCP/API/位置服务相关的条款与能力调整。",
            "verify_status": "待核实",
        })
        if len(items) >= limit:
            break
    return items


def fetch_mcp_spec():
    """MCP 官方规范 changelog 最新条目"""
    items = []
    try:
        html = http_get("https://modelcontextprotocol.io/specification/2026-07-28/changelog")
        for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", html, re.S):
            title = clean(m.group(1))
            if title:
                items.append({
                    "title": "MCP 规范更新：" + title[:80],
                    "source_name": "Model Context Protocol 官方",
                    "source_url": "https://modelcontextprotocol.io/specification/2026-07-28/changelog",
                    "published_at": "",
                    "scenario": "MCP 官方规范 changelog，协议级变更对所有 MCP 服务端实现有影响。",
                    "verify_status": "待核实",
                })
            if len(items) >= 2:
                break
    except Exception:
        pass
    return items


def fetch_postgis_news(limit=4):
    """PostGIS 官方新闻"""
    items = []
    try:
        html = http_get("https://postgis.net/news/")
        for m in re.finditer(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>\s*([^<]{8,90})\s*</a>", html):
            href, title = m.group(1), clean(m.group(2))
            if not href.startswith("http"):
                href = "https://postgis.net" + href
            items.append({
                "title": "PostGIS：" + title[:80],
                "source_name": "PostGIS 官方",
                "source_url": href,
                "published_at": "",
                "scenario": "PostGIS 版本与功能更新，空间数据库底座跟踪。",
                "verify_status": "待核实",
            })
            if len(items) >= limit:
                break
    except Exception:
        pass
    return items


def main():
    today = (datetime.datetime.now(datetime.timezone.utc) + TZ_OFFSET).date()
    out_file = os.path.join(OUT, "business_%s.json" % today.isoformat())
    if os.path.exists(out_file):
        print("已存在，跳过自动生成:", out_file)
        return
    items = []
    for name, fn in [("arXiv", fetch_arxiv), ("高德公告", fetch_amap_news),
                     ("MCP官方", fetch_mcp_spec), ("PostGIS", fetch_postgis_news)]:
        try:
            got = fn()
            print("%s: %d 条" % (name, len(got)))
            items.extend(got)
        except Exception as e:
            print("%s: 失败 %s" % (name, e))
    if not items:
        print("无可用素材，不生成文件")
        return
    os.makedirs(OUT, exist_ok=True)
    json.dump({"date": today.isoformat(), "items": items}, open(out_file, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("已生成:", out_file, "共", len(items), "条（全部为待核实，需人工复核）")


if __name__ == "__main__":
    main()
