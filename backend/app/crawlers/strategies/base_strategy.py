#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫策略基类
定义网站特定爬取规则的接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class BaseCrawlerStrategy(ABC):
    """爬虫策略基类，定义爬取规则的接口"""
    
    def __init__(self, source: str):
        """
        初始化策略
        
        Args:
            source: 数据源名称
        """
        self.source = source
        self.categories = {}  # 分类映射表
    
    @abstractmethod
    def get_list_page_urls(self, days: int = 1, category: Optional[str] = None) -> List[str]:
        """
        获取列表页URL
        
        Args:
            days: 爬取最近几天的新闻
            category: 新闻分类
            
        Returns:
            List[str]: 列表页URL列表
        """
        pass
    
    @abstractmethod
    def parse_list_page(self, html: str, url: str) -> List[str]:
        """
        解析列表页，获取文章URL列表
        
        Args:
            html: 列表页HTML内容
            url: 列表页URL
            
        Returns:
            List[str]: 文章URL列表
        """
        pass
    
    @abstractmethod
    def parse_detail_page(self, html: str, url: str) -> Dict[str, Any]:
        """
        解析详情页，获取文章内容
        
        Args:
            html: 详情页HTML内容
            url: 详情页URL
            
        Returns:
            Dict[str, Any]: 文章内容字典
        """
        pass
    
    def get_start_date(self, days: int) -> datetime:
        """
        获取爬取起始日期
        
        Args:
            days: 爬取最近几天的新闻
            
        Returns:
            datetime: 起始日期
        """
        return datetime.now() - timedelta(days=days)
    
    def is_url_in_date_range(self, url: str, start_date: datetime) -> bool:
        """
        判断URL是否在日期范围内
        
        Args:
            url: 文章URL
            start_date: 起始日期
            
        Returns:
            bool: 是否在日期范围内
        """
        # 默认实现总是返回True，子类可以根据URL规则重写此方法
        return True
    
    def get_category_url(self, category: Optional[str] = None) -> str:
        """
        获取分类URL
        
        Args:
            category: 新闻分类
            
        Returns:
            str: 分类URL
        """
        if category and self.categories and category in self.categories:
            return self.categories[category]
        elif self.categories:
            # 返回默认分类
            return next(iter(self.categories.values()))
        else:
            # 没有分类，返回空
            return ""
    
    def clean_url(self, url: str, base_url: str) -> str:
        """
        清理URL，确保是完整的绝对URL
        
        Args:
            url: 原始URL
            base_url: 基础URL
            
        Returns:
            str: 清理后的URL
        """
        from urllib.parse import urljoin
        return urljoin(base_url, url)
    
    def clean_text(self, text: str) -> str:
        """
        清理文本，去除多余空白字符
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        # 去除空白字符
        text = text.strip()
        
        # 将连续空白字符替换为单个空格
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text 