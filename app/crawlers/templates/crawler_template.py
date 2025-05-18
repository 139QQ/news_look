#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 基于新架构的爬虫模板
用于帮助迁移现有爬虫到新的统一架构
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from app.crawlers.core.base_crawler import BaseCrawler
from app.crawlers.strategies.base_strategy import BaseCrawlerStrategy
from app.utils.logger import get_logger

# 使用专门的日志记录器
logger = get_logger('crawler_template')


class NewCrawler(BaseCrawler):
    """
    基于新架构的爬虫模板类
    
    使用方法:
    1. 复制此模板
    2. 将NewCrawler改为具体的爬虫名称（如EastMoneyCrawler）
    3. 配置source参数为正确的来源名称
    4. 实现自定义方法（如有）
    5. 如有需要，重写_create_strategy方法以使用特定配置初始化策略
    """
    
    def __init__(self, source: str, db_path: str, **options):
        """
        初始化爬虫
        
        Args:
            source: 数据源名称，应与策略映射表中的键匹配
            db_path: 数据库路径
            **options: 其他配置选项
        """
        # 调用父类构造函数
        super().__init__(source, db_path, **options)
        
        # 在这里可以添加爬虫特有的初始化代码
        # 例如，初始化特定的组件、设置等
        
        logger.info(f"{source}爬虫初始化完成")
    
    def _create_strategy(self) -> BaseCrawlerStrategy:
        """
        创建策略实例
        
        如果需要为策略传递特殊参数，可以重写此方法
        
        Returns:
            BaseCrawlerStrategy: 策略实例
        """
        from app.crawlers.strategies import get_strategy
        
        # 获取策略类
        strategy_class = get_strategy(self.source)
        if not strategy_class:
            raise ValueError(f"未找到源 '{self.source}' 对应的爬虫策略")
            
        # 创建策略实例，可以传递自定义参数
        return strategy_class(self.source)
    
    # 如果有特殊的爬取方法，可以在这里实现
    # 建议只添加当前爬虫特有的功能，通用功能应在BaseCrawler中实现
    
    def preprocess_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理文章数据
        
        此方法在保存文章前调用，可以进行特定的数据处理
        
        Args:
            article: 文章数据字典
            
        Returns:
            Dict[str, Any]: 处理后的文章数据
        """
        # 示例：添加自定义字段
        if 'title' in article and article['title']:
            article['title'] = article['title'].strip()
            
        # 设置来源
        if 'source' not in article or not article['source']:
            article['source'] = self.source
            
        return article
    
    # 兼容旧接口的方法，方便迁移
    def crawl_legacy(self, days=1, max_news=None, category=None) -> List[Dict[str, Any]]:
        """
        兼容旧接口的爬取方法
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取数量
            category: 爬取的新闻分类
            
        Returns:
            List[Dict[str, Any]]: 爬取的新闻列表
        """
        return self.crawl(days=days, max_news=max_news, category=category)


# 适配器示例 - 如何使旧代码调用新架构
class CrawlerAdapter:
    """
    爬虫适配器，将旧接口调用适配到新架构
    
    使用示例:
    ```python
    # 旧代码
    crawler = SinaCrawler()
    news = crawler.crawl(days=3)
    
    # 使用适配器
    adapter = CrawlerAdapter('新浪财经', db_path)
    news = adapter.crawl(days=3)
    ```
    """
    
    def __init__(self, source: str, db_path: str, use_async: bool = True, **options):
        """
        初始化适配器
        
        Args:
            source: 数据源名称
            db_path: 数据库路径
            use_async: 是否使用异步模式
            **options: 其他配置选项
        """
        # 设置默认选项
        options.setdefault('async_mode', use_async)
        
        # 创建新架构爬虫实例
        self.crawler = NewCrawler(source, db_path, **options)
        
    def crawl(self, days=1, max_news=None, category=None, **kwargs) -> List[Dict[str, Any]]:
        """
        爬取方法，与旧接口保持一致
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大爬取数量
            category: 爬取的新闻分类
            **kwargs: 其他参数
            
        Returns:
            List[Dict[str, Any]]: 爬取的新闻列表
        """
        return self.crawler.crawl(days=days, max_news=max_news, category=category)
        
    def __getattr__(self, name):
        """
        转发未实现的方法到实际的爬虫实例
        
        Args:
            name: 方法名
            
        Returns:
            任何类型: 转发调用的结果
        """
        return getattr(self.crawler, name) 