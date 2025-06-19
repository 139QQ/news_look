# 财经新闻爬虫系统 - 架构重构

## 系统架构概述

该项目是一个统一的财经新闻爬虫系统，采用模块化设计和策略模式，支持同步和异步爬取模式，可以灵活配置和扩展不同的新闻源。

## 核心组件

### 1. 爬虫基类 (BaseCrawler)

位置：`app/crawlers/core/base_crawler.py`

功能：
- 提供统一的爬虫接口，支持同步和异步爬取模式
- 实现通用的爬取流程，包括列表页和详情页处理
- 管理HTTP客户端、数据处理器和爬取策略
- 提供统计信息收集

### 2. HTTP客户端 (BaseHttpClient)

位置：`app/crawlers/core/http_client.py`

功能：
- 抽象基类定义统一接口
- 同步实现 (SyncHttpClient)：基于requests库
- 异步实现 (AsyncHttpClient)：基于aiohttp库
- 支持代理、重试、超时等配置
- 提供请求统计信息

### 3. 数据处理器 (DataProcessor)

位置：`app/crawlers/core/data_processor.py`

功能：
- 负责文章数据处理和存储
- 支持单条和批量数据保存
- 使用SQLite数据库存储爬取结果
- 提供数据统计信息

### 4. 爬虫策略基类 (BaseCrawlerStrategy)

位置：`app/crawlers/strategies/base_strategy.py`

功能：
- 定义网站爬取的策略接口
- 解析列表页和详情页的方法
- URL生成和处理

### 5. 声明式爬虫策略 (DeclarativeCrawlerStrategy)

位置：`app/crawlers/core/declarative_crawler.py`

功能：
- 通过配置文件定义爬虫行为，无需编写代码
- 支持配置化的选择器和模式匹配
- 可灵活扩展不同的新闻源

### 6. 爬虫工厂 (CrawlerFactory)

位置：`app/crawlers/factory.py`

功能：
- 负责创建和管理爬虫实例
- 加载和缓存爬虫配置
- 提供批量创建爬虫的方法
- 支持注册新的爬虫源

## 配置管理

系统支持JSON和YAML格式的配置文件，存放在`configs/crawlers/`目录下，每个新闻源对应一个配置文件。

配置文件示例：`configs/crawlers/新浪财经.yaml`

## 测试组件

1. 新爬虫架构测试：`test_new_crawler.py`
2. 声明式爬虫测试：`test_declarative_crawler.py`

## 后续开发计划

1. 完善错误处理和日志记录
2. 增强声明式爬虫的灵活性
3. 添加更多新闻源的支持
4. 实现爬虫调度和监控
5. 增加数据分析和处理功能 

# app/config/crawlers/eastmoney.yaml
name: 东方财富
source: 东方财富
base_url: https://www.eastmoney.com
category_urls:
  财经: 
    - https://finance.eastmoney.com/
  股票: 
    - https://stock.eastmoney.com/
  基金: 
    - https://fund.eastmoney.com/
  债券: 
    - https://bond.eastmoney.com/
selectors:
  list_page:
    news_links: "a.news_title"
    next_page: "a.page_next"
  detail_page:
    title: "h1.news_title"
    publish_time: "div.time"
    author: "div.author"
    content: "div.content"
    category: "div.bread_crumb"
headers:
  Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
  Accept-Language: "zh-CN,zh;q=0.9,en;q=0.8"
crawl_interval: 30  # 分钟
max_retry: 3 

# app/utils/config_loader.py
import os
import yaml
from typing import Dict, Any

