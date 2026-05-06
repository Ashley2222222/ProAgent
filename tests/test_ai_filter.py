# -*- coding: utf-8 -*-
"""
测试AI分析过滤功能
验证只有符合要求的通知才会被AI分析
"""
import sys
import io
from urllib3.exceptions import InsecureRequestWarning
import requests

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import time
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试时强制启用AI分析
ENABLE_AI_ANALYSIS = True
AI_ONLY_ANALYZE_VALID = True  # 只对符合要求的通知进行AI分析
MAX_NOTICES_PER_SITE = 2
DATE_RANGE = {
    "start_date": "2025-01-01",
    "end_date": "2026-12-31",
}
OUTPUT_DIR = "data"
RESULT_FILENAME = "test_ai_filter_results.json"

from crawler_factory import ResearchCrawlerFactory

print("=" * 60)
print("AI分析过滤功能测试")
print("=" * 60)
print(f"AI分析模式: 开启")
print(f"只分析符合要求的通知: {AI_ONLY_ANALYZE_VALID}")
print(f"每个网站最多分析: {MAX_NOTICES_PER_SITE} 条通知")
print("=" * 60)

site_configs = ResearchCrawlerFactory.get_all_sites()

# 只测试广东省科技厅
test_sites = ["gdstc.gd.gov.cn"]

all_results = []
ai_analyzed_count = 0
ai_skipped_count = 0

for site_key in test_sites:
    if site_key not in site_configs:
        continue

    config = site_configs[site_key]
    print(f"\n{'='*60}")
    print(f"【网站】{config['description']} - {config['base_url']}")
    print(f"{'='*60}")

    crawler = ResearchCrawlerFactory.create_crawler(site_key)
    list_urls = config.get("list_urls", [])
    if not list_urls:
        print(f"  [WARN] 未配置列表页地址，跳过")
        continue

    all_notices = []
    for list_config in list_urls:
        list_url = list_config["url"]
        list_name = list_config.get("name", "未命名")

        print(f"\n  【列表页】{list_name}")
        print(f"  URL: {list_url}")

        notices = crawler.fetch_notice_list(list_url, max_pages=1)

        if notices:
            print(f"    [OK] 找到 {len(notices)} 条通知")
            all_notices.extend(notices)
        else:
            print(f"    [WARN] 未找到通知")

    notices = all_notices
    print(f"\n  该网站共找到 {len(notices)} 条相关通知")

    if not notices:
        continue

    # 日期过滤
    start_date = DATE_RANGE.get("start_date")
    end_date = DATE_RANGE.get("end_date")

    if start_date or end_date:
        date_range_str = f"{start_date or '不限'} 至 {end_date or '不限'}"
        print(f"  日期范围: {date_range_str}")

        filtered_notices = []
        for notice in notices:
            pub_date = notice.get("发布日期")
            if crawler.is_date_in_range(pub_date, start_date, end_date):
                filtered_notices.append(notice)
            else:
                print(f"  跳过（不在日期范围）: {notice['标题'][:30]}...")

        notices = filtered_notices
        print(f"  日期过滤后剩余 {len(notices)} 条通知")

    if not notices:
        print(f"  没有符合日期范围的通知")
        continue

    # 限制分析数量
    notices_to_process = notices[:MAX_NOTICES_PER_SITE]

    # 分析每条通知
    for idx, notice in enumerate(notices_to_process, 1):
        pub_date = notice.get("发布日期") or "未知"
        print(f"\n  【第 {idx} 条】{notice['标题']}")
        print(f"  发布日期: {pub_date}")
        print(f"  文章链接: {notice['链接']}")

        # 抓取正文
        detail_result = crawler.fetch_notice_detail(notice["链接"])
        content = detail_result.get("content", "")

        if not content or "失败" in content:
            print(f"  [SKIP] 无法获取正文")
            continue

        print(f"  正文长度: {len(content)} 字符")
        print(f"  正文预览: {content[:200]}...")

        # 检查是否符合要求
        is_valid = crawler.should_include_notice(notice["标题"])
        print(f"  符合申报要求: {'是' if is_valid else '否'}")

        if is_valid:
            print(f"  [AI] 通知符合要求，将进行AI分析")
            ai_analyzed_count += 1
            result = {
                "网站": crawler.get_site_name(),
                "标题": notice["标题"],
                "发布日期": notice.get("发布日期"),
                "链接": notice["链接"],
                "正文长度": len(content),
                "AI分析": "将进行分析",
            }
        else:
            print(f"  [SKIP] 通知不符合要求，跳过AI分析")
            ai_skipped_count += 1
            result = {
                "网站": crawler.get_site_name(),
                "标题": notice["标题"],
                "发布日期": notice.get("发布日期"),
                "链接": notice["链接"],
                "正文长度": len(content),
                "AI分析": "跳过 - 不符合申报要求",
            }

        all_results.append(result)
        time.sleep(0.5)

# 总结
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)
print(f"总通知数: {len(all_results)}")
print(f"将进行AI分析: {ai_analyzed_count} 条")
print(f"跳过AI分析: {ai_skipped_count} 条")
print("=" * 60)

# 保存结果
try:
    import json
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, RESULT_FILENAME)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到 {filepath}")
except Exception as e:
    print(f"\n保存结果失败: {str(e)}")
