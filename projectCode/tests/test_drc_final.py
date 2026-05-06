# -*- coding: utf-8 -*-
import sys
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = "https://drc.gd.gov.cn/ywtz/index.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until='commit', timeout=20000)
    page.wait_for_timeout(2000)
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "html.parser")

print("分析所有符合条件的ul:")
print("="*60)

all_uls = soup.find_all("ul")
keywords = ["申报", "征集", "申请", "推荐", "遴选", "课题", "项目", "基金", "指南", "专项", "计划"]
exclude_keywords = ["公示", "结果", "评审结果", "批复", "核准", "培训", "会议", "补贴", "补助"]

for idx, ul in enumerate(all_uls):
    lis = ul.find_all("li")
    content_count = 0
    for li in lis[:5]:
        a = li.find("a")
        if a and len(a.get_text(strip=True)) > 20:
            content_count += 1
    
    if content_count >= 2:
        print(f"\nul[{idx}]: {len(lis)} 个li")
        for li in lis:
            a = li.find("a")
            if a:
                title = a.get_text(strip=True)
                if len(title) > 10:
                    has_kw = any(w in title for w in keywords)
                    has_ex = any(w in title for w in exclude_keywords)
                    status = "✓" if (has_kw and not has_ex) else "✗"
                    print(f"  [{status}] {title[:55]}...")