class CrawlerConfigLoader:
    """爬虫配置加载器"""
    
    def __init__(self, config_dir=None):
        if config_dir is None:
            # 默认配置目录
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_dir = os.path.join(root_dir, 'config', 'crawlers')
        else:
            self.config_dir = config_dir
        
        # 确保目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 配置缓存
        self.configs = {}
    
    def load_config(self, crawler_name: str) -> Dict[str, Any]:
        """加载指定爬虫的配置"""
        if crawler_name in self.configs:
            return self.configs[crawler_name]
        
        config_file = os.path.join(self.config_dir, f"{crawler_name}.yaml")
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"爬虫配置文件不存在: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 缓存配置
        self.configs[crawler_name] = config
        return config
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有爬虫的配置"""
        configs = {}
        for file in os.listdir(self.config_dir):
            if file.endswith('.yaml'):
                crawler_name = file[:-5]  # 移除.yaml后缀
                configs[crawler_name] = self.load_config(crawler_name)
        return configs 

# app/crawlers/parsers/base_parser.py
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from app.utils.text_cleaner import clean_html, decode_html_entities

class BaseParser:
    """解析器基类"""
    
    def __init__(self, config):
        """
        初始化解析器
        
        Args:
            config: 爬虫配置字典
        """
        self.config = config
        self.selectors = config.get('selectors', {})
    
    def parse_list_page(self, html: str) -> List[str]:
        """
        解析列表页，提取新闻链接
        
        Args:
            html: HTML内容
            
        Returns:
            list: 新闻链接列表
        """
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        news_links = []
        
        # 从配置中获取选择器
        selector = self.selectors.get('list_page', {}).get('news_links')
        if not selector:
            return []
        
        # 提取链接
        for link in soup.select(selector):
            url = link.get('href')
            if url and self.is_valid_news_url(url):
                # 处理相对URL
                if not url.startswith(('http://', 'https://')):
                    base_url = self.config.get('base_url', '')
                    url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"
                news_links.append(url)
        
        return news_links
    
    def parse_detail_page(self, html: str, url: str = "") -> Dict[str, Any]:
        """
        解析详情页，提取新闻内容
        
        Args:
            html: HTML内容
            url: 新闻URL
            
        Returns:
            dict: 新闻数据
        """
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取信息
        title = self.extract_title(soup)
        publish_time = self.extract_pub_time(soup)
        content = self.extract_content(soup)
        category = self.extract_category(soup)
        author = self.extract_author(soup)
        
        # 返回结果
        return {
            'title': title,
            'publish_time': publish_time,
            'content': content,
            'category': category,
            'author': author,
            'url': url,
            'source': self.config.get('source', '未知来源'),
            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def is_valid_news_url(self, url: str) -> bool:
        """验证URL是否为有效的新闻URL"""
        # 默认实现
        return bool(url and '.html' in url)
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """提取新闻标题"""
        selector = self.selectors.get('detail_page', {}).get('title')
        if selector:
            elem = soup.select_one(selector)
            if elem:
                return decode_html_entities(elem.get_text().strip())
        return "未知标题"
    
    def extract_pub_time(self, soup: BeautifulSoup) -> str:
        """提取发布时间"""
        selector = self.selectors.get('detail_page', {}).get('publish_time')
        if selector:
            elem = soup.select_one(selector)
            if elem:
                time_text = elem.get_text().strip()
                # 尝试多种时间格式
                patterns = [
                    r'(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2})',
                    r'(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{1,2})',
                    r'(\d{4}年\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{1,2})'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, time_text)
                    if match:
                        return match.group(1)
        
        # 默认返回当前时间
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def extract_content(self, soup: BeautifulSoup) -> str:
        """提取新闻正文"""
        selector = self.selectors.get('detail_page', {}).get('content')
        if selector:
            elem = soup.select_one(selector)
            if elem:
                # 清理HTML
                return clean_html(str(elem))
        return ""
    
    def extract_category(self, soup: BeautifulSoup) -> str:
        """提取新闻类别"""
        selector = self.selectors.get('detail_page', {}).get('category')
        if selector:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text().strip()
                # 提取类别关键词
                categories = ['财经', '股票', '基金', '债券', '期货', '外汇']
                for cat in categories:
                    if cat in text:
                        return cat
        return "未分类"
    
    def extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """提取作者"""
        selector = self.selectors.get('detail_page', {}).get('author')
        if selector:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text().strip()
        return None 

# app/crawlers/eastmoney.py
# 更新文件，合并来自 eastmoney_simple.py 的功能

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 东方财富网爬虫
使用requests库直接爬取，无需浏览器
合并了简化版和完整版功能
"""

import os
import re
import sys
import time
import random
import logging
import hashlib
import requests
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from app.crawlers.base import BaseCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords
from app.db.sqlite_manager import SQLiteManager

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('东方财富')

