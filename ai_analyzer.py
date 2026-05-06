# -*- coding: utf-8 -*-
"""
AI分析模块
调用豆包AI分析通知内容，提取申报信息
"""

import json
import os
from dotenv import load_dotenv
import requests
from config import AI_MODEL

# 加载环境变量
load_dotenv()
API_KEY = os.getenv("AI_API_KEY")


class ResearchAIAnalyzer:
    """科研课题AI分析器"""

    def __init__(self):
        self.api_key = API_KEY
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        self.model = AI_MODEL  # 已开通的模型ID

    def analyze_notice(self, title: str, content: str) -> dict:
        """
        分析通知内容，提取申报信息
        Returns: {"项目名称": "", "申报截止时间": "", ...}
        """
        if not self.api_key:
            return self._get_error_result("未读取到API Key，请检查.env文件")

        prompt = self._build_prompt(title, content)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }

        # 重试机制
        max_retries = 2
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    self.api_url, headers=headers, json=data, timeout=60, verify=False
                )

                result = resp.json()
                if "choices" in result:
                    return self._parse_ai_response(
                        result["choices"][0]["message"]["content"]
                    )
                else:
                    return self._get_error_result(
                        f"平台返回错误：{result.get('error', {}).get('message', '未知错误')}"
                    )

            except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
                if attempt < max_retries - 1:
                    print(f"  ⏳ API请求超时，第{attempt + 1}次重试...")
                    import time

                    time.sleep(2)
                    continue
                return self._get_error_result(
                    f"API请求超时（已重试{max_retries}次）：{str(e)[:100]}"
                )
            except requests.exceptions.SSLError:
                return self._get_error_result("SSL证书验证失败")
            except requests.exceptions.ConnectionError:
                return self._get_error_result("网络连接超时，请检查网络")
            except json.JSONDecodeError:
                return self._get_error_result("接口返回非JSON格式，可能是API Key无效")
            except Exception as e:
                return self._get_error_result(f"未知异常：{str(e)[:100]}")

    def _build_prompt(self, title: str, content: str) -> str:
        """构建AI提示词"""
        return f"""
你是科研课题申报专家，仅输出JSON格式内容，不添加任何额外解释、文字、符号或代码块。
从以下通知中提取申报相关信息，严格按照以下字段输出，字段值若未找到则填充为"未明确"：
{{
    "项目名称": "从标题和内容中提取项目名称",
    "申报截止时间": "提取所有时间信息，包括申报、提交材料、评审等时间节点",
    "申报主体": "明确申报单位要求（如高校、科研院所、企业等）",
    "资助类型": "资助金额、经费类型或资助方式",
    "核心申报条件": "申报资格、技术要求、研究内容、成果形式等所有要求",
    "征集内容": "具体征集的研究方向、技术领域、课题内容",
    "申报流程": "申报步骤、材料清单、提交方式",
    "联系方式": "提取所有联系电话、电子邮箱、联系人、地址等信息",
    "分析结论": "判断是否符合课题申报，给出简要分析",
    "风险提示": "提醒潜在风险和注意事项"
}}

通知标题：{title}
通知内容：{content[:4000]}
"""

    def _parse_ai_response(self, ai_text: str) -> dict:
        """解析AI返回的JSON文本"""
        try:
            # 清理可能的markdown代码块标记
            cleaned_text = ai_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]

            return json.loads(cleaned_text.strip())
        except json.JSONDecodeError:
            return {
                "分析结论": "AI返回格式异常",
                "错误原因": f"返回内容非标准JSON：{ai_text[:200]}",
                "项目名称": "未明确",
                "申报截止时间": "未明确",
                "申报主体": "未明确",
                "资助类型": "未明确",
                "核心申报条件": "未明确",
                "征集内容": "未明确",
                "申报流程": "未明确",
                "联系方式": "未明确",
                "风险提示": "未明确",
            }

    def _get_error_result(self, error_msg: str) -> dict:
        """获取错误结果模板"""
        return {
            "分析结论": "API调用失败",
            "错误原因": error_msg,
            "项目名称": "未明确",
            "申报截止时间": "未明确",
            "申报主体": "未明确",
            "资助类型": "未明确",
            "核心申报条件": "未明确",
            "征集内容": "未明确",
            "申报流程": "未明确",
            "联系方式": "未明确",
            "风险提示": "未明确",
        }
