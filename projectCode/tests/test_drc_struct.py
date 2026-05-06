# -*- coding: utf-8 -*-
import sys
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = "https://drc.gd.gov.cn/ywtz/index.html"

print(f"查看: {url}")
print("="*60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until='commit', timeout=20000)
    page.wait_for_timeout(2000)
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "html.parser")

# 查找列表
print("\n查找列表项:")

# 方式1: ul > li
uls = soup.find_all("ul")
print(f"找到 {len(uls)} 个ul")
for i, ul in enumerate(uls[:3]):
    lis = ul.find_all("li")
    if lis:
        print(f"  ul[{i}]: {len(lis)} 个li")
        for li in lis[:2]:
            a = li.find("a")
            if a:
                print(f"    - {a.get_text(strip=True)[:40]}...")

# 方式2: div > a
divs = soup.find_all("div", class_=lambda x: x and any(k in str(x) for k in ["item", "news", "list", "content"]))
print(f"\n找到 {len(divs)} 个可能的内容div")
for div in divs[:3]:
    a = div.find("a")
    if a:
        print(f"  - {a.get_text(strip=True)[:40]}...")

# 方式3: 所有链接
print("\n申报相关链接 (前10个):")
keywords = ["申报", "征集", "项目", "资金", "专项"]
links = soup.find_all("a", href=True)
count = 0
for link in links:
    text = link.get_text(strip=True)
    if any(kw in text for kw in keywords) and 5 < len(text) < 80:
        print(f"  [{count+1}] {text[:60]}...")
        print(f"      href: {link['href']}")
        count += 1
        if count >= 10:
            break
