#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 网易财经爬虫
专门针对网易财经网站的爬虫实现
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from app.crawlers.core import BaseCrawler
from app.crawlers.strategies.netease_strategy import NeteaseStrategy
from app.utils.logger import get_logger

logger = get_logger('netease_crawler')

class NeteaseCrawler(BaseCrawler):
    """网易财经爬虫实现"""
    
    source = "网易财经"
    
    def __init__(self, db_path: str = None, **kwargs):
        """
        初始化网易财经爬虫
        
        Args:
            db_path: 数据库路径
            **kwargs: 其他参数
        """
        # 创建策略实例
        strategy = NeteaseStrategy()
        
        # 调用父类初始化
        super().__init__(
            source=self.source,
            strategy=strategy,
            db_path=db_path,
            **kwargs
        )
        
        # 确保数据库路径存在
        if db_path:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        logger.info(f"网易财经爬虫初始化完成，使用数据库: {db_path}")
    
    async def fetch_page(self, url: str) -> str:
        """获取页面内容"""
        return await self.http_client.fetch(url)
    
    async def crawl_async(self, days: int = 1, max_news: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """异步爬取方法"""
        try:
            # 获取列表页URL
            list_urls = self.strategy.get_list_page_urls(days, category)
            logger.info(f"获取到 {len(list_urls)} 个列表页URL")
            
            news_list = []
            for list_url in list_urls:
                # 获取列表页内容
                list_html = await self.http_client.fetch(list_url)
                if not list_html:
                    continue
                
                # 解析文章URL
                article_urls = self.strategy.parse_list_page(list_html, list_url)
                
                # 爬取文章
                for article_url in article_urls:
                    if len(news_list) >= max_news:
                        break
                        
                    article_html = await self.http_client.fetch(article_url)
                    if not article_html:
                        continue
                    
                    article = self.strategy.parse_detail_page(article_html, article_url)
                    if article:
                        self.save_news_to_db(article)
                        news_list.append(article)
            
            return news_list
            
        except Exception as e:
            logger.error(f"网易财经爬虫运行出错: {str(e)}")
            return []
    
    def crawl(self, days: int = 1, max_news: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """同步爬取方法"""
        try:
            # 获取列表页URL
            list_urls = self.strategy.get_list_page_urls(days, category)
            logger.info(f"获取到 {len(list_urls)} 个列表页URL")
            
            news_list = []
            for list_url in list_urls:
                # 获取列表页内容
                list_html = self.http_client.fetch(list_url)
                if not list_html:
                    continue
                
                # 解析文章URL
                article_urls = self.strategy.parse_list_page(list_html, list_url)
                
                # 爬取文章
                for article_url in article_urls:
                    if len(news_list) >= max_news:
                        break
                        
                    article_html = self.http_client.fetch(article_url)
                    if not article_html:
                        continue
                    
                    article = self.strategy.parse_detail_page(article_html, article_url)
                    if article:
                        self.save_news_to_db(article)
                        news_list.append(article)
            
            return news_list
        except Exception as e:
            logger.error(f"网易财经爬虫运行出错: {str(e)}")
            return []
    
    def save_news(self, article: Dict[str, Any]) -> bool:
        """Convenience method for saving news"""
        return self.save_news_to_db(article) 