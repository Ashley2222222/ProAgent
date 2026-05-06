# -*- coding: utf-8 -*-
"""
HTML 报表模板
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>政策爬取日报 - {report_date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .overview-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .overview-card .number {{
            font-size: 36px;
            font-weight: bold;
            color: #4facfe;
            margin-bottom: 5px;
        }}
        .section {{ padding: 30px; border-bottom: 1px solid #eee; }}
        .section h2 {{ font-size: 18px; color: #333; margin-bottom: 20px; }}
        .department-table {{ width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .department-table th {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 12px; text-align: left; }}
        .department-table td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        .department-tag {{ display: inline-block; padding: 4px 12px; background: #e3f2fd; color: #1976d2; border-radius: 12px; font-size: 12px; }}
        .keyword-stats {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }}
        .keyword-tag {{ display: inline-block; padding: 6px 14px; background: #f3e5f5; color: #7b1fa2; border-radius: 16px; font-size: 12px; }}
        .policy-table-wrapper {{ margin-top: 20px; overflow-x: auto; border-radius: 10px; border: 1px solid #e6e9f2; }}
        .policy-table {{ width: 100%; border-collapse: collapse; min-width: 980px; }}
        .policy-table th {{ background: #f2f4f8; color: #333; font-weight: 700; font-size: 13px; padding: 12px; text-align: left; border-bottom: 1px solid #e6e9f2; }}
        .policy-table td {{ padding: 12px; border-bottom: 1px solid #eef0f6; vertical-align: top; font-size: 13px; color: #333; }}
        .policy-table tr:hover td {{ background: #fafbff; }}
        .policy-title-link {{ color: #2563eb; text-decoration: none; font-weight: 600; }}
        .policy-source-tag {{ display: inline-block; padding: 4px 10px; background: #e8f5e8; color: #2e7d32; border-radius: 12px; font-size: 12px; white-space: nowrap; }}
        .policy-date {{ font-size: 12px; color: #666; white-space: nowrap; }}
        .policy-keywords {{ display: flex; flex-wrap: wrap; gap: 6px; }}
        .action-btn {{ display: inline-block; padding: 6px 12px; border-radius: 10px; background: #2563eb; color: #fff; text-decoration: none; font-weight: 600; font-size: 12px; white-space: nowrap; }}
        .action-btn:hover {{ filter: brightness(0.95); }}
        .pagination {{ display: flex; justify-content: center; align-items: center; margin-top: 20px; }}
        .pagination a {{ color: #4facfe; padding: 8px 16px; text-decoration: none; border: 1px solid #ddd; margin: 0 4px; border-radius: 4px; }}
        .pagination a.active {{ background-color: #4facfe; color: white; border: 1px solid #4facfe; }}
        .footer {{ text-align: center; padding: 30px; background: #f8f9fa; font-size: 12px; color: #666; }}
        a {{ color: #4facfe; text-decoration: none; }}
        .print-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
        .word-btn {{
            position: fixed;
            top: 20px;
            right: 100px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #2b5876 0%, #4e4376 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
    </style>
</head>
<body>
    <button class="word-btn" onclick="exportToWord()">导出Word</button>
    <button class="print-btn" onclick="window.print()">打印</button>
    
    <div class="container">
        <div class="header">
            <h1>政策爬取日报</h1>
            <p>生成时间: {generation_time}</p>
        </div>
        
        <div class="overview">
            <div class="overview-card">
                <div class="number">{total_count}</div>
                <div class="label">总抓取数</div>
            </div>
            <div class="overview-card">
                <div class="number">{site_count}</div>
                <div class="label">涉及部门</div>
            </div>
            <div class="overview-card">
                <div class="number">{keyword_count}</div>
                <div class="label">关键词种类</div>
            </div>
            <div class="overview-card">
                <div class="number">日报</div>
                <div class="label">报告类型</div>
            </div>
        </div>
        
        <div class="section">
            <h2>部门分布</h2>
            <table class="department-table">
                <thead><tr><th>部门</th><th>数量</th><th>占比</th></tr></thead>
                <tbody>
                    {department_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>关键词统计</h2>
            <div class="keyword-stats">
                {keyword_stats_html}
            </div>
        </div>
        
        <div class="section">
            <h2>详细政策列表</h2>
            <div class="policy-table-wrapper">
                <table class="policy-table">
                    <thead>
                        <tr>
                            <th style="width: 28%;">标题</th>
                            <th style="width: 12%;">来源</th>
                            <th style="width: 10%;">发布日期</th>
                            <th style="width: 14%;">关键词</th>
                            <th style="width: 26%;">AI分析摘要</th>
                            <th style="width: 5%;">查看原文</th>
                            <th style="width: 5%;">建议书</th>
                        </tr>
                    </thead>
                    <tbody id="policy-tbody">
                        {policy_items_html}
                    </tbody>
                </table>
            </div>
            <div class="pagination" id="pagination"></div>
        </div>
        
        <div class="footer">
            <p>本报告由科研课题申报智能体自动生成 | 数据来源：政府官方网站</p>
            <p>生成时间：{generation_time}</p>
            <p>✓ 兼容: iOS 14+ | iPadOS 14+ | Safari | Chrome for iOS</p>
            <p>✓ 同时兼容: macOS | Safari for Mac | Chrome for Mac</p>
        </div>
    </div>

    <script>
        const itemsPerPage = 15;
        const policyTbody = document.getElementById('policy-tbody');
        const policyItems = policyTbody ? Array.from(policyTbody.querySelectorAll('tr')) : [];
        const paginationContainer = document.getElementById('pagination');
        const numPages = Math.ceil(policyItems.length / itemsPerPage);
        let currentPage = 1;

        function showPage(page) {{
            if (numPages <= 0) {{
                if (paginationContainer) paginationContainer.innerHTML = '';
                return;
            }}
            if (page < 1) page = 1;
            if (page > numPages) page = numPages;
            currentPage = page;
            const start = (page - 1) * itemsPerPage;
            const end = start + itemsPerPage;

            policyItems.forEach((item, index) => {{
                item.style.display = (index >= start && index < end) ? 'table-row' : 'none';
            }});

            renderPagination();
        }}

        function renderPagination() {{
            if (!paginationContainer) return;
            if (numPages <= 1) {{
                paginationContainer.innerHTML = '';
                return;
            }}
            let html = '';
            if (currentPage > 1) {{
                html += `<a href="#" onclick="showPage(${{currentPage - 1}})">上一页</a>`;
            }}

            for (let i = 1; i <= numPages; i++) {{
                html += `<a href="#" class="${{currentPage === i ? 'active' : ''}}" onclick="showPage(${{i}})">${{i}}</a>`;
            }}

            if (currentPage < numPages) {{
                html += `<a href="#" onclick="showPage(${{currentPage + 1}})">下一页</a>`;
            }}

            paginationContainer.innerHTML = html;
        }}

        showPage(1);

        function exportToWord() {{
            var content = document.documentElement.outerHTML;
            var blob = new Blob(['\\ufeff', content], {{
                type: 'application/msword'
            }});
            var url = URL.createObjectURL(blob);
            var link = document.createElement('a');
            link.href = url;
            link.download = '科研课题申报日报.doc';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}
    </script>

</body>
</html>"""
