# 第一步：只爬取 + AI分析 + 控制台输出（小白专用）
import requests
from bs4 import BeautifulSoup
import json
import time

# -- coding: utf-8 --
import sys
import io

# 设置标准输出的编码为UTF-8
if sys.stdout.encoding != "UTF-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from typing import List, Dict, Any

# ===================== 你要监控的网站（已经帮你填好！）=====================
TARGET_URLS = [
    "https://service.most.gov.cn/",  # 国家科技
    "https://www.nsfc.gov.cn/",  # 基金委
    "https://gdstc.gd.gov.cn/",  # 广东科技
    "https://kjj.gz.gov.cn/",  # 广州科技
    "https://www.huadu.gov.cn/gzhdkasx/gkmlot/index",  # 花都
]
# ========================================================================


# 1. 抓取通知标题和链接
def fetch_notices(url):
    print(f"正在抓取：{url}")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        notices = []
        for a_tag in soup.find_all("a"):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href")

            # 只抓含这些关键词的通知
            key_words = ["课题", "申报", "立项", "指南", "项目"]
            if href and any(word in title for word in key_words):
                if not href.startswith("http"):
                    if url.endswith("/"):
                        href = url + href
                    else:
                        href = url + "/" + href
                notices.append({"标题": title, "链接": href})
        return notices[:5]  # 每个网站取最新5条
    except Exception as e:
        print(f"抓取失败：{e}")
        return []


# 2. 模拟AI分析（不用APIKey！直接本地分析）
def simple_analysis(title):
    print("\n" + "=" * 50)
    print(f"【标题】{title}")

    # 自动判断类型
    if "课题" in title or "申报" in title:
        type_result = "科研课题申报"
    elif "立项" in title:
        type_result = "项目立项公示"
    elif "指南" in title:
        type_result = "申报指南发布"
    else:
        type_result = "普通通知"

    print(f"【类型】{type_result}")
    print(f"【状态】可关注 → 适合课题申报")
    print("=" * 50 + "\n")
    return type_result


# ===================== 主程序 =====================
if __name__ == "__main__":
    print("🚀 开始抓取政府课题申报通知...\n")

    all_notices = []
    for url in TARGET_URLS:
        notices = fetch_notices(url)
        all_notices.extend(notices)
        time.sleep(1)

    print(f"\n✅ 抓取完成！共找到 {len(all_notices)} 条通知\n")

    # 输出并分析
    for idx, notice in enumerate(all_notices, 1):
        print(f"\n📌 第 {idx} 条")
        print(f"标题：{notice['标题']}")
        print(f"链接：{notice['链接']}")
        simple_analysis(notice["标题"])

    print("\n🎉 第一步完成！所有通知已在控制台输出！")
