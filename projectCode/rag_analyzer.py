# -*- coding: utf-8 -*-
import os
import re
import json
from typing import List, Dict, Any

RETRIEVAL_MODE = "rule"  # 未来可改为 "vector"

APPLICATION_KEYWORDS = [
    "申报",
    "征集",
    "遴选",
    "推荐",
    "申请",
    "申报指南",
    "申请指南",
    "课题申报",
    "项目申报",
]

EXCLUDE_KEYWORDS = [
    "公示",
    "结果",
    "评审结果",
    "立项",
    "中标",
    "成交",
    "批复",
    "核准",
    "批准",
    "备案",
    "验收",
    "奖励",
    "表彰",
    "调研",
    "座谈",
    "会议",
    "培训",
    "通报",
    "意见反馈",
    "征求意见",
    "补贴",
    "补助",
]

MATERIAL_KEYWORDS = [
    "申报材料",
    "材料清单",
    "提交材料",
    "所需材料",
    "纸质",
    "电子版",
    "附件",
    "上传",
    "盖章",
    "扫描件",
    "申请书",
    "项目申报书",
    "预算",
    "预算表",
    "承诺书",
    "营业执照",
    "法人",
    "公章",
    "表格",
]


def _split_paragraphs(text: str) -> List[str]:
    parts = re.split(r"\n{1,}|\r{1,}", text)
    cleaned = [p.strip() for p in parts if p and len(p.strip()) > 10]
    return cleaned


def _parse_json_text(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    if t.startswith("```json"):
        t = t[7:]
    if t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    t = t.strip()
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start : end + 1]
    t = re.sub(r",(\s*[}\]])", r"\1", t)
    t = t.replace("True", "true").replace("False", "false")
    return json.loads(t)


def _norm_int(x: str) -> int:
    try:
        return int(x)
    except:
        return 1


def _fmt_date(y: int, m: int, d: int) -> str:
    y = _norm_int(y)
    m = _norm_int(m)
    d = _norm_int(d)
    y = 2000 if y < 100 else y
    m = 1 if m < 1 or m > 12 else m
    d = 1 if d < 1 or d > 31 else d
    return f"{y:04d}-{m:02d}-{d:02d}"


def _find_dates(text: str) -> List[str]:
    if not text:
        return []
    s = text
    rgx = [
        r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?",
        r"(\d{4})[年/-](\d{1,2})月",
        r"(\d{4})-(\d{1,2})-(\d{1,2})",
        r"(\d{4})/(\d{1,2})/(\d{1,2})",
    ]
    out = []
    for r in rgx:
        for m in re.finditer(r, s):
            g = m.groups()
            if len(g) == 3:
                out.append(_fmt_date(g[0], g[1], g[2]))
            elif len(g) == 2:
                out.append(_fmt_date(g[0], g[1], 1))
    uniq = []
    for x in out:
        if x not in uniq:
            uniq.append(x)
    return uniq


def _extract_date_range(text: str) -> Dict[str, str]:
    if not text:
        return {"开始日期": "", "截止日期": "", "日期范围文本": ""}
    s = text
    pat_range = [
        r"(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?).{0,5}(至|到|—|–|~|-).{0,5}(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?)",
        r"自?(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?)起?.{0,8}(至|到|截止至|截止到).{0,4}(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?)",
    ]
    for p in pat_range:
        m = re.search(p, s)
        if m:
            a, _, b = m.groups()
            ds = _find_dates(a) + _find_dates(b)
            if len(ds) >= 2:
                return {
                    "开始日期": ds[0],
                    "截止日期": ds[1],
                    "日期范围文本": m.group(0),
                }
    pat_deadline = r"(至|到|截止至|截止到)?\s*(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?)"
    m = re.search(pat_deadline, s)
    if m:
        ds = _find_dates(m.group(2))
        if ds:
            return {"开始日期": "", "截止日期": ds[0], "日期范围文本": m.group(0)}
    ds_all = _find_dates(s)
    if ds_all:
        end = ds_all[-1]
        start = ds_all[0] if len(ds_all) > 1 else ""
        return {"开始日期": start, "截止日期": end, "日期范围文本": ""}
    return {"开始日期": "", "截止日期": "", "日期范围文本": ""}


