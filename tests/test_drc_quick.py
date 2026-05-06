# -*- coding: utf-8 -*-
import sys
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from crawlers import GDDRCrawler

crawler = GDDRCrawler("https://drc.gd.gov.cn")

print("测试广东省发改委爬虫...")
print("=" * 60)

list_url = "https://drc.gd.gov.cn/gkmlpt/index"
notices = crawler.fetch_notice_list(list_url, max_pages=1)

print(f"\n找到 {len(notices)} 条通知")
for i, n in enumerate(notices[:3], 1):
    print(f"\n[{i}] {n['标题'][:50]}...")
    print(f"    日期: {n.get('发布日期', '未知')}")
    print(f"    链接: {n['链接'][:60]}...")

print("\n测试完成!")
