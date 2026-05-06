# -*- coding: utf-8 -*-
import sys
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

headers = {"User-Agent": "Mozilla/5.0"}

# 查看首页导航
url = "https://drc.gd.gov.cn"
print(f"查看: {url}")

try:
    res = requests.get(url, headers=headers, timeout=10, verify=False)
    res.encoding = res.apparent_encoding or "utf-8"
    
    soup = BeautifulSoup(res.text, "html.parser")
    
    # 查找所有链接
    print("\n查找栏目链接:")
    keywords = ["通知", "公告", "申报", "项目", "资金", "专项", "投资", "产业"]
    links = soup.find_all("a", href=True)
    
    found = []
    for link in links:
        text = link.get_text(strip=True)
        if any(kw in text for kw in keywords) and len(text) < 20:
            href = link["href"]
            if href not in [f[2] for f in found]:
                found.append((text, href, link["href"]))
                if len(found) >= 15:
                    break
    
    for text, _, href in found:
        print(f"  - {text}: {href}")
    
except Exception as e:
    print(f"错误: {e}")