class EastMoneyCrawler(BaseCrawler):
    """东方财富网爬虫，用于爬取东方财富网的财经新闻"""
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化东方财富网爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
            **kwargs: 其他参数
        """
        self.source = "东方财富"
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, use_source_db=use_source_db, **kwargs)
        
        self.status = 'idle'
        self.last_run = None
        self.next_run = None
        self.error_count = 0
        self.success_count = 0
        
        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 合并原版和简化版的分类URL映射
        self.category_urls = {
            '财经': [
                "https://finance.eastmoney.com/", 
                "https://finance.eastmoney.com/a/cjdd.html"
            ],
            '股票': [
                "https://stock.eastmoney.com/", 
                "https://stock.eastmoney.com/a/cgspl.html"
            ],
            '基金': [
                "https://fund.eastmoney.com/", 
                "https://fund.eastmoney.com/news/cjjj.html"
            ],
            '债券': [
                "https://bond.eastmoney.com/", 
                "https://bond.eastmoney.com/news/czqzx.html"
            ],
        }
        
        # 初始化数据列表
        self.news_data = []
        
        # 随机User-Agent
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        ]
        
        # 如果提供了db_manager并且不是SQLiteManager类型，创建SQLiteManager
        if self.db_manager and not isinstance(self.db_manager, SQLiteManager):
            if hasattr(self.db_manager, 'db_path'):
                self.sqlite_manager = SQLiteManager(self.db_manager.db_path)
            else:
                # 使用传入的db_path或默认路径
                self.sqlite_manager = SQLiteManager(self.db_path or self.db_path)
        elif not self.db_manager:
            # 如果没有提供db_manager，创建SQLiteManager
            self.sqlite_manager = SQLiteManager(self.db_path or self.db_path)
        else:
            # 否则使用提供的db_manager
            self.sqlite_manager = self.db_manager
        
        logger.info(f"东方财富网爬虫初始化完成，数据库路径: {self.db_path}")

    # 其余方法保持不变... 

def _init_crawlers(self):
    """初始化所有爬虫实例"""
    try:
        # 初始化各个爬虫，若指定了数据库目录则传入
        self.eastmoney_crawler = EastMoneyCrawler(
            use_proxy=self.settings.get('USE_PROXY', False),
            use_source_db=True
        )
        self._set_db_path(self.eastmoney_crawler, "东方财富")
        
        self.sina_crawler = SinaCrawler(
            use_proxy=self.settings.get('USE_PROXY', False),
            use_source_db=True
        )
        self._set_db_path(self.sina_crawler, "新浪财经")
        
        self.netease_crawler = NeteaseCrawler(
            use_proxy=self.settings.get('USE_PROXY', False),
            use_source_db=True
        )
        self._set_db_path(self.netease_crawler, "网易财经")
        
        self.ifeng_crawler = IfengCrawler(
            use_proxy=self.settings.get('USE_PROXY', False),
            use_source_db=True
        )
        self._set_db_path(self.ifeng_crawler, "凤凰财经")
        
        # 确保每个爬虫的source属性正确设置
        self._verify_sources()
        
        # 打印初始化信息
        logger.info("爬虫管理器初始化完成，可用爬虫:")
        logger.info(f"- 东方财富 (EastmoneyCrawler): {self.eastmoney_crawler.db_path}")
        logger.info(f"- 新浪财经 (SinaCrawler): {self.sina_crawler.db_path}")
        logger.info(f"- 网易财经 (NeteaseCrawler): {self.netease_crawler.db_path}")
        logger.info(f"- 凤凰财经 (IfengCrawler): {self.ifeng_crawler.db_path}")
        
    except Exception as e:
        logger.error(f"初始化爬虫失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise 

def _verify_sources(self):
    """验证所有爬虫的source属性是否正确设置，并统一来源名称格式"""
    crawlers = {
        'eastmoney_crawler': ('东方财富', self.eastmoney_crawler),
        'sina_crawler': ('新浪财经', self.sina_crawler),
        'netease_crawler': ('网易财经', self.netease_crawler),
        'ifeng_crawler': ('凤凰财经', self.ifeng_crawler)
    }
    
    # 其余代码保持不变 