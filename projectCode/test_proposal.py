import json
from proposal_generator import generate_proposals_batch

# 模拟一条符合要求的通知
mock_notice = {
    "标题": "广东省科学技术厅关于组织申报2026年度省重点研发计划项目的通知",
    "网站": "广东省科学技术厅",
    "发布日期": "2026-04-28",
    "链接": "http://example.com",
    "正文预览": "申报材料包括：项目申报书、预算表、承诺书。截止时间：2026年5月30日。",
    "课题申报分析": {
        "是否课题申报相关": True,
        "相关性理由": "标题包含'申报'",
        "通知要点": "测试要点",
        "申报方向": ["人工智能", "大数据"],
    },
    "材料提取": {
        "材料清单": ["项目申报书", "预算表", "承诺书"],
        "提交方式": "线上+纸质",
        "提交渠道": "系统",
        "截止时间": "2026-05-30",
    },
}

notices = [mock_notice]
count = generate_proposals_batch(notices, output_dir="data/proposals_test")
print(f"生成了 {count} 份建议书")
