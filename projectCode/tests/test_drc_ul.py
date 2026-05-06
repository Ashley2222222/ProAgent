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

print("所有ul分析:")
print("="*60)

uls = soup.find_all("ul")
for i, ul in enumerate(uls):
    lis = ul.find_all("li")
    if len(lis) > 0:
        # 获取第一个li的文本
        first_text = ""
        first_a = lis[0].find("a")
        if first_a:
            first_text = first_a.get_text(strip=True)
        
        # 检查是否是内容列表（有较长文本的链接）
        has_content = False
        for li in lis[:3]:
            a = li.find("a")
            if a and len(a.get_text(strip=True)) > 20:
                has_content = True
                break
        
        print(f"\nul[{i}]: {len(lis)} 个li")
        print(f"  首项: {first_text[:40] if first_text else '(无文本)'}")
        print(f"  有内容: {has_content}")
        
        if has_content and len(lis) > 3:
            print(f"  内容示例:")
            for li in lis[:3]:
                a = li.find("a")
                if a:
                    print(f"    - {a.get_text(strip=True)[:50]}...")
