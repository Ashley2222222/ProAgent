# -*- coding: utf-8 -*-
import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
from rag_analyzer import _retry_request
from config import AI_MODEL

load_dotenv()
API_KEY = os.getenv("AI_API_KEY")
TEST_MODE = False  # 测试模式：返回固定模板，不调用 AI


def generate_proposal_markdown(notice: Dict[str, Any]) -> str:
    if TEST_MODE:
        title = notice.get("标题", "未知标题")
        content = notice.get("正文预览", "")[:200]
        return f"""# 项目申报建议书（测试版）

**通知标题**：{title}
**通知摘要**：{content}

这是一份测试生成的建议书，用于验证文件生成和保存逻辑。

## 项目基本信息
- 项目名称：（待填写）
- 申报截止时间：（待填写）

## 核心申报条件
（测试内容，请勿用于实际申报）

## 重点支持方向
（测试内容）

## 申报材料清单检查表
- [ ] 材料1
- [ ] 材料2

## 下一步行动建议
1. 尽快准备材料
2. 联系合作单位
"""
    # 以下是原有代码（当 TEST_MODE = False 时执行）
    else:
        """调用AI生成《项目申报建议书》Markdown内容"""
        if not API_KEY:
            return "⚠️ 未配置AI_API_KEY，无法生成建议书。"

        title = notice.get("标题", "未知标题")
        content = notice.get("正文预览", "")
        link = notice.get("链接", "")

        # 提取已经存在的RAG分析结果
        rag_info = notice.get("材料提取", {})
        materials = rag_info.get("材料清单", [])
        if isinstance(materials, list):
            materials_text = "\n".join([f"- {m}" for m in materials])
        else:
            materials_text = str(materials)

        prompt = f"""你是专业的项目申报顾问。请根据以下政府/科研项目申报通知，起草一份详细的《项目申报建议书》初稿。
    要求：
    1. 格式为标准的Markdown。
    2. 包含以下模块：
    - **项目基本信息**（名称、来源、截止时间）
    - **核心申报条件**（根据正文提炼企业/个人需要满足的核心门槛）
    - **重点支持方向**（提取重点领域，给出简要的申报切入点建议）
    - **申报材料清单检查表**（基于已有材料提取结果细化，并留出打勾框如 [ ]）
    - **下一步行动建议**（如：成立项目组、准备财务审计报告、联系合作单位等时间节点建议）

    【通知信息】
    标题：{title}
    原文链接：{link}
    已知材料：
    {materials_text}

    正文摘要：
    {content[:3000]}

    请直接输出Markdown内容，不要输出```markdown等代码块包裹。
    """

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json; charset=utf-8",
        }
        data = {
            "model": AI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
        }

        try:
            js = _retry_request(
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                headers,
                data,
                max_retries=2,
            )
            txt = js["choices"][0]["message"]["content"]
            # 清理可能存在的markdown包裹
            if txt.startswith("```markdown"):
                txt = txt[11:]
            if txt.startswith("```"):
                txt = txt[3:]
            if txt.endswith("```"):
                txt = txt[:-3]
            return txt.strip()
        except Exception as e:
            return f"⚠️ 生成建议书失败：{str(e)}"


def generate_proposals_batch(
    notices: List[Dict[str, Any]], output_dir: str = "data/proposals"
):
    """为相关通知批量生成建议书并保存到文件"""
    os.makedirs(output_dir, exist_ok=True)
    generated_count = 0

    for notice in notices:
        # 只处理课题申报相关的通知
        rag_analysis = notice.get("课题申报分析", {})
        if not rag_analysis.get("是否课题申报相关"):
            continue

        # 只要判定为申报相关，就生成建议书，不再限制材料清单非空
        # 注释掉以下条件判断
        # 简单判定为“高价值”：比如有明确方向或材料
        # materials = notice.get("材料提取", {}).get("材料清单", [])
        # if not materials or materials == ["未明确"]:
        #     continue

        print(f"  📝 正在为《{notice['标题'][:20]}...》生成申报建议书...")
        md_content = generate_proposal_markdown(notice)

        # 清理文件名中的非法字符
        safe_title = "".join(
            c for c in notice["标题"] if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_title = safe_title[:50]  # 限制文件名长度

        filename = f"项目申报建议书_{safe_title}.md"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            generated_count += 1
            print(f"    ✅ 已保存至: {filepath}")
        except Exception as e:
            print(f"    ⚠️ 保存失败: {str(e)}")

    return generated_count


def generate_proposals_from_raw(
    notices: List[Dict[str, Any]], output_dir: str = "data/proposals"
) -> int:
    print(f"[DEBUG] 进入函数，notices 数量: {len(notices)}")
    if notices:
        first = notices[0]
        print(f"[DEBUG] 第一条标题: {first.get('标题')}")
        print(f"[DEBUG] 第一条正文预览长度: {len(first.get('正文预览', ''))}")
        print(f"[DEBUG] 第一条正文预览内容: {first.get('正文预览', '')[:100]}")
    """
    基于原始爬取结果（all_results）直接生成申报建议书，不依赖 RAG 分析结果。
    每条通知都会生成一份 .md 文件（即使材料清单为空）。
    """
    os.makedirs(output_dir, exist_ok=True)
    generated_count = 0

    for notice in notices:
        title = notice.get("标题", "")
        content = notice.get("正文预览", "")
        link = notice.get("链接", "")
        if not title or not content:
            continue  # 缺少必要的标题或正文，跳过

        print(f"  📝 正在为《{title[:30]}...》生成申报建议书...")
        md_content = generate_proposal_markdown(notice)  # 复用原有的 AI 生成函数

        safe_title = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_title = safe_title[:50]
        filename = f"项目申报建议书_{safe_title}.md"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            generated_count += 1
            print(f"    ✅ 已保存至: {filepath}")
        except Exception as e:
            print(f"    ⚠️ 保存失败: {str(e)}")

    return generated_count


if __name__ == "__main__":
    test_file = "data/materials_results.json"
    if os.path.exists(test_file):
        with open(test_file, "r", encoding="utf-8") as f:
            notices = json.load(f)
        generate_proposals_batch(notices)
