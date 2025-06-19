#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 爬虫基类
"""

import os
import sys
import time
import random
import requests
from datetime import datetime
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

from backend.app.utils.logger import get_logger, get_crawler_logger
from backend.app.utils.sentiment_analyzer import SentimentAnalyzer
from backend.app.utils.database import DatabaseManager
from backend.app.config import get_settings

# 导入统一数据库路径配置
from backend.newslook.config import get_unified_db_path, get_unified_db_dir

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('base')

class BaseCrawler:
    """爬虫基类，提供所有爬虫共用的基础功能"""
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化爬虫基类
        
        Args:
            db_manager: 数据库管理器对象，如果提供则优先使用
            db_path: 数据库路径，如果为None则使用统一配置路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库（已废弃，统一使用主数据库）
            **kwargs: 其他参数
        """
        # 属性初始化 - 确保source属性被正确设置
        # 注意：子类必须在调用super().__init__之前设置self.source属性
        # 否则将使用kwargs中的source或默认为"未知来源"
        if not hasattr(self, 'source'):
            self.source = kwargs.get('source', "未知来源")
            if self.source == "未知来源":
                logger.warning(f"{self.__class__.__name__}未设置source属性，将使用默认值'{self.source}'")
        
        self.news_data = []  # 存储爬取的新闻数据
        self.use_proxy = use_proxy
        self.proxies = None
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
        
        # 使用统一的数据库路径配置
        if db_path is None:
            # 如果没有指定db_path，使用统一配置的路径
            self.db_path = get_unified_db_path()
            logger.info(f"使用统一配置的数据库路径: {self.db_path}")
        else:
            # 如果指定了db_path，进行路径标准化
            if not os.path.isabs(db_path):
                # 相对路径转换为基于统一数据库目录的绝对路径
                unified_db_dir = get_unified_db_dir()
                self.db_path = os.path.join(unified_db_dir, db_path)
            else:
                self.db_path = db_path
            logger.info(f"使用指定的数据库路径: {self.db_path}")
        
        # 忽略 use_source_db 参数，统一使用主数据库
        if use_source_db:
            logger.warning("use_source_db 参数已废弃，统一使用主数据库")
        
        # 如果提供了db_manager，直接使用
        if db_manager:
            self.db_manager = db_manager
            if hasattr(db_manager, 'db_path'):
                # 确保db_manager使用统一的数据库路径
                if db_manager.db_path != self.db_path:
                    logger.warning(f"db_manager路径 {db_manager.db_path} 与统一路径 {self.db_path} 不一致，将使用统一路径")
                    db_manager.db_path = self.db_path
            else:
                setattr(db_manager, 'db_path', self.db_path)
            logger.info(f"使用提供的数据库管理器，数据库路径: {self.db_path}")
        else:
            # 初始化数据库管理器
            self.db_manager = DatabaseManager()
            
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            # 设置db_manager的db_path属性
            if not hasattr(self.db_manager, 'db_path'):
                setattr(self.db_manager, 'db_path', self.db_path)
        
        # 初始化连接
        self.conn = None
        try:
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"创建数据库目录: {db_dir}")
            
            if os.path.exists(self.db_path):
                logger.info(f"连接到现有数据库: {self.db_path}")
            else:
                logger.info(f"创建新数据库: {self.db_path}")
            
            # 初始化数据库连接
            if hasattr(self.db_manager, 'get_connection'):
                self.conn = self.db_manager.get_connection(self.db_path)
                
                # 验证表是否存在，如果不存在则创建
                cursor = self.conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                if not cursor.fetchone():
                    logger.info(f"数据库表不存在，正在创建表结构: {self.db_path}")
                    self.db_manager.init_db(self.conn)
        except Exception as e:
            logger.error(f"连接数据库失败: {str(e)}")
            # 尝试重新创建数据库
            try:
                logger.info(f"尝试重新创建数据库: {self.db_path}")
                self.conn = self.db_manager.get_connection(self.db_path)
                self.db_manager.init_db(self.conn)
            except Exception as e2:
                logger.error(f"重新创建数据库失败: {str(e2)}")
        
        # 初始化Selenium相关属性
        self.use_selenium = False
        self.driver = None
        
        # 尝试使用fake_useragent生成随机User-Agent
        try:
            self.ua = UserAgent()
        except Exception as e:
            logging.warning(f"初始化UserAgent失败: {str(e)}，将使用预定义的User-Agent列表")
            self.ua = None
        
        logger.info(f"初始化爬虫: {self.source}, 统一数据库路径: {self.db_path}")
    
    def __del__(self):
        """析构函数，关闭数据库连接和Selenium驱动"""
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                logger.debug("数据库连接已关闭")
            
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                logger.debug("Selenium驱动已关闭")
        except Exception as e:
            logger.error(f"关闭资源时出错: {str(e)}")
    
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
                    logging.info(f"第 {attempt+1}/{max_retries} 次重试，等待 {backoff_time:.2f} 秒")
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
                        logging.warning(f"响应内容过短，可能被反爬: {url}, 长度: {len(response.text)}")
                    
                    # 检查是否包含反爬关键词
                    anti_crawl_keywords = [
                        "访问频率过高", "访问过于频繁", "请求频率超过限制", "请输入验证码", "人机验证",
                        "访问受限", "禁止访问", "拒绝访问", "访问被拒绝", "IP被封",
                        "blocked", "forbidden", "denied", "captcha", "verify",
                        "too many requests", "rate limit exceeded", "请稍后再试"
                    ]
                    
                    for keyword in anti_crawl_keywords:
                        if keyword in response.text:
                            logging.warning(f"检测到反爬虫措施: {url}")
                            break
                    else:
                        # 未检测到反爬关键词，返回响应
                        return response
                
                # 处理特定的HTTP错误
                if response.status_code == 403:
                    logging.warning(f"访问被禁止 (403): {url}")
                elif response.status_code == 404:
                    logging.warning(f"页面不存在 (404): {url}")
                    return None  # 对于404错误，直接返回None，不再重试
                elif response.status_code == 429:
                    logging.warning(f"请求过多 (429): {url}")
                elif response.status_code >= 500:
                    logging.warning(f"服务器错误 ({response.status_code}): {url}")
                else:
                    logging.warning(f"HTTP错误 ({response.status_code}): {url}")
                
            except requests.exceptions.Timeout:
                logging.warning(f"请求超时: {url}")
            except requests.exceptions.ConnectionError:
                logging.warning(f"连接错误: {url}")
            except requests.exceptions.RequestException as e:
                logging.warning(f"请求异常: {url}, 错误: {str(e)}")
            except Exception as e:
                logging.warning(f"未知错误: {url}, 错误: {str(e)}")
        
        # 所有重试都失败
        logging.error(f"获取页面失败，已重试 {max_retries} 次: {url}")
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
            self.proxies = self.get_proxy()
        
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
                    logger.warning(f"非HTML或JSON内容: {content_type}, URL: {url}")
                    return None
                
                # 检查内容长度
                if len(response.text) < 100:
                    logger.warning(f"页面内容过短，可能被反爬: {url}")
                    return None
                
                return response.text
            except requests.exceptions.RequestException as e:
                logger.warning(f"获取页面失败: {url}, 错误: {str(e)}, 重试: {i+1}/{retry}")
                
                # 如果使用代理且失败，则更换代理
                if self.use_proxy:
                    self.proxies = self.get_proxy()
                
                # 随机休眠，避免被反爬
                time.sleep(random.uniform(1, 3))
        
        logger.error(f"获取页面失败，已达到最大重试次数: {url}")
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
                    logger.warning(f"页面内容过短，可能被反爬: {url}")
                    return None
                
                return html
            except Exception as e:
                logger.warning(f"使用Selenium获取页面失败: {url}, 错误: {str(e)}, 重试: {i+1}/{retry}")
                
                # 随机休眠，避免被反爬
                time.sleep(random.uniform(1, 3))
        
        logger.error(f"使用Selenium获取页面失败，已达到最大重试次数: {url}")
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
                proxy = list(self.proxies.values())[0]
                chrome_options.add_argument(f'--proxy-server={proxy}')
            
            # 初始化驱动
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            
            logger.info("Selenium驱动初始化成功")
        except Exception as e:
            logger.error(f"初始化Selenium驱动失败: {str(e)}")
            self.use_selenium = False
    
    def get_proxy(self):
        """
        获取代理
        
        Returns:
            dict: 代理配置
        """
        # 这里可以实现获取代理的逻辑，例如从代理池获取
        # 简单起见，这里返回一个固定的代理
        return {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }
    
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
        logging.debug(f"随机休眠 {sleep_time:.2f} 秒")
        time.sleep(sleep_time)
    
    def save_news(self, news_data):
        """
        保存新闻数据（首先尝试保存到数据库，如果无法保存则收集到内存列表）
        
        Args:
            news_data: 新闻数据字典
        
        Returns:
            bool: 是否成功添加
        """
        try:
            # 检查news_data是否包含必要的字段
            required_fields = ['id', 'title', 'content', 'pub_time', 'source', 'url']
            for field in required_fields:
                if field not in news_data:
                    logger.warning(f"新闻数据缺少必要字段: {field}")
                    return False
            
            # 确保所有必要字段都有值
            if 'author' not in news_data or not news_data['author']:
                news_data['author'] = self.source
                
            if 'sentiment' not in news_data or not news_data['sentiment']:
                news_data['sentiment'] = '中性'
                
            if 'crawl_time' not in news_data:
                news_data['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
            if 'keywords' not in news_data:
                news_data['keywords'] = ''
                
            if 'category' not in news_data:
                news_data['category'] = '财经'
                
            if 'images' not in news_data:
                news_data['images'] = ''
                
            if 'related_stocks' not in news_data:
                news_data['related_stocks'] = ''
            
            # 首先尝试保存到数据库
            saved_to_db = False
            if hasattr(self, 'db_manager') and hasattr(self.db_manager, 'save_news'):
                try:
                    saved_to_db = self.db_manager.save_news(news_data)
                    if saved_to_db:
                        logger.info(f"新闻已保存到数据库: {news_data['title']}")
                        return True
                except Exception as e:
                    logger.error(f"保存新闻到数据库失败: {str(e)}")
            
            # 如果无法保存到数据库，则保存到内存列表
            if not saved_to_db:
                # 检查是否已在内存中存在
                if hasattr(self, 'news_data'):
                    if any(news['id'] == news_data['id'] for news in self.news_data):
                        logger.debug(f"新闻已存在于内存中: {news_data['title']}")
                        return False
                else:
                    # 初始化新闻数据列表
                    self.news_data = []
                
                # 将新闻添加到内存列表
                self.news_data.append(news_data)
                logger.info(f"新闻已添加到内存列表: {news_data['title']}")
                return True
            
        except Exception as e:
            logger.error(f"保存新闻失败: {str(e)}")
            if 'title' in news_data:
                logger.error(f"标题: {news_data['title']}")
            return False
    
    def get_news_count(self):
        """
        获取数据库中的新闻数量
        
        Returns:
            int: 新闻数量
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM news")
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.error(f"获取新闻数量失败: {str(e)}")
            return 0
    
    def get_news_by_category(self, category):
        """
        获取指定分类的新闻
        
        Args:
            category: 新闻分类
        
        Returns:
            list: 新闻列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM news WHERE category = ? ORDER BY pub_time DESC", (category,))
            news_list = cursor.fetchall()
            
            # 将查询结果转换为字典列表
            columns = [column[0] for column in cursor.description]
            result = []
            for row in news_list:
                news_dict = dict(zip(columns, row))
                result.append(news_dict)
            
            return result
        except Exception as e:
            logger.error(f"获取分类新闻失败: {category}, 错误: {str(e)}")
            return []
    
    def get_news_by_date_range(self, start_date, end_date):
        """
        获取指定日期范围的新闻
        
        Args:
            start_date: 开始日期，格式为'YYYY-MM-DD'
            end_date: 结束日期，格式为'YYYY-MM-DD'
        
        Returns:
            list: 新闻列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM news 
                WHERE pub_time BETWEEN ? AND ? 
                ORDER BY pub_time DESC
            """, (start_date, end_date))
            news_list = cursor.fetchall()
            
            # 将查询结果转换为字典列表
            columns = [column[0] for column in cursor.description]
            result = []
            for row in news_list:
                news_dict = dict(zip(columns, row))
                result.append(news_dict)
            
            return result
        except Exception as e:
            logger.error(f"获取日期范围新闻失败: {start_date} - {end_date}, 错误: {str(e)}")
            return []
    
    def search_news(self, keyword):
        """
        搜索新闻
        
        Args:
            keyword: 关键词
        
        Returns:
            list: 新闻列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM news 
                WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ? 
                ORDER BY pub_time DESC
            """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
            news_list = cursor.fetchall()
            
            # 将查询结果转换为字典列表
            columns = [column[0] for column in cursor.description]
            result = []
            for row in news_list:
                news_dict = dict(zip(columns, row))
                result.append(news_dict)
            
            return result
        except Exception as e:
            logger.error(f"搜索新闻失败: {keyword}, 错误: {str(e)}")
            return []
    
    def get_random_user_agent(self):
        """获取随机User-Agent"""
        if self.ua:
            try:
                return self.ua.random
            except Exception as e:
                logging.warning(f"获取随机User-Agent失败: {str(e)}，将使用预定义的User-Agent")
        
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
        logger.info(f"数据库路径: {db_path}")
        
        return db_path
