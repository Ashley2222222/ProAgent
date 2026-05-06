# -*- coding: utf-8 -*-
"""
科研课题申报智能体 - 主程序
"""

import sys
import io
from urllib3.exceptions import InsecureRequestWarning
import requests

# 禁用 SSL 警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 强制设置标准输出/错误流的编码为UTF-8（解决Windows中文乱码）
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import time
import os
import json
from datetime import datetime
from crawler_factory import ResearchCrawlerFactory
from ai_analyzer import ResearchAIAnalyzer
from html_report_generator import generate_html_report
from rag_analyzer import analyze_materials_batch
from proposal_generator import generate_proposals_batch

import argparse


def send_wechat_message(message):
    """发送企业微信消息"""
    try:
        headers = {"Content-Type": "application/json"}
        data = {"msgtype": "markdown", "markdown": {"content": message}}
        response = requests.post(
            WECHAT_WEBHOOK_URL, headers=headers, json=data, verify=False
        )
        response.raise_for_status()
        result = response.json()
        if result.get("errcode") == 0:
            print("✅ 企业微信消息推送成功")
            return True
        else:
            print(f"⚠️  企业微信消息推送失败: {result.get('errmsg')}")
            return False
    except Exception as e:
        print(f"❌ 企业微信消息推送异常: {str(e)}")
        return False


def _extract_wechat_webhook_key(webhook_url: str) -> str | None:
    try:
        if not webhook_url:
            return None
        if "key=" not in webhook_url:
            return None
        return webhook_url.split("key=", 1)[1].split("&", 1)[0].strip() or None
    except Exception:
        return None


def upload_file_to_wechat(file_path: str, webhook_key: str) -> str | None:
    """
    将本地文件上传到企业微信临时素材库，获取 media_id（有效期3天）
    官方限制：最小5字节，最大20MB
    """
    try:
        if not file_path or not os.path.exists(file_path):
            print(f"⚠️  文件不存在，跳过上传：{file_path}")
            return None
        file_size = os.path.getsize(file_path)
        if not (5 <= file_size <= 20 * 1024 * 1024):
            print(f"⚠️  文件大小不符合要求：{file_size} 字节（需介于5B和20MB之间）")
            return None
        if not webhook_key:
            print("⚠️  webhook_key 为空，跳过上传")
            return None

        upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={webhook_key}&type=file"
        with open(file_path, "rb") as f:
            files = {
                "media": (os.path.basename(file_path), f, "application/octet-stream")
            }
            resp = requests.post(upload_url, files=files, timeout=60, verify=False)
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode") == 0 and result.get("media_id"):
            print(f"✅ 文件上传成功，media_id: {result['media_id']}")
            return result["media_id"]
        print(f"⚠️  文件上传失败：{result}")
        return None
    except Exception as e:
        print(f"❌ 文件上传异常：{str(e)}")
        return None


