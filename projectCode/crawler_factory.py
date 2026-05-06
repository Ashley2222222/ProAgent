# -*- coding: utf-8 -*-
"""
爬虫工厂类
管理所有网站配置和爬虫实例创建
"""
from typing import Dict
from crawlers import (
    BaseResearchCrawler,
    GDSTCrawler,
    GZKJJCrawler,
    HuaduCrawler,
    GDDRCrawler,
    GDIIcrawler,
    GDSWCrawler,
    GDMRCrawler,
    GZFGWCrawler,
    GZGXICrawler,
    GZSWcrawler,
    GZSCcrawler,
)


class ResearchCrawlerFactory:
    """爬虫工厂类"""

    # 网站配置
    SITE_CONFIGS = {
        "gdstc.gd.gov.cn": {
            "class": GDSTCrawler,
            "base_url": "https://gdstc.gd.gov.cn",
            "list_urls": [  # 支持多个列表页
                {"url": "https://gdstc.gd.gov.cn/zwgk_n/tzgg/", "name": "通知公告"},
                {
                    "url": "https://gdstc.gd.gov.cn/zwgk_n/zdly/zjzn/index.html",
                    "name": "重点领域-资金指南",
                },
            ],
            "description": "广东省科学技术厅",
            "max_pages": 5,  # 抓取5页
        },
        "kjj.gz.gov.cn": {
            "class": GZKJJCrawler,
            "base_url": "https://kjj.gz.gov.cn",
            "list_urls": [
                {
                    "url": "http://kjj.gz.gov.cn/xxgk/kjglhxmjf/index.html",
                    "name": "科技管理和项目经费",
                },
            ],
            "description": "广州市科学技术局",
            "max_pages": 3,
        },
        "huadu.gov.cn": {
            "class": HuaduCrawler,
            "base_url": "https://www.huadu.gov.cn",
            "list_urls": [
                {
                    "url": "https://www.huadu.gov.cn/gzhdkgsx/gkmlpt/index",
                    "name": "信息公开平台",
                },
            ],
            "description": "花都区科技工业商务和信息化局",
            "max_pages": 3,
        },
        "drc.gd.gov.cn": {
            "class": GDDRCrawler,
            "base_url": "https://drc.gd.gov.cn",
            "list_urls": [
                {
                    "url": "https://drc.gd.gov.cn/gggs5623/index.html",
                    "name": "公告公示",
                },
                {"url": "https://drc.gd.gov.cn/ywtz/index.html", "name": "业务通知"},
            ],
            "description": "广东省发展和改革委员会",
            "max_pages": 3,
        },
        "gdii.gd.gov.cn": {
            "class": GDIIcrawler,
            "base_url": "https://gdii.gd.gov.cn",
            "list_urls": [
                {"url": "https://gdii.gd.gov.cn/zwgk/tzgg1011/", "name": "通知公告"},
            ],
            "description": "广东省工业和信息化厅",
            "max_pages": 3,
        },
        "com.gd.gov.cn": {
            "class": GDSWCrawler,
            "base_url": "https://com.gd.gov.cn",
            "list_urls": [
                {"url": "https://com.gd.gov.cn/zwgk/gggs/", "name": "公告公示"},
                {"url": "https://com.gd.gov.cn/zwgk/ywtz/", "name": "业务通知"},
            ],
            "description": "广东省商务厅",
            "max_pages": 3,
        },
        "amr.gd.gov.cn": {
            "class": GDMRCrawler,
            "base_url": "https://amr.gd.gov.cn",
            "list_urls": [
                {"url": "https://amr.gd.gov.cn/zwgk/tzgg/", "name": "通知公告"},
            ],
            "description": "广东省市场监督管理局",
            "max_pages": 3,
        },
        "fgw.gz.gov.cn": {
            "class": GZFGWCrawler,
            "base_url": "http://fgw.gz.gov.cn",
            "list_urls": [
                {"url": "http://fgw.gz.gov.cn/tzgg/", "name": "通知公告"},
            ],
            "description": "广州市发展和改革委员会",
            "max_pages": 3,
        },
        "gxj.gz.gov.cn": {
            "class": GZGXICrawler,
            "base_url": "https://gxj.gz.gov.cn",
            "list_urls": [
                {"url": "https://gxj.gz.gov.cn/yw/tzgg/", "name": "通知公告"},
            ],
            "description": "广州市工业和信息化局",
            "max_pages": 3,
        },
        "sw.gz.gov.cn": {
            "class": GZSWcrawler,
            "base_url": "http://sw.gz.gov.cn",
            "list_urls": [
                {"url": "http://sw.gz.gov.cn/xxgk/tzgg/", "name": "通知公告"},
            ],
            "description": "广州市商务局",
            "max_pages": 3,
        },
        "scjgj.gz.gov.cn": {
            "class": GZSCcrawler,
            "base_url": "http://scjgj.gz.gov.cn",
            "list_urls": [
                {"url": "http://scjgj.gz.gov.cn/zwdt/tzgg/", "name": "通知公告"},
            ],
            "description": "广州市市场监督管理局(知识产权)",
            "max_pages": 3,
        },
    }

    @classmethod
    def create_crawler(cls, site_key: str) -> BaseResearchCrawler:
        """创建爬虫实例"""
        if site_key not in cls.SITE_CONFIGS:
            raise ValueError(f"不支持的网站: {site_key}")

        config = cls.SITE_CONFIGS[site_key]
        return config["class"](config["base_url"])

    @classmethod
    def get_all_sites(cls) -> Dict[str, Dict[str, str]]:
        """获取所有网站配置"""
        return cls.SITE_CONFIGS
