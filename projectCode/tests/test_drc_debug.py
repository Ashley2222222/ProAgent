# -*- coding: utf-8 -*-
import sys
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = "https://drc.gd.gov.cn/ywtz/index.html"

print(f"调试: {url}")
print("="*60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until='commit', timeout=20000)
    page.wait_for_timeout(2000)
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "html.parser")

# 查找内容区的li
content_div = soup.find("div", class_=lambda x: x and any(k in str(x) for k in ["content", "main", "list", "news"]))
if content_div:
    items = content_div.find_all("li")
    print(f"找到 {len(items)} 个li\n")
    
    for i, item in enumerate(items[:10], 1):
        a = item.find("a", href=True)
        if a:
            title = a.get_text(strip=True)
            print(f"[{i}] {title}")
            
            # 检查关键词匹配
            keywords = ["申报", "征集", "申请", "推荐", "遴选", "课题", "项目", "基金", "指南", "专项", "计划"]
            exclude_keywords = ["公示", "结果", "评审结果", "批复", "核准", "培训", "会议", "补贴", "补助"]
            
            has_kw = any(w in title for w in keywords)
            has_ex = any(w in title for w in exclude_keywords)
            
            print(f"    有关键词: {has_kw}, 有排除词: {has_ex}, 通过: {has_kw and not has_ex}")
