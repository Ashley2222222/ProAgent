# -*- coding: utf-8 -*-
"""
爬虫模块
包含各个政府网站的爬虫实现
"""
from .base import BaseResearchCrawler
from .gdstc import GDSTCrawler
from .gzkjj import GZKJJCrawler
from .huadu import HuaduCrawler
from .gddrc import GDDRCrawler
from .gdii import GDIIcrawler
from .gdsw import GDSWCrawler
from .gdmr import GDMRCrawler
from .gzfgw import GZFGWCrawler
from .gzgxi import GZGXICrawler
from .gzsw import GZSWcrawler
from .gzsc import GZSCcrawler

__all__ = [
    "BaseResearchCrawler",
    "GDSTCrawler",
    "GZKJJCrawler",
    "HuaduCrawler",
    "GDDRCrawler",
    "GDIIcrawler",
    "GDSWCrawler",
    "GDMRCrawler",
    "GZFGWCrawler",
    "GZGXICrawler",
    "GZSWcrawler",
    "GZSCcrawler",
]
