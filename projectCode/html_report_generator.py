# -*- coding: utf-8 -*-
"""
HTML日报生成器
"""

from datetime import datetime
from html_templates import HTML_TEMPLATE
import os
from urllib.parse import quote


def generate_html_report(results, filename):
    """生成HTML日报文件"""
    try:
        # 统计数据
        total_count = len(results)
        site_groups = {}
        for result in results:
            site = result["网站"]
            if site not in site_groups:
                site_groups[site] = []
            site_groups[site].append(result)

        site_count = len(site_groups)

        # 关键词统计（简化版）
        keywords = {}
        for result in results:
            title = result["标题"]
            for kw in [
                "申报",
                "人工智能",
                "高质量发展",
                "工业互联网",
                "创新应用",
                "基金项目",
                "专项计划",
            ]:
                if kw == "高质量发展" and "高质量" in title:
                    keywords[kw] = keywords.get(kw, 0) + 1
                elif kw == "工业互联网" and "工业" in title:
                    keywords[kw] = keywords.get(kw, 0) + 1
                elif kw in title:
                    keywords[kw] = keywords.get(kw, 0) + 1

        # 部门分布 HTML
        department_rows = ""
        for site, site_results in sorted(
            site_groups.items(), key=lambda x: len(x[1]), reverse=True
        )[:8]:
            count = len(site_results)
            percentage = round(count / total_count * 100, 1)
            department_rows += f"""
                    <tr>
                        <td><span class="department-tag">{site}</span></td>
                        <td>{count}</td>
                        <td>{percentage}%</td>
                    </tr>"""

        # 关键词统计 HTML
        keyword_stats_html = "".join(
            [
                f'<span class="keyword-tag">{kw} ({count})</span>'
                for kw, count in keywords.items()
            ]
        )

        # 政策列表 HTML
        # 生成表格行
        policy_items_html = ""
        report_dir = os.path.dirname(os.path.abspath(filename)) if filename else ""
        proposals_dir = os.path.join(report_dir, "proposals") if report_dir else ""
        for idx, result in enumerate(results, 1):
            title = result["标题"]
            site = result["网站"]
            pub_date = result["发布日期"]

            item_keywords = []
            for kw in [
                "申报",
                "人工智能",
                "高质量发展",
                "工业互联网",
                "创新应用",
                "基金项目",
                "专项计划",
            ]:
                if kw == "高质量发展" and "高质量" in title:
                    item_keywords.append(kw)
                elif kw == "工业互联网" and "工业" in title:
                    item_keywords.append(kw)
                elif kw in title:
                    item_keywords.append(kw)
            keywords_html = "".join([f'<span class="keyword-tag">{kw}</span>' for kw in item_keywords])

            # 提取AI分析摘要（如果有）
            ai_analysis = result.get("分析结果", {})
            if ai_analysis:
                # 构建摘要内容：项目名称、截止时间、资助类型、分析结论等
                summary_parts = []
                if ai_analysis.get("项目名称"):
                    summary_parts.append(f"【项目】{ai_analysis['项目名称']}")
                if ai_analysis.get("申报截止时间"):
                    summary_parts.append(f"【截止】{ai_analysis['申报截止时间'][:60]}")
                if ai_analysis.get("资助类型"):
                    summary_parts.append(f"【资助】{ai_analysis['资助类型']}")
                if ai_analysis.get("分析结论"):
                    summary_parts.append(f"【结论】{ai_analysis['分析结论'][:80]}")
                ai_summary = (
                    "<br>".join(summary_parts) if summary_parts else "AI分析无关键信息"
                )
            else:
                # 降级使用材料提取中的信息
                materials = result.get("材料提取", {})
                if materials.get("截止时间"):
                    ai_summary = f"【截止】{materials['截止时间'][:60]}"
                else:
                    ai_summary = "无AI分析"

            # 生成建议书下载链接（文件存在性检查在web_app中完成，这里只构造链接）
            # 根据标题生成建议书文件名（与proposal_generator一致）
            safe_title = "".join(
                c for c in title if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            safe_title = safe_title[:50]
            proposal_filename = f"项目申报建议书_{safe_title}.md"
            proposal_url = f"proposals/{quote(proposal_filename)}"
            proposal_path = (
                os.path.join(proposals_dir, proposal_filename) if proposals_dir else ""
            )

            # 操作链接（查看原文）
            link_html = f'<a class="action-btn" href="{result["链接"]}" target="_blank">查看原文</a>'
            if proposal_path and os.path.exists(proposal_path):
                proposal_html = (
                    f'<a class="action-btn" href="{proposal_url}" target="_blank">打开建议书</a>'
                )
            else:
                proposal_html = '<span style="color:#9ca3af;font-size:12px;">未生成</span>'

            policy_items_html += f"""
            <tr>
                <td><a class="policy-title-link" href="{result['链接']}" target="_blank">{idx}. {title}</a></td>
                <td><span class="policy-source-tag">{site}</span></td>
                <td><span class="policy-date">{pub_date}</span></td>
                <td><div class="policy-keywords">{keywords_html}</div></td>
                <td>{ai_summary}</td>
                <td>{link_html}</td>
                <td>{proposal_html}</td>
            </tr>
            """

        # 使用模板填充内容
        html_content = HTML_TEMPLATE.format(
            report_date=datetime.now().strftime("%Y-%m-%d"),
            generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_count=total_count,
            site_count=site_count,
            keyword_count=len(keywords),
            department_rows=department_rows,
            keyword_stats_html=keyword_stats_html,
            policy_items_html=policy_items_html,
        )

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"HTML日报已生成: {filename}")
        return filename

    except Exception as e:
        print(f"生成HTML日报失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    import json

    # 测试代码
    test_file = "../data/crawl_results.json"
    if os.path.exists(test_file):
        with open(test_file, "r", encoding="utf-8") as f:
            results = json.load(f)

        output_file = f"政策爬取日报_{datetime.now().strftime('%Y%m%d')}.html"
        generate_html_report(results, output_file)
