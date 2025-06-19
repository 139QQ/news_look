#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫基类
"""

import os
import time
import random
import requests
from datetime import datetime, timedelta
import sqlite3
import json
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import re
import hashlib
from typing import List, Dict, Optional, Tuple, Any, Union
import uuid
from PIL import Image
from io import BytesIO

from backend.app.utils.logger import get_logger, get_crawler_logger
from backend.app.utils.sentiment_analyzer import SentimentAnalyzer
from backend.app.utils.database import DatabaseManager
from backend.app.config import get_settings
from backend.app.utils.text_cleaner import TextCleaner, format_for_display, clean_html, extract_keywords
from backend.app.db.SQLiteManager import SQLiteManager

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('base')

class BaseCrawler:
    """爬虫基类，提供所有爬虫共用的基础功能"""
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, source=None, **kwargs):
        """
        初始化爬虫基类
        
        Args:
            db_manager: 数据库管理器对象，如果提供则优先使用
            db_path: 数据库路径，如果为None则根据 use_source_db 决定
            use_proxy: 是否使用代理
            use_source_db: 是否将数据保存到来源专用数据库 (位于 data/db/sources/)
            source: 爬虫来源名称 (应由子类在调用super前设置或在此处传递)
            **kwargs: 其他参数
        """
        # 设置来源
        self.source = source or getattr(self, 'source', self.__class__.__name__.lower().replace("crawler", ""))
        
        # 初始化日志记录器 (self.logger)
        # 使用 get_crawler_logger 获取针对此爬虫实例的 logger
        # 子类可以通过 super().__init__(source="...") 传递 source，或者直接在子类中定义 self.source
        self.logger = get_crawler_logger(self.source if self.source != "未知来源" else self.__class__.__name__)
        
        if self.source == "未知来源":
            self.logger.warning(f"{self.__class__.__name__} 未明确设置 source 属性，将使用类名作为日志source。")
        
        # 初始化基本属性
        self.news_data: List[Dict[str, Any]] = []  # 存储爬取的新闻数据
        self.use_proxy: bool = use_proxy
        self.proxies: Optional[Dict[str, str]] = None
        
        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 初始化情感分析器
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # 从配置中获取设置
        self.settings = get_settings()
        
        # 爬虫统计信息
        self.stats = {
            'total_articles': 0,
            'successful_crawls': 0,
            'failed_crawls': 0,
            'last_crawl_time': None,
            'last_crawl_articles': 0,
            'created_at': datetime.now().isoformat(),
        }
        
        # 初始化Selenium相关属性
        self.use_selenium = False
        self.driver = None
        
        # 尝试使用fake_useragent生成随机User-Agent
        try:
            self.ua = UserAgent()
        except (ValueError, ConnectionError, FileNotFoundError) as e:
            logging.warning("初始化UserAgent失败: %s，将使用预定义的User-Agent列表", str(e))
            self.ua = None
        
        # 初始化数据库管理器 (self.db_manager)
        if db_manager:
            self.db_manager = db_manager
            # 尝试获取 db_path 从提供的 manager (可能没有)
            self.db_path = getattr(db_manager, 'db_path', None)
            if not self.db_path:
                 self.logger.warning("提供的 db_manager 没有 db_path 属性，db_path 将为 None")
        else:
            # 确定主数据库路径或源数据库路径的 *基础目录*
            # SQLiteManager 会在其内部处理 sources 子目录
            if db_path:
                # 如果明确提供了 db_path，使用它作为基础路径
                base_db_dir = os.path.dirname(db_path)
                main_db_filename = os.path.basename(db_path)
                # 如果文件名不是 finance_news.db，记录一个潜在的非标准用法
                if main_db_filename != 'finance_news.db':
                    self.logger.info(f"使用明确指定的数据库路径: {db_path}")
                effective_db_path = db_path # 用于SQLiteManager初始化的路径
            else:
                # 没有提供 db_path，使用默认结构 data/db/
                base_db_dir = os.path.abspath(os.path.join('data', 'db'))
                main_db_filename = 'finance_news.db'
                effective_db_path = os.path.join(base_db_dir, main_db_filename)
                self.logger.info(f"未指定db_path, 使用默认主数据库路径: {effective_db_path}")
            
            # 确保基础数据库目录存在 (e.g., data/db/)
            # SQLiteManager 内部会创建 sources 和 backups 子目录
            if base_db_dir and not os.path.exists(base_db_dir):
                os.makedirs(base_db_dir)
                self.logger.info(f"创建基础数据库目录: {base_db_dir}")
            
            # 设置 self.db_path 为主/聚合数据库的路径
            self.db_path = effective_db_path 
            
            # 创建 SQLiteManager 实例，传入主/聚合数据库的路径
            # SQLiteManager 的 __init__ 会创建 sources 和 backups 子目录
            try:
                self.db_manager = SQLiteManager(self.db_path)
            except Exception as e_mgr:
                self.logger.error(f"创建 SQLiteManager 失败: {e_mgr}")
                self.db_manager = None # 确保设置为 None

        # Log final db_manager status
        if self.db_manager:
             self.logger.info(f"爬虫 {self.source} 初始化完成，db_manager 指向: {getattr(self.db_manager, 'db_path', '未知路径')}")
        else:
             self.logger.error(f"爬虫 {self.source} 初始化完成，但 db_manager 初始化失败!")
        
        self.logger.info(f"初始化爬虫: {self.source}, 数据库路径: {self.db_path}")
    
    def __del__(self):
        """析构函数，关闭Selenium驱动"""
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                self.logger.debug("Selenium驱动已关闭")
        except Exception as e:
            self.logger.error("关闭资源时出错: %s", str(e))
    
    def crawl(self, days=1):
        """
        爬取新闻的主方法，子类需要实现此方法
        
        Args:
            days: 爬取最近几天的新闻
        
        Returns:
            list: 爬取的新闻列表
        """
        raise NotImplementedError("子类必须实现crawl方法")
    
    def fetch_page(self, url, params=None, headers=None, max_retries=None, timeout=None):
        """
        获取页面内容
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            
        Returns:
            Response对象
        """
        if max_retries is None:
            max_retries = 3
        
        if timeout is None:
            timeout = 30
        
        # 随机休眠，避免频繁请求
        self.random_sleep()
        
        # 设置代理
        proxies = self.proxies if self.use_proxy else None
        
        # 设置请求头
        if headers is None:
            headers = {}
        
        # 添加随机User-Agent
        user_agent = self.get_random_user_agent()
        headers.setdefault('User-Agent', user_agent)
        
        # 添加随机Referer
        referer = self.get_random_referer(url)
        headers.setdefault('Referer', referer)
        
        # 添加其他常见请求头
        headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9')
        headers.setdefault('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8')
        headers.setdefault('Accept-Encoding', 'gzip, deflate, br')
        headers.setdefault('Connection', 'keep-alive')
        headers.setdefault('Upgrade-Insecure-Requests', '1')
        headers.setdefault('Cache-Control', 'max-age=0')
        
        # 添加更多现代浏览器的请求头
        headers.setdefault('sec-ch-ua', '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"')
        headers.setdefault('sec-ch-ua-mobile', '?0')
        headers.setdefault('sec-ch-ua-platform', '"Windows"')
        headers.setdefault('Sec-Fetch-Dest', 'document')
        headers.setdefault('Sec-Fetch-Mode', 'navigate')
        headers.setdefault('Sec-Fetch-Site', 'none')
        headers.setdefault('Sec-Fetch-User', '?1')
        
        # 添加随机Cookie
        cookies = self.get_random_cookies()
        
        # 重试机制
        for attempt in range(max_retries):
            try:
                # 每次重试使用不同的User-Agent和Referer
                if attempt > 0:
                    headers['User-Agent'] = self.get_random_user_agent()
                    headers['Referer'] = self.get_random_referer(url)
                    # 指数退避策略
                    backoff_time = 2 ** attempt + random.uniform(0, 1)
                    self.logger.info("第 %d/%d 次重试，等待 %.2f 秒", attempt+1, max_retries, backoff_time)
                    time.sleep(backoff_time)
                
                # 发送请求
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    proxies=proxies,
                    cookies=cookies,
                    timeout=timeout
                )
                
                # 检查响应状态码
                if response.status_code == 200:
                    # 检查响应内容长度
                    if len(response.text) < 500:
                        self.logger.warning("响应内容过短，可能被反爬: %s, 长度: %d", url, len(response.text))
                    
                    # 检查是否包含反爬关键词
                    anti_crawl_keywords = [
                        "访问频率过高", "访问过于频繁", "请求频率超过限制", "请输入验证码", "人机验证",
                        "访问受限", "禁止访问", "拒绝访问", "访问被拒绝", "IP被封",
                        "blocked", "forbidden", "denied", "captcha", "verify",
                        "too many requests", "rate limit exceeded", "请稍后再试"
                    ]
                    
                    for keyword in anti_crawl_keywords:
                        if keyword in response.text:
                            self.logger.warning("检测到反爬虫措施: %s", url)
                            break
                    else:
                        # 未检测到反爬关键词，返回响应
                        return response
                
                # 处理特定的HTTP错误
                if response.status_code == 403:
                    self.logger.warning("访问被禁止 (403): %s", url)
                elif response.status_code == 404:
                    self.logger.warning("页面不存在 (404): %s", url)
                    return None  # 对于404错误，直接返回None，不再重试
                elif response.status_code == 429:
                    self.logger.warning("请求过多 (429): %s", url)
                elif response.status_code >= 500:
                    self.logger.warning("服务器错误 (%d): %s", response.status_code, url)
                else:
                    self.logger.warning("HTTP错误 (%d): %s", response.status_code, url)
                
            except requests.exceptions.Timeout:
                self.logger.warning("请求超时: %s", url)
            except requests.exceptions.ConnectionError:
                self.logger.warning("连接错误: %s", url)
            except requests.exceptions.RequestException as e:
                self.logger.warning("请求异常: %s, 错误: %s", url, str(e))
            except (ValueError, TypeError, AttributeError) as e:
                self.logger.warning("未知错误: %s, 错误: %s", url, str(e))
        
        # 所有重试都失败
        self.logger.error("获取页面失败，已重试 %d 次: %s", max_retries, url)
        return None
    
    def fetch_page_with_requests(self, url, retry=3, timeout=10):
        """
        使用requests获取页面内容
        
        Args:
            url: 页面URL
            retry: 重试次数
            timeout: 超时时间
        
        Returns:
            str: 页面内容
        """
        # 如果启用代理，则获取代理
        if self.use_proxy and not self.proxies:
            self.proxies = self.get_proxy()  # 现在 get_proxy 总是返回字典，即使是空的
        
        # 尝试获取页面内容
        for i in range(retry):
            try:
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    proxies=self.proxies, 
                    timeout=timeout
                )
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type and 'application/json' not in content_type:
                    self.logger.warning("非HTML或JSON内容: %s, URL: %s", content_type, url)
                    return None
                
                # 检查内容长度
                if len(response.text) < 100:
                    self.logger.warning("页面内容过短，可能被反爬: %s", url)
                    return None
                
                return response.text
            except requests.exceptions.RequestException as e:
                self.logger.warning("获取页面失败: %s, 错误: %s, 重试: %d/%d", url, str(e), i+1, retry)
                
                # 如果使用代理且失败，则更换代理
                if self.use_proxy:
                    self.proxies = self.get_proxy()  # 现在 get_proxy 总是返回字典，即使是空的
                
                # 随机休眠，避免被反爬
                time.sleep(random.uniform(1, 3))
        
        self.logger.error("获取页面失败，已达到最大重试次数: %s", url)
        return None
    
    def fetch_page_with_selenium(self, url, retry=3, timeout=10):
        """
        使用Selenium获取页面内容
        
        Args:
            url: 页面URL
            retry: 重试次数
            timeout: 超时时间
        
        Returns:
            str: 页面内容
        """
        # 如果驱动未初始化，则初始化驱动
        if not self.driver:
            self.init_selenium_driver()
        
        # 尝试获取页面内容
        for i in range(retry):
            try:
                self.driver.get(url)
                
                # 等待页面加载完成
                time.sleep(random.uniform(2, 5))
                
                # 获取页面内容
                html = self.driver.page_source
                
                # 检查内容长度
                if len(html) < 100:
                    self.logger.warning("页面内容过短，可能被反爬: %s", url)
                    return None
                
                return html
            except Exception as e:
                self.logger.warning("使用Selenium获取页面失败: %s, 错误: %s, 重试: %d/%d", url, str(e), i+1, retry)
                
                # 随机休眠，避免被反爬
                time.sleep(random.uniform(1, 3))
        
        self.logger.error("使用Selenium获取页面失败，已达到最大重试次数: %s", url)
        return None
    
    def init_selenium_driver(self):
        """初始化Selenium驱动"""
        try:
            # 设置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            # 如果使用代理，则设置代理
            if self.use_proxy and self.proxies:
                # Assuming self.proxies is like {'http': 'http://proxy', 'https': 'http://proxy'}
                # Selenium typically takes a single proxy string for all protocols or specific ones.
                # This part might need adjustment based on actual proxy format if used.
                http_proxy = self.proxies.get('http') or self.proxies.get('https')
                if http_proxy:
                    chrome_options.add_argument(f'--proxy-server={http_proxy}')
            
            # 初始化驱动
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(60)  # 设置页面加载超时
            
            self.logger.info("Selenium WebDriver 初始化成功。")
        except Exception as e:
            self.logger.error(f"初始化 Selenium WebDriver 失败: {e}")
            self.driver = None
            self.use_selenium = False # Disable selenium if it fails to init
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        获取代理
        
        Returns:
            Optional[Dict[str, str]]: 代理配置字典 (e.g., {'http': '...', 'https': '...'}), 
                                     或 {} (如果未实现或无可用代理).
        """
        # 这里可以实现获取代理的逻辑，例如从代理池获取
        # 简单起见，这里返回一个空字典，子类可以重写此方法实现真正的代理逻辑
        self.logger.info("get_proxy called, but no proxy fetching logic implemented yet.")
        return {} # 返回空字典而不是 None
    
    def random_sleep(self, min_seconds=None, max_seconds=None):
        """
        随机休眠，避免被反爬
        
        Args:
            min_seconds: 最小休眠时间
            max_seconds: 最大休眠时间
        """
        if min_seconds is None:
            min_seconds = max(1, 5 * 0.8)
        if max_seconds is None:
            max_seconds = max(3, 5 * 1.2)
        
        sleep_time = random.uniform(min_seconds, max_seconds)
        
        if self.settings.DEBUG_MODE:
            self.logger.debug(f"随机休眠: {sleep_time:.2f} 秒 (范围: {min_seconds}-{max_seconds}s)")
        time.sleep(sleep_time)
    
    def save_news(self, news_data):
        """
        保存新闻数据。
        主要职责是调用 self.save_news_to_db 进行实际的数据库保存。
        如果直接调用此方法，它会确保通过 save_news_to_db 保存。
        
        Args:
            news_data: 新闻数据字典
            
        Returns:
            bool: 是否成功保存 (委托给 save_news_to_db)
        """
        self.logger.debug(f"[BaseCrawler.save_news] 接收到新闻: {news_data.get('title', 'N/A')}, 将通过 save_news_to_db 处理")
        return self.save_news_to_db(news_data)

    def _preprocess_news_data(self, news_data):
        """
        初步预处理新闻数据 (主要设置爬虫source和基础时间戳)
        更全面的预处理（ID生成、完整默认值、类型转换）由SQLiteManager负责。
        
        Args:
            news_data: 原始新闻数据
            
        Returns:
            dict: 处理后的新闻数据
        """
        # 创建副本以避免修改原始数据
        processed = news_data.copy()
        
        # 1. 添加/确保来源 (source)
        # 子类应该在初始化时设置 self.source
        if not hasattr(self, 'source') or not self.source:
            self.logger.warning(f"[BaseCrawler._preprocess] 爬虫实例 {self.__class__.__name__} 未正确设置 source 属性。将尝试从数据中获取或设为'未知来源'")
            processed['source'] = news_data.get('source', '未知来源')
        else:
            processed['source'] = self.source
        
        # 2. 确保基础时间字段存在，如果完全没有则设置当前时间
        # SQLiteManager会进行更细致的检查和默认值设置
        if 'pub_time' not in processed or not processed['pub_time']:
            processed['pub_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.logger.debug(f"[BaseCrawler._preprocess] 新闻 {processed.get('title', 'N/A')} 缺少pub_time, 暂时设置为当前时间.")
            
        if 'crawl_time' not in processed or not processed['crawl_time']:
            processed['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 其他特定于爬虫基类的早期处理可在此添加
        # 例如：通用的HTML标签清理、特殊字符替换等，如果这些不适合在SQLiteManager中做

        self.logger.debug(f"[BaseCrawler._preprocess] 初步预处理完成 for: {processed.get('title', 'N/A')}, Source: {processed.get('source')}")
        return processed

    def get_news_count(self):
        """获取已爬取的新闻数量"""
        if self.db_manager:
            try:
                cursor = self.db_manager.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM news")
                return cursor.fetchone()[0]
            except Exception as e:
                self.logger.error(f"获取新闻数量失败: {str(e)}")
        return len(self.news_data)
    
    def get_news_by_category(self, category):
        """获取指定分类的新闻"""
        if self.db_manager:
            try:
                cursor = self.db_manager.conn.cursor()
                cursor.execute(
                    "SELECT * FROM news WHERE category = ? ORDER BY pub_time DESC", 
                    (category,)
                )
                return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                self.logger.error(f"获取分类新闻失败: {category}, 错误: {str(e)}")
        
        # 如果数据库不可用，从内存中过滤
        return [news for news in self.news_data if news.get('category') == category]
    
    def get_news_by_date_range(self, start_date, end_date):
        """获取指定日期范围的新闻"""
        try:
            rows = self.db_manager.execute(
                "SELECT * FROM news WHERE pub_time BETWEEN ? AND ? ORDER BY pub_time DESC",
                (start_date, end_date)
            )
            return [dict(zip(['id', 'title', 'content', 'url', 'source', 'category', 'pub_time', 'crawl_time', 'keywords'], row)) 
                    for row in rows]
        except Exception as e:
            self.logger.error("获取日期范围新闻失败: %s - %s, 错误: %s", start_date, end_date, str(e))
            return []
    
    def search_news(self, keyword):
        """搜索新闻"""
        try:
            rows = self.db_manager.execute(
                "SELECT * FROM news WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ? ORDER BY pub_time DESC",
                (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
            )
            return [dict(zip(['id', 'title', 'content', 'url', 'source', 'category', 'pub_time', 'crawl_time', 'keywords'], row)) 
                    for row in rows]
        except Exception as e:
            self.logger.error("搜索新闻失败: %s, 错误: %s", keyword, str(e))
            return []
    
    def get_random_user_agent(self):
        """获取随机User-Agent"""
        if self.ua:
            try:
                return self.ua.random
            except Exception as e:
                logging.warning("获取随机User-Agent失败: %s，将使用预定义的User-Agent", str(e))
        
        # 预定义的User-Agent列表
        user_agents = [
            # Chrome
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
            
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
            
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 Edg/92.0.902.73",
            
            # Mobile
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Mobile Safari/537.36"
        ]
        
        return random.choice(user_agents)
    
    def get_random_referer(self, url=None):
        """获取随机Referer"""
        referers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.baidu.com/",
            "https://www.sogou.com/",
            "https://www.so.com/",
            "https://www.yahoo.com/",
            "https://www.eastmoney.com/",
            "https://finance.sina.com.cn/",
            "https://finance.qq.com/",
            "https://www.jrj.com.cn/",
            "https://www.cnstock.com/",
            "https://www.10jqka.com.cn/"
        ]
        
        # 如果提供了URL，有50%的概率使用该URL的域名作为Referer
        if url and random.random() < 0.5:
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
                referers.append(base_url)
            except Exception:
                pass
        
        return random.choice(referers)
    
    def get_random_cookies(self):
        """生成随机Cookies"""
        # 生成随机的Cookie值
        cookie_values = {
            "visited": "1",
            "lastVisit": str(int(time.time())),
            "resolution": f"{random.choice([1366, 1440, 1536, 1920, 2560])}x{random.choice([768, 900, 1080, 1440])}",
            "sessionid": ''.join(random.choices('0123456789abcdef', k=32)),
            "uuid": ''.join(random.choices('0123456789abcdef', k=32)),
            "locale": random.choice(["zh-CN", "en-US", "zh-TW", "ja-JP"]),
            "timezone": random.choice(["Asia/Shanghai", "Asia/Hong_Kong", "Asia/Tokyo", "America/New_York"]),
        }
        
        return cookie_values

    def _get_db_path(self, source=None):
        """获取数据库路径"""
        if source is None:
            source = self.source or "news"
            
        # 将来源转换为文件名安全的字符串
        db_name = re.sub(r'[^\w]', '_', source.lower())
        
        # 确保DB_DIR存在
        db_dir = self.settings.get('DB_DIR', 'data/db')
        os.makedirs(db_dir, exist_ok=True)
        
        # 使用固定名称的数据库，每个来源一个数据库
        db_path = os.path.join(db_dir, f"{db_name}.db")
        self.logger.info("数据库路径: %s", db_path)
        
        return db_path

    def _process_news_detail(self, news_detail: dict) -> dict:
        """处理新闻详情，清理和规范数据"""
        # 已有的代码保持不变
        # ...

        # 如果是凤凰财经的内容，过滤浏览器提示
        if news_detail.get('source') == '凤凰财经' and news_detail.get('content'):
            # 去除浏览器升级提示
            browser_tip_pattern = r'亲爱的凤凰网用户[\s\S]*?浏览器.*?下载'
            news_detail['content'] = re.sub(browser_tip_pattern, '', news_detail['content'])
        
        # 清理新闻正文内容
        if news_detail.get('content'):
            # 格式化内容
            news_detail['content'] = format_for_display(news_detail['content'])
        
        # 关键词处理
        if 'keywords' not in news_detail or not news_detail['keywords']:
            # 尝试从标题和摘要中提取关键词
            keywords = []
            title = news_detail.get('title', '')
            summary = news_detail.get('summary', '')
            content_sample = news_detail.get('content', '')[:500] if news_detail.get('content') else ''
            
            # 组合文本进行关键词提取
            combined_text = f"{title} {summary} {content_sample}"
            try:
                # 使用TextCleaner提取关键词
                keywords = TextCleaner.extract_keywords(combined_text, top_k=5)
                if keywords:
                    news_detail['keywords'] = ','.join(keywords)
            except Exception as e:
                self.logger.error("提取关键词失败: %s", str(e))
        
        # 确保关键词是字符串格式
        if isinstance(news_detail.get('keywords'), list):
            news_detail['keywords'] = ','.join(news_detail['keywords'])
        
        # 确保所有字段都有值
        # ... 其余处理保持不变

        return news_detail
        
    def _extract_images(self, soup, news_id):
        """提取并处理新闻中的图片"""
        images = []
        
        # 确保soup是BeautifulSoup对象
        if isinstance(soup, str):
            try:
                soup = BeautifulSoup(soup, 'html.parser')
            except Exception as e:
                self.logger.error("解析HTML失败: %s", str(e))
                return images
        
        # 查找所有图片标签
        img_tags = soup.select('img')
        self.logger.info("找到 %d 个图片标签", len(img_tags))
        
        for img in img_tags:
            img_url = img.get('src', '')
            
            # 检查图片URL
            if not img_url:
                continue
            
            # 处理相对路径
            if not img_url.startswith(('http://', 'https://')):
                self.logger.debug("跳过相对路径图片: %s", img_url)
                continue
            
            # 过滤小图标和广告图片
            skip_patterns = ['logo', 'icon', 'avatar', 'ad', 'banner', '.gif', '.svg']
            if any(pattern in img_url.lower() for pattern in skip_patterns):
                self.logger.debug("跳过小图标或广告图片: %s", img_url)
                continue
            
            # 提取alt文本，改进图片描述
            alt_text = img.get('alt', '').strip()
            if not alt_text:
                # 尝试从图片周围的文本中提取描述
                parent = img.parent
                if parent:
                    alt_text = parent.get_text().strip()[:50]
            
            # 记录图片信息
            image_info = {
                'url': img_url,
                'alt': alt_text or '新闻图片',
                'original_url': img_url
            }
            
            # 本地保存图片（如果配置了SAVE_IMAGES）
            if self.settings.get('SAVE_IMAGES', False):
                try:
                    local_path = self._save_image(img_url, news_id)
                    if local_path:
                        # 更新图片元数据
                        local_url = f'/images/{news_id}/{os.path.basename(local_path)}'
                        image_info['local_url'] = local_url
                        
                        # 更新图片标签
                        img['src'] = local_url
                        img['data-original-src'] = img_url  # 保存原始URL
                        img['loading'] = 'lazy'
                        
                        # 添加类
                        img_classes = img.get('class', [])
                        if isinstance(img_classes, str):
                            img_classes = [img_classes]
                        if 'img-fluid' not in img_classes:
                            img_classes.append('img-fluid')
                        if 'rounded' not in img_classes:
                            img_classes.append('rounded')
                        img['class'] = ' '.join(img_classes)
                except (requests.RequestException, IOError, Image.UnidentifiedImageError) as e:
                    self.logger.error("保存图片失败: %s, 错误: %s", img_url, str(e))
            
            images.append(image_info)
        
        return images

    def _save_image(self, img_url, news_id):
        """保存图片到本地"""
        try:
            # 从配置中获取图片保存目录
            image_dir = self.settings.get('IMAGE_DIR')
            if not image_dir:
                self.logger.warning("未配置图片保存目录，跳过保存")
                return None
                
            # 创建新闻专属的图片目录
            news_image_dir = os.path.join(image_dir, str(news_id))
            os.makedirs(news_image_dir, exist_ok=True)
            
            # 获取图片文件名
            img_filename = os.path.basename(urlparse(img_url).path)
            # 如果文件名为空或不包含扩展名，生成一个随机文件名
            if not img_filename or '.' not in img_filename:
                img_filename = f"img_{uuid.uuid4().hex[:8]}.jpg"
            
            # 完整的本地保存路径
            local_path = os.path.join(news_image_dir, img_filename)
            
            # 下载图片
            response = requests.get(img_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # 获取内容类型
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                self.logger.warning("非图片内容类型: %s, URL: %s", content_type, img_url)
                return None
            
            # 确定图片格式
            img_format = None
            if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                img_format = 'JPEG'
                if not local_path.lower().endswith(('.jpg', '.jpeg')):
                    local_path = f"{os.path.splitext(local_path)[0]}.jpg"
            elif 'image/png' in content_type:
                img_format = 'PNG'
                if not local_path.lower().endswith('.png'):
                    local_path = f"{os.path.splitext(local_path)[0]}.png"
            elif 'image/webp' in content_type:
                img_format = 'WEBP'
                if not local_path.lower().endswith('.webp'):
                    local_path = f"{os.path.splitext(local_path)[0]}.webp"
            else:
                img_format = 'JPEG'  # 默认格式
                if not local_path.lower().endswith(('.jpg', '.jpeg')):
                    local_path = f"{os.path.splitext(local_path)[0]}.jpg"
            
            # 保存图片
            with Image.open(BytesIO(response.content)) as img:
                # 压缩大图片
                if max(img.size) > 1200:
                    # 保持宽高比例等比例缩小
                    width, height = img.size
                    if width > height:
                        new_width = 1200
                        new_height = int(height * (1200 / width))
                    else:
                        new_height = 1200
                        new_width = int(width * (1200 / height))
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 获取质量参数
                quality = self.settings.get('IMAGE_QUALITY', 85)
                
                # 保存图片
                img.save(local_path, format=img_format, quality=quality, optimize=True)
                self.logger.info("图片已保存到: %s", local_path)
            
            return local_path
            
        except (requests.RequestException, IOError, Image.UnidentifiedImageError) as e:
            self.logger.error("保存图片失败: %s, 错误: %s", img_url, str(e))
            return None

    def get_info(self) -> Dict[str, Any]:
        """
        获取爬虫信息和统计数据
        
        Returns:
            Dict[str, Any]: 爬虫信息字典
        """
        # 获取数据库中的文章数量
        try:
            article_count = self.get_news_count()
            self.stats['total_articles'] = article_count
        except Exception as e:
            self.logger.error("获取文章数量失败: %s", str(e))
        
        # 构建爬虫信息
        info = {
            'source': self.source,
            'crawler_type': self.__class__.__name__,
            'capabilities': {
                'use_selenium': hasattr(self, 'use_selenium') and self.use_selenium,
                'use_proxy': hasattr(self, 'use_proxy') and self.use_proxy,
            },
            'db_path': self.db_manager.db_path,
            'stats': self.stats
        }
        
        # 添加自定义属性（子类可以覆盖这个方法以添加更多信息）
        custom_info = self._get_custom_info()
        if custom_info:
            info.update(custom_info)
        
        return info

    def _get_custom_info(self) -> Dict[str, Any]:
        """
        获取爬虫的自定义信息，子类可覆盖此方法
        
        Returns:
            Dict[str, Any]: 自定义爬虫信息
        """
        return {}

    def update_stats(self, articles_count: int, success: bool = True):
        """
        更新爬虫统计信息
        
        Args:
            articles_count: 本次爬取的文章数量
            success: 爬取是否成功
        """
        self.stats['last_crawl_time'] = datetime.now().isoformat()
        self.stats['last_crawl_articles'] = articles_count
        
        if success:
            self.stats['successful_crawls'] += 1
        else:
            self.stats['failed_crawls'] += 1

    def save_news_to_db(self, news_data: Dict[str, Any]) -> bool:
        """
        将单个新闻条目保存到其来源对应的数据库。
        
        Args:
            news_data (Dict[str, Any]): 经过初步预处理的新闻数据字典。
                                         必须包含 'source' 字段。
        
        Returns:
            bool: 如果成功保存到数据库则返回 True，否则返回 False。
        """
        if not self.db_manager:
            self.logger.error("[BaseCrawler.save_news_to_db] db_manager 未初始化，无法保存新闻。")
            return False

        if not news_data.get('source'):
            # self.source 应该在 _preprocess_news_data 中被设置到 news_data['source']
            # 但以防万一，这里再次检查，并尝试使用爬虫实例的 self.source
            current_source = getattr(self, 'source', None)
            if current_source:
                news_data['source'] = current_source
                self.logger.warning(f"[BaseCrawler.save_news_to_db] news_data 中缺少 'source' 字段，已使用爬虫实例的 source: {current_source}")
            else:
                self.logger.error(f"[BaseCrawler.save_news_to_db] news_data 和爬虫实例中均缺少 'source' 字段，无法确定目标数据库。标题: {news_data.get('title', 'N/A')}")
                return False
        
        # 调用 SQLiteManager 的 save_to_source_db 方法
        # 该方法会处理目标数据库路径的确定、连接获取以及实际的插入/替换操作。
        # _preprocess_news_data 已经被调用，这里传递的数据应该是相对干净的。
        # SQLiteManager._preprocess_news_data 会进行更细致的最终处理。
        self.logger.debug(f"[BaseCrawler.save_news_to_db] 准备调用 db_manager.save_to_source_db for source: {news_data['source']}, title: {news_data.get('title')}")
        try:
            # SQLiteManager.save_to_source_db 内部会调用 _preprocess_news_data 和 insert_news
            success = self.db_manager.save_to_source_db(news_data) 
            if success:
                self.logger.info(f"[BaseCrawler.save_news_to_db] 成功保存新闻到来源数据库 '{news_data['source']}': {news_data.get('title')}")
                if hasattr(self, 'stats') and hasattr(self.stats, 'increment'):
                    self.stats.increment('saved_to_db')
            else:
                self.logger.warning(f"[BaseCrawler.save_news_to_db] db_manager.save_to_source_db 未成功保存新闻到来源数据库 '{news_data['source']}': {news_data.get('title')}")
                if hasattr(self, 'stats') and hasattr(self.stats, 'increment'):
                    self.stats.increment('failed_to_save_db')
            return success
        except Exception as e:
            self.logger.error(f"[BaseCrawler.save_news_to_db] 调用 db_manager.save_to_source_db 时发生意外错误 for source '{news_data['source']}': {e}", exc_info=True)
            if hasattr(self, 'stats') and hasattr(self.stats, 'increment'):
                self.stats.increment('failed_to_save_db')
            return False

    def run(self, **kwargs):
        """
        运行爬虫
        
        Args:
            **kwargs: 其他参数
        """
        # 实现爬虫的运行逻辑
        try:
            self.logger.info(f"开始运行爬虫: {self.source} (class: {self.__class__.__name__})")
            # days = kwargs.get('days', self.settings.DEFAULT_CRAWL_DAYS) # 从kwargs或配置获取
            # self.crawl(days=days)
            self.crawl(**kwargs) # 将所有kwargs传递给crawl方法
            self.logger.info(f"爬虫 {self.source} 运行完成。")
            self.logger.info(f"统计: {self.stats}")
        except NotImplementedError:
            self.logger.error(f"爬虫 {self.source} 的 crawl 方法未实现!")
        except Exception as e:
            self.logger.error(f"爬虫 {self.source} 运行时发生错误: {e}", exc_info=True)

    def get_news(self, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取新闻列表.
        Triggers the crawl process for the specified number of days and then retrieves news from the database.
        
        Args:
            days: 最近几天的新闻
            
        Returns:
            List[Dict[str, Any]]: 新闻列表
        """
        if days is None:
            # Use settings for default crawl days
            days = self.settings.get('DEFAULT_CRAWL_DAYS', 1) 
        
        self.logger.info(f"({self.source}) get_news: 开始获取最近 {days} 天的新闻...")
        
        try:
            # 1. Trigger the crawl process. 
            # Subclass crawl method should handle the 'days' parameter.
            self.logger.info(f"({self.source}) get_news: 调用 self.crawl(days={days}) 来填充数据库。")
            self.crawl(days=days) 
            
            # 2. After crawling, fetch data from the database.
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            if not self.db_manager:
                self.logger.error(f"({self.source}) get_news: 数据库管理器未初始化，无法获取新闻。")
                return []

            # Assuming SQLiteManager has a method to fetch news for a specific source and date range.
            # This was the structure in a previous correct version.
            # If SQLiteManager's API changed, this might need adjustment.
            # For now, restoring the intended logic flow.
            self.logger.info(f"({self.source}) get_news: 从数据库查询 {self.source} 从 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 的新闻。")
            news_items = []
            if hasattr(self.db_manager, 'get_news_from_source_db'):
                 news_items = self.db_manager.get_news_from_source_db(
                    source_name=self.source,
                    start_date_str=start_date.strftime('%Y-%m-%d'),
                    end_date_str=end_date.strftime('%Y-%m-%d')
                )
            elif hasattr(self.db_manager, 'get_news_by_date_range_for_source'): # Fallback for another possible method name
                 news_items = self.db_manager.get_news_by_date_range_for_source(
                    source=self.source,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
            else:
                self.logger.warning(f"({self.source}) get_news: SQLiteManager does not have a recognized method to fetch source-specific news by date range (e.g., get_news_from_source_db).")


            self.logger.info(f"({self.source}) get_news: 从数据库获取到 {len(news_items)} 条新闻。")
            return news_items

        except NotImplementedError:
            self.logger.error(f"({self.source}) get_news: crawl 方法未实现，无法执行。")
            return []
        except Exception as e:
            self.logger.error(f"({self.source}) get_news: 执行过程中发生错误: {e}", exc_info=True)
            return []
