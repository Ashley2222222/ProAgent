# -*- coding: utf-8 -*-
import os
import re
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from config import AI_MODEL

load_dotenv()
API_KEY = os.getenv("AI_API_KEY")
MODEL_BLOCKED = False

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


def _fetch_page_text(url: str, timeout: int = 20) -> str:
    try:
        resp = requests.get(url, timeout=timeout, verify=False)
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.extract()
        text = soup.get_text("\n")
        return re.sub(r"\n{2,}", "\n", text)
    except Exception:
        return ""


def _quick_is_application_related(title: str) -> bool:
    if any(k in title for k in EXCLUDE_KEYWORDS):
        return False
    if any(k in title for k in APPLICATION_KEYWORDS):
        return True
    return False


def _quick_content_is_application(content: str) -> bool:
    """基于正文的快速规则判断是否与课题申报相关（不消耗token）"""
    if not content:
        return False
    # 强相关短语（必须出现至少一个）
    strong_phrases = [
        "申报",
        "项目申报",
        "申报工作",
        "申报通知",
        "申报材料",
        "申请书",
        "项目申报书",
        "截止时间",
        "报送",
        "申报指南",
        "申请指南",
        "请于",
        "前将",
        "电子版",
        "纸质版",
    ]
    content_lower = content[:30000]  # 只看前30000字符
    for phrase in strong_phrases:
        if phrase in content_lower:
            return True
    return False


import time
from requests.exceptions import RequestException


def _retry_request(
    url: str, headers: dict, json_data: dict, max_retries: int = 3
) -> dict:
    global MODEL_BLOCKED
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                url, headers=headers, json=json_data, timeout=60, verify=False
            )
            js = resp.json()
            if "choices" not in js:
                err = js.get("error", {}) if isinstance(js, dict) else {}
                msg = err.get("message") or err.get("code") or str(js)[:200]
                if "inference limit" in str(msg) or "Safe Experience Mode" in str(msg):
                    MODEL_BLOCKED = True
                    raise ValueError(f"Model blocked: {msg}")
                raise ValueError(msg)
            return js
        except RequestException as e:
            last_error = e
            time.sleep(2**attempt)
        except ValueError as e:
            last_error = e
            if MODEL_BLOCKED:
                break
            time.sleep(2**attempt)
    raise last_error or Exception("Max retries exceeded")


