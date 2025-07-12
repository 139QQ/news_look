#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一爬虫架构 - 核心模块
提供统一的爬虫接口和组件
"""

from backend.app.crawlers.core.base_crawler import BaseCrawler
from backend.app.crawlers.core.http_client import BaseHttpClient, SyncHttpClient, AsyncHttpClient
from backend.app.crawlers.core.data_processor import DataProcessor
from backend.app.crawlers.core.declarative_crawler import DeclarativeCrawlerStrategy
from backend.app.crawlers.enhanced_crawler import EnhancedCrawler

__all__ = [
    'BaseCrawler',
    'BaseHttpClient',
    'SyncHttpClient',
    'AsyncHttpClient',
    'DataProcessor',
    'DeclarativeCrawlerStrategy',
    'EnhancedCrawler'
] 