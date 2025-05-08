#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 东方财富爬虫 (新架构)
基于统一爬虫架构的东方财富爬虫实现
"""

from typing import Dict, List, Any, Optional
import os
import re
import hashlib
from datetime import datetime
from urllib.parse import urljoin

from app.crawlers.core.base_crawler import BaseCrawler
from app.crawlers.strategies.eastmoney_strategy import EastMoneyStrategy
from app.utils.logger import get_logger
from app.utils.text_cleaner import clean_html, decode_html_entities, decode_unicode_escape
from app.utils.sentiment_analyzer import SentimentAnalyzer

# 使用专门的日志记录器
logger = get_logger('eastmoney_crawler')


class EastMoneyCrawler(BaseCrawler):
    """
    基于新架构的东方财富爬虫实现
    
    此类继承自统一的BaseCrawler，并使用EastMoneyStrategy处理网站特定的爬取逻辑
    """
    
    def __init__(self, db_path: str = None, **options):
        """
        初始化东方财富爬虫
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            **options: 其他配置选项
        """
        source = "东方财富"
        
        # 如果未提供db_path，尝试从环境中获取
        if db_path is None:
            from app.config import get_settings
            settings = get_settings()
            db_dir = settings.get('DB_DIR')
            if not db_dir:
                db_dir = os.path.join(os.getcwd(), 'data', 'db')
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, f"{source}.db")
            
        # 设置选项默认值
        options.setdefault('async_mode', True)       # 默认使用异步模式
        options.setdefault('max_concurrency', 10)    # 最大并发请求数
        options.setdefault('batch_size', 20)         # 批处理大小
        
        # 初始化情感分析器和其他组件
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # 调用父类构造函数
        super().__init__(source, db_path, **options)
        
        logger.info(f"东方财富爬虫初始化完成，数据库路径: {db_path}")
        
    def _create_strategy(self):
        """
        创建东方财富爬虫策略实例
        
        Returns:
            EastMoneyStrategy: 策略实例
        """
        return EastMoneyStrategy(self.source)
    
    def preprocess_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理文章数据
        
        Args:
            article: 文章数据字典
            
        Returns:
            Dict[str, Any]: 处理后的文章数据
        """
        # 调用父类的预处理方法
        article = super().preprocess_article(article) if hasattr(super(), 'preprocess_article') else article
        
        # 生成ID（如果没有）
        if 'id' not in article or not article['id']:
            if 'url' in article and article['url']:
                article['id'] = hashlib.md5(article['url'].encode('utf-8')).hexdigest()
            else:
                article['id'] = hashlib.md5((article.get('title', '') + str(datetime.now())).encode('utf-8')).hexdigest()
        
        # 提取和清洗图片
        if 'images' in article and article['images'] and isinstance(article['images'], list):
            try:
                # 清理图片URL
                cleaned_images = []
                for img in article['images']:
                    if isinstance(img, dict) and 'url' in img:
                        img_url = img['url']
                    else:
                        img_url = str(img)
                    
                    # 确保URL是完整的
                    if img_url and not img_url.startswith(('http://', 'https://')):
                        if 'url' in article and article['url']:
                            img_url = urljoin(article['url'], img_url)
                    
                    if img_url:
                        cleaned_images.append(img_url)
                
                article['images'] = cleaned_images
            except Exception as e:
                logger.error(f"处理图片失败: {str(e)}")
        
        # 进行情感分析
        if 'content' in article and article['content'] and not article.get('sentiment'):
            try:
                sentiment = self.sentiment_analyzer.analyze(article['content'])
                article['sentiment'] = sentiment
            except Exception as e:
                logger.error(f"情感分析失败: {str(e)}")
        
        # 设置分类
        if not article.get('category') and not article.get('classification'):
            article['category'] = '财经'
            
        # 确保来源正确
        article['source'] = self.source
        
        return article

    # 兼容旧接口的方法
    def crawl_with_old_api(self, days=1, max_news=None):
        """
        兼容旧接口的爬取方法
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取数量
            
        Returns:
            List[Dict[str, Any]]: 爬取的新闻列表
        """
        categories = list(self.strategy.categories.keys())
        all_news = []
        
        # 对每个分类进行爬取
        for category in categories:
            news = self.crawl(days=days, max_news=max_news, category=category)
            all_news.extend(news)
            
            # 检查是否达到最大爬取数量
            if max_news and len(all_news) >= max_news:
                all_news = all_news[:max_news]
                break
                
        return all_news


# 适配器 - 将旧接口调用适配到新架构
class EastMoneyCrawlerAdapter:
    """
    东方财富爬虫适配器，使旧接口调用能够使用新架构
    """
    
    def __init__(self, db_path: str = None, **options):
        """
        初始化适配器
        
        Args:
            db_path: 数据库路径
            **options: 其他配置选项
        """
        self.crawler = EastMoneyCrawler(db_path, **options)
        
    def crawl(self, days=1, max_news=None, **kwargs):
        """
        爬取方法，与旧接口保持一致
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取数量
            **kwargs: 其他参数
            
        Returns:
            List[Dict[str, Any]]: 爬取的新闻列表
        """
        return self.crawler.crawl_with_old_api(days=days, max_news=max_news)
        
    def __getattr__(self, name):
        """
        转发未实现的方法到实际的爬虫实例
        
        Args:
            name: 方法名
            
        Returns:
            任何类型: 转发调用的结果
        """
        return getattr(self.crawler, name) 