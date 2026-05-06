# -*- coding: utf-8 -*-
import sys
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from crawlers import GDDRCrawler

crawler = GDDRCrawler("https://drc.gd.gov.cn")

# 测试两个新栏目
urls = [
    ("公告公示", "https://drc.gd.gov.cn/gggs5623/index.html"),
    ("业务通知", "https://drc.gd.gov.cn/ywtz/index.html"),
]

for name, url in urls:
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"URL: {url}")
    print("-"*60)
    
    notices = crawler.fetch_notice_list(url, max_pages=1)
    print(f"\n找到 {len(notices)} 条通知")
    for i, n in enumerate(notices[:5], 1):
        print(f"\n[{i}] {n['标题'][:60]}...")

print("\n\n测试完成!")
