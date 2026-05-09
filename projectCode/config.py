# -*- coding: utf-8 -*-
"""
配置文件
在此修改爬虫系统的配置参数
"""

# ========== AI分析配置 ==========

# 是否启用AI分析
# True: 启用AI分析（需要配置API Key），False: 仅爬取和打印信息
ENABLE_AI_ANALYSIS = True

# 是否自动为高价值通知生成《项目申报建议书》(Markdown初稿)
ENABLE_AUTO_PROPOSAL = True

# ========== 爬取配置 ==========

# 是否限制每个网站分析的通知数量
# True: 限制数量（节省时间和token），False: 分析所有符合要求的通知（推荐）
LIMIT_NOTICES_PER_SITE = False

# 每个网站最多分析的通知数量（仅在 LIMIT_NOTICES_PER_SITE = True 时生效）
MAX_NOTICES_PER_SITE = 3

# 说明：
# 系统已经通过关键词过滤和日期范围过滤，剩下的都是符合要求的通知
# 建议设置为 False，分析所有符合要求的通知，避免错过重要信息
# 如果网站通知非常多，可以设置为 True 限制数量，节省时间和token

# ========== 时间段配置 ==========
# 设置搜索的时间范围，格式："YYYY-MM-DD"
# 设置为 None 表示不限制时间
DATE_RANGE = {
    "start_date": "2026-04-01",  # 开始日期（包含）
    "end_date": "2026-04-30",  # 结束日期（包含）
}

# 示例配置：
# DATE_RANGE = {"start_date": "2026-03-01", "end_date": "2026-03-31"}  # 只搜索3月份
# DATE_RANGE = {"start_date": None, "end_date": None}  # 搜索所有时间

# ========== 输出配置 ==========
import os

# 获取本文件所在目录（即 ProAgent 目录）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_DIR 为绝对路径
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data")

RESULT_FILENAME = "crawl_results.json"  # 结果文件名
RAG_RESULT_FILENAME = "materials_results.json"

# ========== 企业微信配置 ==========
# 企业微信群Webhook地址
WECHAT_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=785959de-4802-4810-a986-ffabd88a807a"

# 是否启用企业微信消息推送#false不做推送 true做推送
ENABLE_WECHAT_NOTIFICATION = False

# 企业微信推送内容开关（ENABLE_WECHAT_NOTIFICATION=True 时生效）
ENABLE_WECHAT_MARKDOWN = False
ENABLE_WECHAT_FILE = True

# ========== AI模型配置 ==========
# 豆包模型名称或接入点ID# 修改为你将要使用的新模型名称或接入点ID
# AI_MODEL = "doubao-1-5-lite-32k-250115"
# AI_MODEL = "doubao-seed-1-6-lite-251015"
AI_MODEL = "doubao-1-5-pro-32k-250115"