def _compute_standard_dates(res: Dict[str, Any], context: str) -> Dict[str, str]:
    txt = ""
    v = res.get("截止时间")
    if isinstance(v, str):
        txt += v + " "
    v2 = res.get("通知要点")
    if isinstance(v2, str):
        txt += v2 + " "
    if not txt and isinstance(context, str):
        txt = context
    rng = _extract_date_range(txt)
    return rng


def _select_relevant_by(text: str, keywords: List[str], max_chars: int = 4000) -> str:
    paras = _split_paragraphs(text)
    scored: List[tuple[int, str]] = []
    for p in paras:
        score = sum(1 for kw in keywords if kw in p)
        if score > 0:
            scored.append((score, p))
    if not scored:
        for p in paras:
            score = 1 if ("申报" in p and "材料" in p) else 0
            if score > 0:
                scored.append((score, p))
    if not scored:
        context = ""
        for p in paras:
            if len(context) + len(p) + 1 > max_chars:
                break
            context += p + "\n"
        return context[:max_chars]
    scored.sort(key=lambda x: x[0], reverse=True)
    context = ""
    for _, p in scored:
        if len(context) + len(p) + 1 > max_chars:
            break
        context += p + "\n"
    return context[:max_chars]


def _select_relevant(text: str, max_chars: int = 4000) -> str:
    return _select_relevant_by(text, MATERIAL_KEYWORDS, max_chars=max_chars)


def _coerce_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y", "是")
    return bool(v)


def _rule_is_application_related(title: str) -> bool:
    t = title or ""
    if any(k in t for k in EXCLUDE_KEYWORDS):
        return False
    return any(k in t for k in APPLICATION_KEYWORDS)


def analyze_materials_batch(notices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for item in notices:
        ai_res = item.get("分析结果")
        if not isinstance(ai_res, dict) or not ai_res:
            continue

        merged = dict(item)
        if "是否课题申报相关" in ai_res:
            is_related = _coerce_bool(ai_res.get("是否课题申报相关", False))
        else:
            is_related = _rule_is_application_related(item.get("标题") or "")

        directions = ai_res.get("申报方向", [])
        if isinstance(directions, str):
            directions = [directions] if directions.strip() and directions != "未明确" else []
        if not isinstance(directions, list):
            directions = []
        directions = [x for x in directions if isinstance(x, str) and x.strip() and x.strip() != "未明确"]

        merged["课题申报分析"] = {
            "是否课题申报相关": is_related,
            "相关性理由": ai_res.get("分析结论", "未明确") or "未明确",
            "通知要点": (ai_res.get("核心申报条件") or ai_res.get("征集内容") or "")[:200]
            or "未明确",
            "申报方向": directions,
            "错误": ai_res.get("错误原因", "") or "",
        }

        if is_related:
            materials = ai_res.get("材料清单", [])
            if isinstance(materials, str):
                materials = [materials] if materials.strip() and materials != "未明确" else []
            if not isinstance(materials, list):
                materials = []
            materials = [x for x in materials if isinstance(x, str) and x.strip() and x.strip() != "未明确"]

            deadline_text = ai_res.get("申报截止时间", "未明确")
            merged["材料提取"] = {
                "材料清单": materials,
                "提交方式": ai_res.get("提交方式", "未明确") or "未明确",
                "提交渠道": ai_res.get("提交渠道", "未明确") or "未明确",
                "份数与格式要求": ai_res.get("份数与格式要求", "未明确") or "未明确",
                "模板或表格下载": ai_res.get("模板或表格下载", "未明确") or "未明确",
                "截止时间": deadline_text or "未明确",
                "其他要求": ai_res.get("其他要求", "未明确") or "未明确",
            }
            merged["标准化日期"] = _extract_date_range(str(deadline_text or ""))
            results.append(merged)
    return results


if __name__ == "__main__":
    import sys
    import io

    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    if sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )
    input_path = os.path.join(os.path.dirname(__file__), "data", "crawl_results.json")
    output_path = os.path.join(
        os.path.dirname(__file__), "data", "materials_results.json"
    )
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        out = analyze_materials_batch(items)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(output_path)
    except Exception as e:
        print(str(e))
