# -*- coding: utf-8 -*-
"""
科研课题申报爬虫基类
"""
import requests
import time
import re
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseResearchCrawler(ABC):
    """科研课题申报爬虫基类"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def extract_date_from_text(self, text: str) -> Optional[str]:
        """
        从文本中提取日期
        支持格式：2024-01-01、2024年01月01日、2024/01/01
        Returns: YYYY-MM-DD 格式日期或 None
        """
        if not text:
            return None

        # 匹配 2024-01-01 或 2024/01/01
        pattern1 = r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})"
        # 匹配 2024年01月01日
        pattern2 = r"(\d{4})年(\d{1,2})月(\d{1,2})日"

        for pattern in [pattern1, pattern2]:
            match = re.search(pattern, text)
            if match:
                year, month, day = match.groups()
                try:
                    date_obj = datetime(int(year), int(month), int(day))
                    return date_obj.strftime("%Y-%m-%d")
                except:
                    continue
        return None

    def is_date_in_range(
        self, date_str: str, start_date: Optional[str], end_date: Optional[str]
    ) -> bool:
        """
        检查日期是否在指定范围内
        Args:
            date_str: 日期字符串 YYYY-MM-DD
            start_date: 开始日期（None表示不限制）
            end_date: 结束日期（None表示不限制）
        """
        if not date_str:
            return True  # 无法提取日期时默认包含

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            if start_date:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                if date_obj < start:
                    return False

            if end_date:
                end = datetime.strptime(end_date, "%Y-%m-%d")
                if date_obj > end:
                    return False

            return True
        except:
            return True  # 解析失败时默认包含

    @abstractmethod
    def get_site_name(self) -> str:
        """返回网站名称"""
        pass

    @abstractmethod
    def fetch_notice_list(
        self, list_url: str, max_pages: int = 3
    ) -> List[Dict[str, str]]:
        """
        抓取通知列表（支持分页）
        Args:
            list_url: 列表页URL
            max_pages: 最大抓取页数，默认3页
        Returns: [{"标题": "xxx", "链接": "xxx"}, ...]
        """
        pass

    @abstractmethod
    def fetch_notice_detail(self, detail_url: str) -> Dict[str, Any]:
        """
        抓取通知正文和发布日期
        Returns: {"content": 正文文本, "pub_date": 发布日期(YYYY-MM-DD或None)}
        """
        pass

    def should_include_notice(self, title: str) -> bool:
        """
        判断通知是否应该被包含
        默认实现：关键词过滤
        只保留正在申报/征集阶段的通知，排除结果公示、评审结束等
        """
        # 关键词：申报类、征集类
        keywords = [
            "申报",
            "智慧",
            "人工智能",
            "征集",
            "申请",
            "推荐",
            "遴选",
            "课题",
            "项目",
            "基金",
            "指南",
            "专项",
            "计划",
        ]
        # 排除关键词（结果类、已完结类、非申报类）
        exclude_keywords = [
            # 结果公示类（已结束）
            "公示",
            "结果",
            "评审结果",
            "拟立项",
            "立项公示",
            # 批复/核准类（已完成审批）
            "批复",
            "核准",
            "批准",
            "同意",
            # 完结类
            "备案",
            "获奖",
            "奖励",
            "颁奖",
            "验收",
            "评价",
            "决算",
            # 活动/调研类（非申报）
            "调研",
            "考察",
            "参观",
            "走访",
            "督导",
            "检查",
            "座谈",
            "宣讲",
            "宣贯会",  # 宣讲会
            # 其他无关
            "事务所",
            "审计",
            "预算",
            "培训",
            "会议",
            "补贴",
            "补助",
        ]

        has_keyword = any(word in title for word in keywords)
        has_exclude = any(word in title for word in exclude_keywords)

        return has_keyword and not has_exclude

    def build_full_url(self, href: str) -> str:
        """构建完整URL"""
        if href.startswith(("http://", "https://")):
            return href
        elif href.startswith("./"):
            return self.base_url.rstrip("/") + href[1:]
        elif href.startswith("/"):
            return self.base_url.rstrip("/") + href
        else:
            return self.base_url.rstrip("/") + "/" + href

    def get(self, url: str, timeout: int = 15) -> requests.Response:
        """发送GET请求"""
        return requests.get(url, headers=self.headers, timeout=timeout, verify=False)