def _call_llm_for_application(title: str, context: str) -> Dict[str, Any]:
    print(f"[DEBUG] 调用 AI 模型: {AI_MODEL}")
    global MODEL_BLOCKED
    if not API_KEY:
        return {
            "是否课题申报相关": False,
            "相关性理由": "缺少AI_API_KEY",
            "通知要点": "未明确",
            "申报方向": [],
            "材料清单": [],
            "提交方式": "未明确",
            "提交渠道": "未明确",
            "份数与格式要求": "未明确",
            "模板或表格下载": "未明确",
            "截止时间": "未明确",
            "其他要求": "未明确",
        }
    if MODEL_BLOCKED:
        return {
            "是否课题申报相关": False,
            "相关性理由": "模型服务暂停",
            "通知要点": "未明确",
            "申报方向": [],
            "材料清单": [],
            "提交方式": "未明确",
            "提交渠道": "未明确",
            "份数与格式要求": "未明确",
            "模板或表格下载": "未明确",
            "截止时间": "未明确",
            "其他要求": "未明确",
            "错误": "模型服务暂停",
        }
    prompt = (
        "你是科研课题申报分析助手。"
        "先判断通知是否与课题/项目申报相关；仅当相关时，提取申报方向并梳理申报材料。"
        "只输出JSON，不要任何解释或代码块。"
        '严格输出以下字段，信息缺失填"未明确"，列表为空用[]，严禁臆测：'
        "{"
        '"是否课题申报相关": true/false,'
        '"相关性理由":"一句话说明",'
        '"通知要点":"用要点总结通知内容",'
        '"申报方向":["方向/领域/专题（尽量短）"],'
        '"材料清单":["逐条列出材料名称及要点"],'
        '"提交方式":"线上/纸质/两者及送达方式",'
        '"提交渠道":"系统名称/邮箱/地址等",'
        '"份数与格式要求":"份数、纸质/电子及格式要求",'
        '"模板或表格下载":"是否提供下载及描述",'
        '"截止时间":"如出现则提取",'
        '"其他要求":"其他与申报/材料相关注意事项"'
        "}"
        f"\n标题：{title}\n上下文：{context[:3900]}"
    )
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }
    data = {
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    try:
        js = _retry_request(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions", headers, data
        )
        txt = js["choices"][0]["message"]["content"]
        return _parse_json_text(txt)
    except Exception as e:
        last_error = e

    return {
        "是否课题申报相关": False,
        "相关性理由": "解析失败",
        "通知要点": "未明确",
        "申报方向": [],
        "材料清单": [],
        "提交方式": "未明确",
        "提交渠道": "未明确",
        "份数与格式要求": "未明确",
        "模板或表格下载": "未明确",
        "截止时间": "未明确",
        "其他要求": "未明确",
        "错误": str(last_error) if last_error else "未知错误",
    }


def _call_llm(title: str, context: str) -> Dict[str, Any]:
    global MODEL_BLOCKED
    if not API_KEY:
        print(f"[DEBUG] API_KEY 未配置")
        return {
            "材料清单": [],
            "提交方式": "未明确",
            "提交渠道": "未明确",
            "份数与格式要求": "未明确",
            "模板或表格下载": "未明确",
            "截止时间": "未明确",
            "其他要求": "未明确",
            "错误": "缺少AI_API_KEY",
        }
    if MODEL_BLOCKED:
        return {
            "材料清单": [],
            "提交方式": "未明确",
            "提交渠道": "未明确",
            "份数与格式要求": "未明确",
            "模板或表格下载": "未明确",
            "截止时间": "未明确",
            "其他要求": "未明确",
            "错误": "模型服务暂停",
        }
    prompt = (
        "你是科研课题申报材料解析助手。"
        "只输出JSON，不要任何解释或代码块。"
        "根据给定的标题与上下文，提取申报材料信息："
        '{"材料清单": ["逐条列出材料名称及要点"],'
        '"提交方式":"纸质/线上及送达方式",'
        '"提交渠道":"系统名称/邮箱/地址等",'
        '"份数与格式要求":"份数、纸质/电子及格式要求",'
        '"模板或表格下载":"是否提供下载及链接描述",'
        '"截止时间":"如出现则提取",'
        '"其他要求":"其他与材料相关的限制或注意事项"}'
        '若信息缺失，填"未明确"。严禁臆测。'
        f"\n标题：{title}\n上下文：{context[:3900]}"
    )
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }
    data = {
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    try:
        js = _retry_request(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions", headers, data
        )
        txt = js["choices"][0]["message"]["content"]
        return _parse_json_text(txt)
    except Exception as e:
        return {
            "材料清单": [],
            "提交方式": "未明确",
            "提交渠道": "未明确",
            "份数与格式要求": "未明确",
            "模板或表格下载": "未明确",
            "截止时间": "未明确",
            "其他要求": "未明确",
            "错误": str(e),
        }


def extract_materials_for_notice(
    title: str, content: str, link: str | None = None
) -> Dict[str, Any]:
    ctx = _select_relevant(content or "")
    if len(ctx) < 300 and link:
        page_text = _fetch_page_text(link)
        if page_text:
            ctx = _select_relevant(page_text)
    return _call_llm(title, ctx)


def analyze_application_notice(
    title: str, content: str, link: str | None = None
) -> Dict[str, Any]:
    ctx = _select_relevant_by(
        content or "", APPLICATION_KEYWORDS + MATERIAL_KEYWORDS, max_chars=4000
    )
    if len(ctx) < 300 and link:
        page_text = _fetch_page_text(link)
        if page_text:
            ctx = _select_relevant_by(
                page_text, APPLICATION_KEYWORDS + MATERIAL_KEYWORDS, max_chars=4000
            )
    res = _call_llm_for_application(title, ctx)
    std_dates = _compute_standard_dates(res, ctx)
    res["标准化日期"] = std_dates
    if res.get("错误"):
        directions: List[str] = []
        m = re.search(r"围绕(.{0,160}?)(?:四大|三大|五大|六大)(?:板块|专题板块)", ctx)
        if m:
            parts = [
                p.strip(" ，,。；;")
                for p in re.split(r"[、,，]", m.group(1))
                if p.strip()
            ]
            directions.extend(parts[:12])
        m2 = re.search(r"形成了“(.{0,120}?)”等若干个主题研究方向", ctx)
        if m2:
            directions.append(m2.group(1).strip())
        key_paras = [
            p
            for p in _split_paragraphs(ctx)
            if any(k in p for k in ["方向", "领域", "专题", "板块"])
        ]
        if not directions and key_paras:
            directions = [key_paras[0][:80]]
        directions = [
            d for i, d in enumerate(directions) if d and d not in directions[:i]
        ]
        return {
            "是否课题申报相关": True,
            "相关性理由": "规则判断：标题包含申报类关键词",
            "通知要点": (ctx[:200] + "...") if len(ctx) > 200 else (ctx or "未明确"),
            "申报方向": directions,
            "材料清单": [],
            "提交方式": "未明确",
            "提交渠道": "未明确",
            "份数与格式要求": "未明确",
            "模板或表格下载": "未明确",
            "截止时间": "未明确",
            "其他要求": "未明确",
            "错误": res.get("错误"),
            "标准化日期": std_dates,
        }
    return res


def analyze_materials_batch(notices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for item in notices:
        title = item.get("标题") or ""
        content = item.get("正文预览") or ""
        link = item.get("链接")
        merged = dict(item)
        related = _quick_is_application_related(title)
        if related:
            # 新增：正文规则快速过滤，避免无关通知消耗token
            if not _quick_content_is_application(content):
                continue
            app = analyze_application_notice(title, content, link)
            merged["课题申报分析"] = {
                "是否课题申报相关": bool(app.get("是否课题申报相关")),
                "相关性理由": app.get("相关性理由", "未明确"),
                "通知要点": app.get("通知要点", "未明确"),
                "申报方向": (
                    app.get("申报方向", [])
                    if isinstance(app.get("申报方向"), list)
                    else []
                ),
                "错误": app.get("错误", ""),
            }
            if bool(app.get("是否课题申报相关")):
                merged["材料提取"] = {
                    "材料清单": app.get("材料清单", []),
                    "提交方式": app.get("提交方式", "未明确"),
                    "提交渠道": app.get("提交渠道", "未明确"),
                    "份数与格式要求": app.get("份数与格式要求", "未明确"),
                    "模板或表格下载": app.get("模板或表格下载", "未明确"),
                    "截止时间": app.get("截止时间", "未明确"),
                    "其他要求": app.get("其他要求", "未明确"),
                }
                merged["标准化日期"] = app.get(
                    "标准化日期", {"开始日期": "", "截止日期": "", "日期范围文本": ""}
                )
                results.append(merged)
        # 非相关记录不写入
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
