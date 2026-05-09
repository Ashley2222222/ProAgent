# -*- coding: utf-8 -*-
import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
from config import AI_MODEL
import time
import requests

load_dotenv()
API_KEY = os.getenv("AI_API_KEY")
TEST_MODE = False  # 测试模式：返回固定模板，不调用 AI


def _retry_request(
    url: str, headers: dict, json_data: dict, max_retries: int = 2
) -> dict:
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                url, headers=headers, json=json_data, timeout=60, verify=False
            )
            resp.raise_for_status()
            js = resp.json()
            if "choices" not in js:
                err = js.get("error", {}) if isinstance(js, dict) else {}
                msg = err.get("message") or err.get("code") or str(js)[:200]
                raise ValueError(msg)
            if "usage" in js:
                print(f"[Token] 本次生成消耗: {js['usage']}")
            return js
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
                continue
            raise
    raise last_error or Exception("Max retries exceeded")


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


def generate_full_proposal(notice_info: Dict[str, Any], kb, top_k: int = 5) -> str:

    title = (notice_info.get("标题") or "").strip()
    link = (notice_info.get("链接") or "").strip()
    site = (notice_info.get("网站") or "").strip()
    pub_date = (notice_info.get("发布日期") or "").strip()
    ai = (
        notice_info.get("分析结果")
        if isinstance(notice_info.get("分析结果"), dict)
        else {}
    )

    query_parts = [title]
    for k in [
        "核心申报条件",
        "征集内容",
        "申报主体",
        "资助类型",
        "申报截止时间",
        "申报流程",
    ]:
        v = ai.get(k)
        if isinstance(v, str) and v.strip() and v != "未明确":
            query_parts.append(f"{k}:{v}")
    query_text = "\n".join(query_parts).strip()

    if kb is None or getattr(kb, "is_empty", None) is None or kb.is_empty():
        return "⚠️ 知识库为空，请先上传历史申报书后再生成。"

    hits = kb.query(query_text, top_k=top_k)
    refs = []

    for i, h in enumerate(hits, 1):
        meta = h.get("metadata") or {}
        src = meta.get("source") or "unknown"
        txt = (h.get("text") or "").strip()
        if not txt:
            continue
        refs.append(f"[{i}] 来源：{src}\n{txt}")
    refs_text = "\n\n".join(refs)[:8000]
    print(f"[DEBUG] 检索到的片段数量: {len(hits)}")
    print(f"[DEBUG] 第一个片段内容: {refs_text[:500] if refs_text else '无'}")
    structured = {
        "标题": title or "未明确",
        "来源": site or "未明确",
        "发布日期": pub_date or "未明确",
        "原文链接": link or "未明确",
        "项目名称": ai.get("项目名称", "未明确"),
        "申报截止时间": ai.get("申报截止时间", "未明确"),
        "申报主体": ai.get("申报主体", "未明确"),
        "资助类型": ai.get("资助类型", "未明确"),
        "核心申报条件": ai.get("核心申报条件", "未明确"),
        "征集内容": ai.get("征集内容", "未明确"),
        "申报流程": ai.get("申报流程", "未明确"),
        "联系方式": ai.get("联系方式", "未明确"),
        "风险提示": ai.get("风险提示", "未明确"),
    }

    prompt = f"""你是资深科研项目申报撰写专家。
请参考“历史申报书片段”（风格、结构、措辞、章节组织），并结合“当前通知信息”，生成一份可直接用于申报的《项目申报书》Markdown 初稿。
只输出 Markdown，不要输出任何代码块标记。
使用清晰的三级标题（###），避免过深层级。

必须包含以下模块（按顺序）：
### 项目概述
### 立项依据
### 研究内容与目标
### 技术路线
### 预期成果
### 进度安排
### 经费预算
### 团队基础

写作要求：
1. 语言正式、可落地。**每个章节必须根据历史片段和通知信息填充实质性内容，不允许出现“（待补充）”或类似的占位符**。
2. 若通知里提到申报主体/资助方式/截止时间/流程/材料等，请在相应章节体现。
3. 可借鉴历史片段的表达方式，但不要逐字照搬；保持一致性与可读性。
4. 如果某些信息在历史片段或通知中缺失，请基于通用科研项目申报惯例进行合理推断，确保每个章节至少有一段具体描述。

【当前通知信息（结构化）】
{json.dumps(structured, ensure_ascii=False, indent=2)}

【历史申报书参考片段（检索Top{top_k}）】
{refs_text}
"""

    if not API_KEY:
        return "⚠️ 未配置AI_API_KEY，无法生成完整申报书。"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }
    data = {
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    try:
        js = _retry_request(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers,
            data,
            max_retries=2,
        )
        txt = js["choices"][0]["message"]["content"]
        if txt.startswith("```markdown"):
            txt = txt[11:]
        if txt.startswith("```"):
            txt = txt[3:]
        if txt.endswith("```"):
            txt = txt[:-3]
        print(f"[DEBUG] 模型原始返回: {txt[:500]}")
        return txt.strip()
    except Exception as e:
        return f"⚠️ 生成完整申报书失败：{str(e)}"


if __name__ == "__main__":
    test_file = "data/materials_results.json"
    if os.path.exists(test_file):
        with open(test_file, "r", encoding="utf-8") as f:
            notices = json.load(f)
        generate_proposals_batch(notices)