def send_wechat_file(media_id: str, webhook_url: str) -> bool:
    """发送文件到企业微信群（file 消息）"""
    try:
        if not media_id:
            return False
        headers = {"Content-Type": "application/json"}
        data = {"msgtype": "file", "file": {"media_id": media_id}}
        resp = requests.post(
            webhook_url, headers=headers, json=data, timeout=60, verify=False
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode") == 0:
            print("✅ 企业微信文件消息推送成功")
            return True
        print(f"⚠️  企业微信文件消息推送失败: {result.get('errmsg')}")
        return False
    except Exception as e:
        print(f"❌ 企业微信文件消息推送异常: {str(e)}")
        return False


# 导入配置
from config import (
    ENABLE_AI_ANALYSIS,
    ENABLE_RAG_ANALYSIS,
    ENABLE_AUTO_PROPOSAL,
    AI_ONLY_ANALYZE_VALID,
    LIMIT_NOTICES_PER_SITE,
    MAX_NOTICES_PER_SITE,
    DATE_RANGE,
    OUTPUT_DIR,
    RESULT_FILENAME,
    RAG_RESULT_FILENAME,
    WECHAT_WEBHOOK_URL,
    ENABLE_WECHAT_NOTIFICATION,
    ENABLE_WECHAT_MARKDOWN,
    ENABLE_WECHAT_FILE,
)


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="科研课题申报智能体")
    parser.add_argument(
        "--sites",
        type=str,
        default=None,
        help="指定要爬取的网站（多个用逗号分隔），例如: --sites gdstc.gd.gov.cn,kjj.gz.gov.cn。不指定则爬取所有网站。",
    )
    parser.add_argument(
        "--list-sites", action="store_true", help="列出所有可用的网站标识，然后退出"
    )
    args = parser.parse_args()

    # 如果要求列出网站，则打印并退出
    if args.list_sites:
        site_configs = ResearchCrawlerFactory.get_all_sites()
        print("可用的网站标识：")
        for key in site_configs.keys():
            desc = site_configs[key].get("description", key)
            print(f"  {key}  -> {desc}")
        return

    # 获取完整网站配置
    all_site_configs = ResearchCrawlerFactory.get_all_sites()

    # 根据 --sites 参数过滤需要爬取的网站
    if args.sites:
        selected_keys = [s.strip() for s in args.sites.split(",")]
        site_configs = {k: v for k, v in all_site_configs.items() if k in selected_keys}
        if not site_configs:
            print(
                f"错误：指定的网站标识 {args.sites} 无效，请使用 --list-sites 查看可用标识"
            )
            return
        print(f"已选择爬取网站: {list(site_configs.keys())}")
    else:
        site_configs = all_site_configs
        print("未指定网站，将爬取所有网站")

    """主程序入口"""
    print("=" * 60)
    print("科研课题申报智能体 - 开始运行")
    print(f"AI分析模式: {'开启' if ENABLE_AI_ANALYSIS else '关闭（仅爬取）'}")
    print("=" * 60)

    # 创建AI分析器（仅在需要时）
    analyzer = ResearchAIAnalyzer() if ENABLE_AI_ANALYSIS else None

    # 获取所有网站配置
    # site_configs = ResearchCrawlerFactory.get_all_sites() 上面168行那段代码选择了网站了

    all_results = []

    # 遍历所有网站
    for site_key, config in site_configs.items():
        print(f"\n{'='*60}")
        print(f"【网站】{config['description']} - {config['base_url']}")
        print(f"{'='*60}")

        # 创建爬虫实例
        crawler = ResearchCrawlerFactory.create_crawler(site_key)

        # 获取该网站的所有列表页
        list_urls = config.get("list_urls", [])
        if not list_urls:
            print(f"  ⚠️  未配置列表页地址，跳过")
            continue

        # 遍历所有列表页
        all_notices = []
        for list_config in list_urls:
            list_url = list_config["url"]
            list_name = list_config.get("name", "未命名")

            print(f"\n  【列表页】{list_name}")
            print(f"  URL: {list_url}")

            # 抓取通知列表（支持分页）
            max_pages = config.get("max_pages", 10)
            notices = crawler.fetch_notice_list(list_url, max_pages=max_pages)

            if notices:
                print(f"    ✅ 找到 {len(notices)} 条通知")
                all_notices.extend(notices)
            else:
                print(f"    ⚠️  未找到通知")

        notices = all_notices
        print(f"\n  📊 该网站共找到 {len(notices)} 条相关通知")

        # 第一步：在爬虫阶段按标题做语义过滤（排除公示/结果/会议等不相关通知）
        pre_filter_count = len(notices)
        notices = [
            n for n in notices if crawler.should_include_notice(n.get("标题", ""))
        ]
        if len(notices) != pre_filter_count:
            print(
                f"  🔍 按关键词预过滤后剩余 {len(notices)} 条（剔除 {pre_filter_count - len(notices)} 条非申报类）"
            )

        if not notices:
            continue

        # 根据配置决定是否限制分析数量
        if LIMIT_NOTICES_PER_SITE:
            notices_to_process = notices[:MAX_NOTICES_PER_SITE]
            print(
                f"  限制分析数量: 前 {len(notices_to_process)} 条（共 {len(notices)} 条）"
            )
        else:
            notices_to_process = notices
            print(f"  分析所有符合要求的通知: {len(notices)} 条")

        # 分析每条通知
        start_date = DATE_RANGE.get("start_date")
        end_date = DATE_RANGE.get("end_date")

        if start_date or end_date:
            date_range_str = f"{start_date or '不限'} 至 {end_date or '不限'}"
            print(f"  📅 日期范围: {date_range_str}")

        filtered_results = []

        for idx, notice in enumerate(notices_to_process, 1):
            pub_date = notice.get("发布日期") or "未知"
            print(f"\n  【第 {idx} 条】{notice['标题']}")
            print(f"  发布日期: {pub_date}")
            print(f"  文章链接: {notice['链接']}")

            # 抓取正文
            detail_result = crawler.fetch_notice_detail(notice["链接"])
            content = detail_result.get("content", "")
            detail_pub_date = detail_result.get("pub_date")

            # 如果详情页提取到了日期，优先使用详情页的日期
            if detail_pub_date:
                notice["发布日期"] = detail_pub_date
                print(f"  🔄 更新发布日期: {detail_pub_date}")

            # 按日期范围过滤
            pub_date = notice.get("发布日期")
            if start_date or end_date:
                if not crawler.is_date_in_range(pub_date, start_date, end_date):
                    print(f"  ⏭️  跳过（不在日期范围）: {notice['标题'][:30]}...")
                    continue

            if not content or "失败" in content:
                print(f"  ❌ 无法获取正文: {content}")
                continue

            # 简单信息提取（无需AI）
            print(f"  📄 正文长度: {len(content)} 字符")
            print(f"  📝 正文预览: {content[:200]}...")

            if ENABLE_AI_ANALYSIS:
                # 只对符合要求的通知进行AI分析（受 AI_ONLY_ANALYZE_VALID 控制）
                if AI_ONLY_ANALYZE_VALID and not crawler.should_include_notice(
                    notice["标题"]
                ):
                    print("  ⏭️  跳过AI分析（非申报类通知）")
                    result = {
                        "网站": crawler.get_site_name(),
                        "标题": notice["标题"],
                        "发布日期": notice.get("发布日期"),
                        "链接": notice["链接"],
                        "正文长度": len(content),
                        "正文预览": content[:500],
                    }
                else:
                    # AI分析模式
                    print(f"  🤖 AI分析中...")
                    ai_result = analyzer.analyze_notice(notice["标题"], content)

                    # 输出结果
                    print(f"  ✅ AI分析完成:")
                    for k, v in ai_result.items():
                        try:
                            print(f"     {k}: {v}")
                        except:
                            print(f"     {k}: {str(v)[:100]}...")

                    # 保存结果
                    result = {
                        "网站": crawler.get_site_name(),
                        "标题": notice["标题"],
                        "发布日期": notice.get("发布日期"),
                        "链接": notice["链接"],
                        "正文长度": len(content),
                        "正文预览": content[:500],
                        "分析结果": ai_result,
                    }
            else:
                # 仅爬取模式
                print(f"  ✅ 爬取完成（AI分析已跳过）")
                result = {
                    "网站": crawler.get_site_name(),
                    "标题": notice["标题"],
                    "发布日期": notice.get("发布日期"),
                    "链接": notice["链接"],
                    "正文长度": len(content),
                    "正文预览": content[:500],
                }

            filtered_results.append(result)

            # 稍微延迟，避免请求过快
            time.sleep(0.5)

        # 将过滤后的结果添加到总结果中
        all_results.extend(filtered_results)
        print(f"  ✅ 日期过滤后剩余 {len(filtered_results)} 条通知")

        if not filtered_results:
            print(f"  ⚠️  没有符合日期范围的通知")
            continue

    # 总结
    print("\n" + "=" * 60)
    if ENABLE_AI_ANALYSIS:
        print(f"✅ 全部完成！共AI分析 {len(all_results)} 条通知")
    else:
        print(f"✅ 全部完成！共爬取 {len(all_results)} 条通知（AI分析未启用）")
    print("=" * 60)

    # 保存到文件（可选）
    try:
        import json

        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 根据AI分析状态选择文件名
        filename = "analysis_results.json" if ENABLE_AI_ANALYSIS else RESULT_FILENAME
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 结果已保存到 {filepath}")
    except Exception as e:
        print(f"\n⚠️  保存结果失败: {str(e)}")

    # RAG材料提取
    if ENABLE_RAG_ANALYSIS and all_results:
        print("\n🧩 正在进行RAG材料提取...")
        materials_results = analyze_materials_batch(all_results)
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            rag_path = os.path.join(OUTPUT_DIR, RAG_RESULT_FILENAME)
            with open(rag_path, "w", encoding="utf-8") as f:
                json.dump(materials_results, f, ensure_ascii=False, indent=2)
            print(f"🧾 材料提取结果已保存到 {rag_path}")
        except Exception as e:
            print(f"⚠️  材料提取结果保存失败: {str(e)}")

        # 自动生成《项目申报建议书》初稿
        if ENABLE_AUTO_PROPOSAL:
            print("\n📝 正在为判定为申报相关的通知生成《项目申报建议书》...")
            try:
                # 直接使用 RAG 分析后的材料结果 materials_results
                from proposal_generator import generate_proposals_batch

                count = generate_proposals_batch(
                    materials_results, output_dir=os.path.join(OUTPUT_DIR, "proposals")
                )
                print(f"✅ 共生成 {count} 份建议书")

            except Exception as e:
                print(f"⚠️  生成建议书失败: {str(e)}")

            print(
                "\n📝 正在为所有通知生成《项目申报建议书》（基于原始爬取内容） 测试用..."
            )
            try:
                from proposal_generator import generate_proposals_from_raw

                count = generate_proposals_from_raw(
                    all_results, output_dir=os.path.join(OUTPUT_DIR, "proposals")
                )
                print(f"✅ 共生成 {count} 份建议书")
            except Exception as e:
                print(f"⚠️  生成建议书失败: {str(e)}")

    # 生成HTML日报
    html_filename = None
    # 如果启用了AI分析，日报应该使用包含分析结果的原始数据
    if ENABLE_AI_ANALYSIS:
        results_for_html = all_results
    else:
        # 否则优先使用RAG结果（如果存在且非空）
        results_for_html = None
        if ENABLE_RAG_ANALYSIS and all_results:
            try:
                rag_path = os.path.join(OUTPUT_DIR, RAG_RESULT_FILENAME)
                if os.path.exists(rag_path):
                    with open(rag_path, "r", encoding="utf-8") as f:
                        results_for_html = json.load(f)
            except Exception:
                results_for_html = None
        if results_for_html is None or len(results_for_html) == 0:
            results_for_html = all_results

    if results_for_html:
        print("\n📄 正在生成HTML日报...")
        html_filename = f"政策爬取日报_{datetime.now().strftime('%Y%m%d')}.html"
        # 将日报保存到 data 目录下
        html_filepath = os.path.join(OUTPUT_DIR, html_filename)
        # 确保 OUTPUT_DIR 存在（已经在上方创建过，但再保证一次）
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        html_filename = generate_html_report(results_for_html, html_filepath)
        # 为了后续企业微信消息里显示文件名，只保留文件名（不含路径）
        if html_filename:
            html_filename = os.path.basename(html_filename)

    # 企业微信消息推送
    if ENABLE_WECHAT_NOTIFICATION and all_results:
        if ENABLE_WECHAT_MARKDOWN or ENABLE_WECHAT_FILE:
            print("\n📤 正在推送企业微信消息...")

        # 构建消息内容
        today = time.strftime("%Y-%m-%d")

        if ENABLE_AI_ANALYSIS:
            title = f"【AI分析结果】科研课题申报日报 - {today}"
            message = f"## {title}\n\n"
        else:
            title = f"【政策爬取日报】科研课题申报 - {today}"
            message = f"## {title}\n\n"

        # 概览部分
        message += f"### 📊 今日概览\n"
        message += f"- **爬取网站**: {len(site_configs)} 个\n"
        message += f"- **通知数量**: {len(all_results)} 条\n"
        message += f"- **生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"

        if html_filename:
            message += f"- **HTML日报**: 已生成，保存在本地\n\n"
        else:
            message += "\n"

        # 按网站分组展示
        site_groups = {}
        for result in all_results:
            site = result["网站"]
            if site not in site_groups:
                site_groups[site] = []
            site_groups[site].append(result)

        # 详细结果部分
        message += "### 📋 重点通知\n"

        # 限制显示的网站数量和通知数量
        top_sites = sorted(site_groups.items(), key=lambda x: len(x[1]), reverse=True)[
            :3
        ]
        total_displayed = 0

        for site, site_results in top_sites:
            message += f"#### 🏢 {site}\n"

            # 每个网站显示前2条
            for i, result in enumerate(site_results[:2], 1):
                if total_displayed >= 6:  # 最多显示6条通知
                    break

                # 限制标题长度
                title = (
                    result["标题"][:40] + "..."
                    if len(result["标题"]) > 40
                    else result["标题"]
                )
                message += f"**{i}. {title}**\n"
                message += f"> 日期: {result['发布日期']}\n"
                message += f"> 链接: [{result['链接'][:50]}...]({result['链接']})\n"

                if ENABLE_AI_ANALYSIS and "分析结果" in result:
                    ai_result = result["分析结果"]
                    message += "> **AI分析:**\n"
                    # 只显示关键信息
                    key_fields = ["资助金额", "截止日期", "申请条件"]
                    for field in key_fields:
                        if field in ai_result and ai_result[field]:
                            message += f"> - {field}: {ai_result[field]}\n"
                else:
                    # 不显示摘要，减少长度
                    pass
                message += "\n"
                total_displayed += 1

            if len(site_results) > 2 and total_displayed < 6:
                message += f"> ... 还有 {len(site_results) - 2} 条\n\n"

        # 其他网站汇总
        if len(site_groups) > 3:
            other_sites = len(site_groups) - 3
            other_notices = sum(
                len(results)
                for site, results in site_groups.items()
                if site not in dict(top_sites)
            )
            message += f"#### 🌐 其他网站\n"
            message += f"> {other_sites}个网站，共{other_notices}条通知\n\n"

        # 结尾
        message += "### 💡 提示\n"
        message += "> 完整结果已保存至本地文件\n"
        if html_filename:
            message += f"> HTML日报已生成: {html_filename}\n"
        message += "> 此日报由智能体自动生成\n"
        if html_filename:
            print(f"\n📤 HTML日报编写完成： {html_filename}")
        else:
            print(
                "\n⚠️ HTML日报生成失败，请检查 results_for_html 是否为空或 generate_html_report 报错"
            )
        # 发送 Markdown 摘要消息（可选）
        if ENABLE_WECHAT_MARKDOWN:
            send_wechat_message(message)

        # 发送 HTML 文件（作为单独一条 file 消息，可选）
        if ENABLE_WECHAT_FILE and html_filename:
            print("\n📤 发送 HTML 文件： " + html_filename)
            try:
                # html_filename 可能是绝对路径或相对路径，这里统一解析为实际文件路径
                # 直接用 OUTPUT_DIR 绝对路径拼接
                html_file_path = os.path.join(OUTPUT_DIR, html_filename)
                if os.path.exists(html_file_path):
                    print(f"\n📤 文件路径：{html_file_path}")
                    webhook_key = _extract_wechat_webhook_key(WECHAT_WEBHOOK_URL)
                    media_id = upload_file_to_wechat(html_file_path, webhook_key or "")
                    if media_id:
                        send_wechat_file(media_id, WECHAT_WEBHOOK_URL)
                    else:
                        print("⚠️  未获取到 media_id，跳过文件发送")
                else:
                    print(f"⚠️  HTML 文件不存在，跳过发送：{html_file_path}")
            except Exception as e:
                print(f"⚠️  文件发送流程异常：{str(e)}")


if __name__ == "__main__":
    main()
