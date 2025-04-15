#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新浪财经爬虫模块
"""

import re
import os
import time
import json
import sqlite3
import logging
import random
import hashlib
import traceback
import requests
from datetime import datetime, timedelta
from urllib.parse import quote
from bs4 import BeautifulSoup
from bs4.element import Comment
from app.utils.database import DatabaseManager
from app.utils.proxy_manager import ProxyManager
from app.utils.logger import get_crawler_logger

# 设置日志
logger = get_crawler_logger('新浪财经')

"""
财经新闻爬虫系统 - 新浪财经爬虫
"""

# 广告链接模式
ad_patterns = [
    'sinaads', 'adbox', 'advertisement', 'promotion', 'sponsor', 
    'click.sina', 'sina.cn', 'game.weibo', 'games.sina', 'iask'
]

class SinaCrawler:
    """新浪财经爬虫，用于爬取新浪财经的财经新闻"""
    
    # 分类URL映射
    CATEGORY_URLS = {
        '财经': 'https://finance.sina.com.cn/',
        '股票': 'https://finance.sina.com.cn/stock/',
        '新股': 'https://finance.sina.com.cn/roll/index.d.html?cid=56592',
        '港股': 'https://finance.sina.com.cn/stock/hkstock/',
        '美股': 'https://finance.sina.com.cn/stock/usstock/',
        '基金': 'https://finance.sina.com.cn/fund/',
        '期货': 'https://finance.sina.com.cn/futures/',
        '外汇': 'https://finance.sina.com.cn/forex/',
        '黄金': 'https://finance.sina.com.cn/nmetal/',
        '债券': 'https://finance.sina.com.cn/bond/',
        '科技': 'https://tech.sina.com.cn/',
        '股市及时雨': 'https://finance.sina.com.cn/roll/index.d.html?cid=56589',
        '薪酬趋势': 'https://finance.sina.com.cn/roll/index.d.html?cid=56637',
        '宏观研究': 'https://finance.sina.com.cn/roll/index.d.html?cid=56598',
        '个股点评': 'https://finance.sina.com.cn/roll/index.d.html?cid=56588'
    }
    
    # 股票页面选择器
    STOCK_PAGE_SELECTORS = {
        'news_links': 'div.news_list ul li a, div.m-list li a, div.f-list li a',
        'stock_indices': 'table.tb_01 tr',
        'stock_data': 'table.tb_02 tr'
    }
    
    # 用户代理列表
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
    ]
    
    def __init__(self, config=None):
        """
        初始化新浪财经爬虫
        
        Args:
            config: 配置字典，包含以下可选键：
                - db_path: 数据库路径
                - db_manager: 数据库管理器
                - use_proxy: 是否使用代理
                - use_async: 是否使用异步
        """
        # 初始化配置
        self.config = config or {}
        
        # 初始化数据库
        self._init_database()
        
        # 初始化会话
        self.session = requests.Session()
        
        # 初始化代理设置
        self._init_proxy()
        
        # 初始化异步设置
        self.use_async = self.config.get('use_async', False)
        self.async_session = None
        
        # 初始化统计信息
        self.success_count = 0
        self.fail_count = 0
        self.news_data = []
        
        # 初始化配置
        self._init_config()
        
        # 初始化源
        self.source = '新浪财经'
        
        # 初始化线程锁，用于多线程环境下的数据同步
        self._lock = None
        
        logger.info("新浪财经爬虫初始化完成，数据库路径: %s", self.db_path)
    
    def _init_database(self):
        """初始化数据库设置"""
        # 获取数据库路径和管理器
        self.db_path = self.config.get('db_path')
        self.db_manager = self.config.get('db_manager')
        
        # 如果没有提供数据库管理器，则创建一个
        if not self.db_manager and self.db_path:
            self.db_manager = DatabaseManager(self.db_path)
    
    def _init_proxy(self):
        """初始化代理设置"""
        self.use_proxy = self.config.get('use_proxy', False)
        self.current_proxy = None
        
        if self.use_proxy:
            self.proxy_manager = ProxyManager()
    
    def _init_config(self):
        """初始化爬虫配置"""
        try:
            # 配置已经在Config初始化时自动加载
            logger.info("成功加载配置文件")
        except (IOError, ValueError, KeyError) as e:
            logger.warning("加载配置文件失败: %s, 使用默认配置", str(e))
            # 设置默认配置
            self.crawler_config = {
                'crawler': {
                    'max_retries': 3,
                    'timeout': 10,
                    'request_delay': 1,
                    'max_pages_per_category': 3
                }
            }
    
    def fetch_page(self, url, retries=3):
        """
        获取页面内容
        
        Args:
            url (str): 页面URL
            retries (int): 重试次数
            
        Returns:
            str: 页面内容，获取失败则返回None
        """
        # 随机选择一个User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        user_agent = random.choice(user_agents)
        
        # 设置请求头
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # 尝试获取页面内容
        for attempt in range(retries):
            try:
                # 发送请求
                response = self.session.get(url, headers=headers, timeout=10)
                
                # 检查状态码
                if response.status_code == 200:
                    # 确保返回的是HTML内容
                    if 'text/html' in response.headers.get('Content-Type', ''):
                        # 尝试自动检测编码
                        if response.encoding == 'ISO-8859-1':
                            # 尝试从内容中检测编码
                            encodings = ['utf-8', 'gb2312', 'gbk', 'gb18030']
                            for enc in encodings:
                                try:
                                    content = response.content.decode(enc)
                                    return content
                                except UnicodeDecodeError:
                                    continue
                            
                            # 如果所有尝试都失败，使用apparent_encoding
                            response.encoding = response.apparent_encoding
                        else:
                            # 使用响应头中的编码
                            response.encoding = 'utf-8'
                        
                        return response.text
                    else:
                        logger.warning("非HTML内容: %s, Content-Type: %s", url, response.headers.get('Content-Type'))
                        return None
                else:
                    logger.warning("请求失败，状态码: %d，重试中: %s", response.status_code, url)
                    time.sleep(2 * (attempt + 1))  # 指数退避
            except requests.RequestException as e:
                logger.warning("请求异常: %s, 重试中: %s", str(e), url)
                time.sleep(2 * (attempt + 1))
        
        logger.error("获取页面内容失败，已重试 %d 次: %s", retries, url)
        return None
    
    def extract_publish_time(self, soup):
        """
        从HTML中提取发布时间
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 发布时间，格式为 YYYY-MM-DD HH:MM:SS
        """
        return self._extract_publish_time(soup)
    
    def extract_content(self, soup):
        """
        提取正文内容
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 正文内容
        """
        return self._extract_content(soup)
    
    def extract_author(self, soup):
        """
        提取作者/来源
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 作者/来源
        """
        return self._extract_author(soup)
    
    def extract_keywords(self, soup, content):
        """
        提取关键词
        
        Args:
            soup: BeautifulSoup对象
            content: 正文内容
            
        Returns:
            list: 关键词列表
        """
        return self._extract_keywords(soup, content)
    
    def extract_images(self, soup):
        """
        提取图片URL
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            list: 图片URL列表
        """
        return self._extract_images(soup)
    
    def extract_related_stocks(self, soup):
        """
        提取相关股票
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            list: 相关股票列表
        """
        return self._extract_related_stocks(soup)
    
    def _generate_news_id(self, url, title):
        """
        生成新闻ID
        
        Args:
            url: 新闻URL
            title: 新闻标题
        
        Returns:
            str: 新闻ID
        """
        try:
            # 使用URL和标题的组合生成唯一的新闻ID
            # 确保输入是字符串
            url = str(url) if url else ""
            title = str(title) if title else ""
            
            # 组合并编码
            combined = (url + title).encode('utf-8')
            
            # 使用MD5哈希算法生成ID
            return hashlib.md5(combined).hexdigest()
        except Exception as e:
            logger.error("生成新闻ID时发生错误: %s, URL: %s, 标题: %s", str(e), url, title)
            # 使用时间戳作为备用ID
            return hashlib.md5(str(time.time()).encode('utf-8')).hexdigest()
    
    def process_news_link(self, url, category=None):
        """
        处理新闻链接，爬取新闻详情
        
        Args:
            url: 新闻链接
            category: 新闻分类
            
        Returns:
            dict: 新闻数据
        """
        if not url:
            return None
        
        # 验证URL
        if not self.validate_url(url):
            logger.info("过滤无效URL: %s", url)
            return None
        
        try:
            # 获取页面内容
            html = self.fetch_page(url)
            if not html:
                logger.warning("获取页面内容失败: %s", url)
                return None
            
            # 解析页面内容
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title = self._extract_title(soup)
            if not title:
                logger.warning("未找到标题: %s", url)
                return None
            
            title = title.encode('latin1').decode('utf-8') if '\\' in title else title
            
            # 提取发布时间
            pub_time = self._extract_publish_time(soup)
            
            # 提取正文内容
            content = self._extract_content(soup)
            if not content:
                logger.warning("未找到正文内容: %s", url)
                return None
            
            # 提取作者/来源
            author = self._extract_author(soup)
            
            # 提取关键词
            keywords = self._extract_keywords(soup, content)
            
            # 提取图片URL
            image_urls = self._extract_images(soup)
            
            # 提取相关股票
            related_stocks = self._extract_related_stocks(soup)
            
            # 生成新闻ID
            news_id = self._generate_news_id(url, title)
            
            # 构建新闻数据
            news_data = {
                'id': news_id,
                'title': title,
                'content': content,
                'pub_time': pub_time,
                'source': '新浪财经',
                'author': author,
                'category': category if category else '财经',
                'url': url,
                'keywords': ','.join(keywords) if keywords else '',
                'images': ','.join(image_urls) if image_urls else '',
                'related_stocks': ','.join(related_stocks) if related_stocks else '',
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return news_data
        except (IOError, ValueError, AttributeError, requests.RequestException) as e:
            logger.error("处理新闻链接失败: %s, 错误: %s", url, str(e))
            return None
            
    def save_news_to_db(self, news_data):
        """
        保存新闻到数据库
        
        Args:
            news_data: 新闻数据
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 如果有数据库管理器，则保存到数据库
            if hasattr(self, 'db_manager') and self.db_manager:
                return self.db_manager.save_news(news_data)
            
            # 否则保存到内存中
            self.news_data.append(news_data)
            return True
        except (IOError, ValueError, AttributeError, TypeError) as e:
            logger.error("保存新闻到数据库失败: %s, 错误: %s", news_data.get('title', '未知标题'), str(e))
            return False
            
    def validate_url(self, url):
        """
        验证URL是否有效
        
        Args:
            url (str): 要验证的URL
            
        Returns:
            bool: URL是否有效
        """
        # 检查URL是否为空
        if not url:
            return False
            
        # 检查URL是否为绝对URL
        if not url.startswith('http'):
            return False
            
        # 检查URL是否来自新浪
        if 'sina.com.cn' not in url:
            return False
            
        # 检查URL是否为广告
        for pattern in ad_patterns:
            if pattern in url.lower():
                return False
                
        # 检查URL是否为列表页面
        if any(pattern in url for pattern in [
            '/index.d.html', 
            '/index.shtml',
            '?cid=',
            '?fid=',
            '/roll/',
            '/quotes/',
            '/globalindex/',
            '/fund/quotes/',
            '/forex/quotes/',
            '/futures/quotes/',
            '/otc/',
            '/nmetal/',
            '/bond/',
            '/futuremarket/',
            '/zt_d/',
            '/sinachanganforum/',
            '/xiongan/'
        ]):
            return False
            
        # 检查URL是否为首页或分类首页
        if url in [
            'http://finance.sina.com.cn/',
            'https://finance.sina.com.cn/',
            'http://finance.sina.com.cn/stock/',
            'https://finance.sina.com.cn/stock/',
            'http://finance.sina.com.cn/fund/',
            'https://finance.sina.com.cn/fund/',
            'http://finance.sina.com.cn/forex/',
            'https://finance.sina.com.cn/forex/',
            'http://finance.sina.com.cn/futures/',
            'https://finance.sina.com.cn/futures/',
            'http://finance.sina.com.cn/bond/',
            'https://finance.sina.com.cn/bond/',
            'http://finance.sina.com.cn/nmetal/',
            'https://finance.sina.com.cn/nmetal/',
            'http://finance.sina.com.cn/futuremarket/',
            'https://finance.sina.com.cn/futuremarket/',
            'http://otc.finance.sina.com.cn/',
            'https://otc.finance.sina.com.cn/',
            'http://finance.sina.com.cn/stock/hkstock/',
            'https://finance.sina.com.cn/stock/hkstock/',
            'http://finance.sina.com.cn/stock/usstock/',
            'https://finance.sina.com.cn/stock/usstock/',
        ]:
            return False
        
        # 检查URL是否以.shtml或.html结尾，这通常是新闻页面
        if not (url.endswith('.shtml') or url.endswith('.html') or '/doc-' in url):
            return False
            
        return True
    
    def crawl(self, days=1, max_pages=3, category=None):
        """
        爬取新浪财经的新闻
        
        Args:
            days: 爬取的天数范围，默认为1天
            max_pages: 每个分类最多爬取的页数，默认为3页
            category: 指定要爬取的特定分类，默认为None（爬取所有分类）
            
        Returns:
            list: 爬取的新闻列表
        """
        # 重置统计信息
        self.success_count = 0
        self.fail_count = 0
        self.news_data = []
        
        # 保存天数设置，用于日期范围检查
        self.days = days
        
        logger.info("开始爬取新浪财经的新闻，天数范围: %d天, 每个分类最多爬取: %d页", days, max_pages)
        print(f"开始爬取新浪财经的新闻，天数范围: {days}天, 每个分类最多爬取: {max_pages}页")
        
        # 计算开始日期
        start_date = datetime.now() - timedelta(days=days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        logger.info("爬取的开始日期: %s", start_date_str)
        print(f"爬取的开始日期: {start_date_str}")
        
        # 如果指定了特定分类，只爬取该分类
        if category:
            if category in self.CATEGORY_URLS:
                logger.info("指定爬取分类: %s", category)
                print(f"指定爬取分类: {category}")
                base_url = self.CATEGORY_URLS[category]
                try:
                    self._crawl_category(category, base_url, start_date, max_pages)
                    logger.info("分类 %s 爬取完成", category)
                    print(f"分类 {category} 爬取完成")
                except requests.RequestException as e:
                    logger.error("爬取分类 %s 时发生请求异常: %s", category, str(e))
                    print(f"爬取分类 {category} 时发生请求异常: {str(e)}")
                    self.fail_count += 1
                except ValueError as e:
                    logger.error("爬取分类 %s 时发生值错误: %s", category, str(e))
                    print(f"爬取分类 {category} 时发生值错误: {str(e)}")
                    self.fail_count += 1
                except Exception as e:
                    logger.error("爬取分类 %s 时发生未知异常: %s", category, str(e))
                    logger.error("异常详情: %s", traceback.format_exc())
                    print(f"爬取分类 {category} 时发生未知异常: {str(e)}")
                    self.fail_count += 1
            else:
                logger.error("指定的分类 %s 不存在", category)
                print(f"指定的分类 {category} 不存在，可用分类: {', '.join(self.CATEGORY_URLS.keys())}")
                return self.news_data
        else:
            # 爬取每个分类
            for category, base_url in self.CATEGORY_URLS.items():
                logger.info("开始爬取分类: %s, URL: %s", category, base_url)
                print(f"开始爬取分类: {category}, URL: {base_url}")
                try:
                    self._crawl_category(category, base_url, start_date, max_pages)
                    logger.info("分类 %s 爬取完成", category)
                    print(f"分类 {category} 爬取完成")
                except requests.RequestException as e:
                    logger.error("爬取分类 %s 时发生请求异常: %s", category, str(e))
                    print(f"爬取分类 {category} 时发生请求异常: {str(e)}")
                    self.fail_count += 1
                except ValueError as e:
                    logger.error("爬取分类 %s 时发生值错误: %s", category, str(e))
                    print(f"爬取分类 {category} 时发生值错误: {str(e)}")
                    self.fail_count += 1
                except Exception as e:
                    logger.error("爬取分类 %s 时发生未知异常: %s", category, str(e))
                    logger.error("异常详情: %s", traceback.format_exc())
                    print(f"爬取分类 {category} 时发生未知异常: {str(e)}")
                    self.fail_count += 1
        
        logger.info("爬取完成，成功: %d, 失败: %d", self.success_count, self.fail_count)
        print(f"爬取完成，成功: {self.success_count}, 失败: {self.fail_count}")
        return self.news_data
    
    def _crawl_category(self, category, base_url, start_date, max_pages):
        """
        爬取特定分类的新闻
        
        Args:
            category: 分类名称
            base_url: 分类URL
            start_date: 开始日期
            max_pages: 最大页数
        """
        logger.info("开始爬取分类: %s, URL: %s", category, base_url)
        print(f"开始爬取分类: {category}, URL: {base_url}")
        
        try:
            # 获取分类页面
            html = self.fetch_page(base_url)
            if not html:
                logger.warning("获取分类页面失败: %s", base_url)
                print(f"获取分类页面失败: {base_url}")
                return
            
            # 解析页面，提取新闻链接
            soup = BeautifulSoup(html, 'html.parser')
            news_links = self._extract_news_links(soup)
            logger.info("从分类 %s 中提取到 %s 条新闻链接", category, len(news_links))
            print(f"从分类 {category} 中提取到 {len(news_links)} 条新闻链接")
            
            # 处理每个新闻链接
            self._process_news_links(news_links, category)
            
        except (IOError, ValueError, AttributeError, requests.RequestException) as e:
            logger.error("爬取分类 %s 失败: %s", category, str(e))
            print(f"爬取分类 {category} 失败: {str(e)}")
    
    def _extract_news_links(self, html):
        """
        从HTML中提取新闻链接
        
        Args:
            html: HTML内容
            
        Returns:
            list: 新闻链接列表
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            news_links = []
            
            # 尝试多种可能的链接选择器
            link_selectors = [
                'ul.list_009 li a',  # 传统新闻列表
                'div.feed-card-item h2 a',  # 新版新闻卡片
                'div.news-item h2 a',  # 另一种新闻卡片
                'li.news-item a',  # 简化新闻列表
                'div.m-list li a',  # 移动版列表
                'ul.list-a li a',  # 另一种列表样式
                'div.news-list a',  # 通用新闻列表
                'div.content a',  # 内容区域链接 (适用于基金页面)
                'div.tab-content a',  # 选项卡内容 (适用于基金页面)
                'div.fund-news a',  # 基金新闻区域 (适用于基金页面)
                'ul.fund_info_list li a',  # 基金信息列表 (适用于基金页面)
                'a[href*="finance.sina.com.cn/roll/index.d.html"]',  # 滚动新闻链接 (适用于基金页面)
                'a[href*="finance.sina.com.cn"]',  # 通用链接选择器
            ]
            
            for selector in link_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href and href.startswith('http') and href not in news_links:
                        # 过滤掉导航链接和非新闻内容
                        if any(pattern in href for pattern in ['sina.com.cn/guide/', 'sina.com.cn/mobile/', 'sinaimg.cn']):
                            continue
                        news_links.append(href)
            
            return news_links
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("提取新闻链接失败: %s", str(e))
            return []
    
    def _process_news_links(self, news_links, category):
        """
        处理新闻链接列表
        
        Args:
            news_links: 新闻链接列表
            category: 分类名称
        """
        # 限制每个分类处理的链接数量
        links_to_process = news_links[:20]  # 增加处理链接数量
        
        processed_count = 0
        for link in links_to_process:
            try:
                # 验证URL
                if not self.validate_url(link):
                    logger.debug("URL不符合要求，跳过: %s", link)
                    continue
                    
                # 获取新闻详情
                news = self.get_news_detail(link)
                if not news:
                    logger.debug("获取新闻详情失败，跳过: %s", link)
                    continue
                    
                # 添加分类信息
                news['category'] = category
                
                # 检查新闻日期是否在指定范围内
                if not self._is_news_in_date_range(news):
                    logger.debug("新闻日期不在指定范围内，跳过: %s", link)
                    continue
                
                # 保存到数据库
                if self._save_news(news):
                    logger.info("成功保存新闻: %s", news.get('title', '未知标题'))
                    print(f"成功保存新闻: {news.get('title', '未知标题')}")
                    self.success_count += 1
                    processed_count += 1
                else:
                    logger.warning("保存新闻失败: %s", news.get('title', '未知标题'))
                    print(f"保存新闻失败: {news.get('title', '未知标题')}")
                    self.fail_count += 1
                    
                # 随机延迟，避免请求过于频繁
                delay = random.uniform(1, 3)
                logger.debug("随机延时 %.2f 秒", delay)
                time.sleep(delay)
                
                # 如果已经处理了足够多的新闻，就停止
                if processed_count >= 10:  # 每个分类最多保存10条新闻
                    logger.info("已达到分类 %s 的最大处理数量限制", category)
                    break
                    
            except requests.RequestException as e:
                logger.warning("处理新闻链接失败: %s, 错误: %s", link, str(e))
                print(f"处理新闻链接失败: {link}, 错误: {str(e)}")
                self.fail_count += 1
            except Exception as e:
                logger.error("处理新闻链接时发生未知异常: %s, 错误: %s", link, str(e))
                logger.error("异常详情: %s", traceback.format_exc())
                self.fail_count += 1

    def get_news_detail(self, url):
        """
        获取新闻详情
        
        Args:
            url (str): 新闻URL
            
        Returns:
            dict: 新闻详情，获取失败则返回None
        """
        logger.info("获取新闻详情: %s", url)
        print(f"获取新闻详情: {url}")
        
        try:
            # 获取页面内容
            html = self.fetch_page(url)
            if not html:
                logger.warning("获取页面内容失败: %s", url)
                print(f"获取页面内容失败: {url}")
                return None
            
            # 解析页面内容
            try:
                soup = BeautifulSoup(html, 'html.parser')
                if not soup:
                    logger.warning("创建BeautifulSoup对象失败: %s", url)
                    print(f"创建BeautifulSoup对象失败: {url}")
                    return None
            except Exception as e:
                logger.warning("解析HTML内容失败: %s, 错误: %s", url, str(e))
                print(f"解析HTML内容失败: {url}, 错误: {str(e)}")
                return None
            
            # 提取标题
            title = self._extract_title(soup)
            if not title:
                logger.warning("提取标题失败: %s", url)
                print(f"提取标题失败: {url}")
                return None
            
            # 提取发布时间
            pub_time = self._extract_publish_time(soup)
            if not pub_time:
                logger.warning("提取发布时间失败: %s，使用当前时间", url)
                print(f"提取发布时间失败: {url}，使用当前时间")
                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 提取正文内容
            content = self._extract_content(soup)
            if not content:
                logger.warning("提取内容失败: %s", url)
                print(f"提取内容失败: {url}")
                return None
            
            # 提取作者
            author = self._extract_author(soup)
            
            # 提取关键词
            keywords = self._extract_keywords(soup, content)
            
            # 提取图片URL
            image_urls = self._extract_images(soup)
            
            # 提取相关股票
            related_stocks = self._extract_related_stocks(soup)
            
            # 生成新闻ID
            news_id = self._generate_news_id(url, title)
            
            # 构建新闻数据
            news_data = {
                'id': news_id,
                'url': url,
                'title': title,
                'content': content,
                'pub_time': pub_time,
                'author': author,
                'keywords': keywords,
                'source': '新浪财经',
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.debug("成功提取新闻详情: %s", title)
            return news_data
        except requests.RequestException as e:
            logger.error("请求新闻详情失败: %s, 错误: %s", url, str(e))
            print(f"请求新闻详情失败: {url}, 错误: {str(e)}")
            return None
        except Exception as e:
            logger.error("获取新闻详情时发生未知异常: %s, 错误: %s", url, str(e))
            logger.error("异常详情: %s", traceback.format_exc())
            print(f"获取新闻详情时发生未知异常: {url}, 错误: {str(e)}")
            return None

    def _init_config(self):
        """初始化配置"""
        try:
            # 初始化默认配置
            self.crawler_config = {
                'crawler': {
                    'request_delay': 1,
                    'max_pages_per_category': 3
                }
            }
        except (ValueError, AttributeError) as e:
            logger.error("初始化配置失败: %s", str(e))
            raise

    def _extract_publish_time(self, soup):
        """
        从HTML中提取发布时间
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 发布时间，格式为 YYYY-MM-DD HH:MM:SS
        """
        try:
            # 尝试从meta标签中提取时间
            pub_time_tag = soup.find('meta', attrs={'property': 'article:published_time'})
            if pub_time_tag and pub_time_tag.get('content'):
                pub_time = pub_time_tag['content'].split('+')[0].replace('T', ' ')
                if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', pub_time):
                    logger.debug("从meta标签提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从time标签中提取时间
            time_tag = soup.find('time')
            if time_tag and time_tag.get('datetime'):
                pub_time = time_tag['datetime'].split('+')[0].replace('T', ' ')
                if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', pub_time):
                    logger.debug("从time标签提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从新浪特定的时间标签中提取
            time_source = soup.find('span', class_='date')
            if time_source:
                time_text = time_source.get_text().strip()
                # 处理"2023年01月01日 12:34"格式
                match = re.search(r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})', time_text)
                if match:
                    year, month, day, hour, minute = match.groups()
                    pub_time = f"{year}-{month}-{day} {hour}:{minute}:00"
                    logger.debug("从date标签提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从class为'date-source'的div中提取
            date_source = soup.find('div', class_='date-source')
            if date_source:
                time_text = date_source.get_text().strip()
                # 处理"2023年01月01日 12:34"格式
                match = re.search(r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})', time_text)
                if match:
                    year, month, day, hour, minute = match.groups()
                    pub_time = f"{year}-{month}-{day} {hour}:{minute}:00"
                    logger.debug("从date-source提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从class为'time-source'的span中提取
            time_source = soup.find('span', class_='time-source')
            if time_source:
                time_text = time_source.get_text().strip()
                # 处理"2023-01-01 12:34:56"格式
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    logger.debug("从time-source提取到发布时间: %s", pub_time)
                    return pub_time
                
                # 处理"2023年01月01日 12:34"格式
                match = re.search(r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})', time_text)
                if match:
                    year, month, day, hour, minute = match.groups()
                    pub_time = f"{year}-{month}-{day} {hour}:{minute}:00"
                    logger.debug("从time-source提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从class为'publish_time'的标签中提取
            publish_time = soup.find(class_='publish_time')
            if publish_time:
                time_text = publish_time.get_text().strip()
                # 处理"2023-01-01 12:34:56"格式
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    logger.debug("从publish_time提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从class为'article-info'的div中提取
            article_info = soup.find('div', class_='article-info')
            if article_info:
                time_text = article_info.get_text().strip()
                # 处理"2023-01-01 12:34:56"格式
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    logger.debug("从article-info提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从class为'article-meta'的div中提取
            article_meta = soup.find('div', class_='article-meta')
            if article_meta:
                time_text = article_meta.get_text().strip()
                # 处理"2023-01-01 12:34:56"格式
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    logger.debug("从article-meta提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从class为'info'的div中提取
            info_div = soup.find('div', class_='info')
            if info_div:
                time_text = info_div.get_text().strip()
                # 处理"2023-01-01 12:34:56"格式
                match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)', time_text)
                if match:
                    pub_time = match.group(1)
                    if len(pub_time.split(':')) == 2:
                        pub_time += ':00'
                    logger.debug("从info提取到发布时间: %s", pub_time)
                    return pub_time
            
            # 尝试从全文中提取时间
            text = soup.get_text()
            # 处理"2023-01-01 12:34:56"格式
            match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
            if match:
                pub_time = match.group(1)
                logger.debug("从全文提取到发布时间: %s", pub_time)
                return pub_time
            
            # 处理"2023年01月01日 12:34"格式
            match = re.search(r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})', text)
            if match:
                year, month, day, hour, minute = match.groups()
                pub_time = f"{year}-{month}-{day} {hour}:{minute}:00"
                logger.debug("从全文提取到发布时间: %s", pub_time)
                return pub_time
            
            # 如果所有方法都失败，使用当前时间
            logger.warning("无法提取发布时间，使用当前时间")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.error("提取发布时间时出错: %s", str(e))
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _extract_content(self, soup):
        """
        提取正文内容
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 正文内容
        """
        try:
            # 尝试多种可能的正文选择器
            content_selectors = [
                'div.article-content',
                'div.article',
                'div#artibody',
                'div.main-content',
                'div.content',
                'article'
            ]
            
            for selector in content_selectors:
                content_tag = soup.select_one(selector)
                if content_tag:
                    # 移除脚本和样式
                    for script in content_tag.find_all(['script', 'style']):
                        script.decompose()
                    
                    # 移除注释
                    for comment in content_tag.find_all(text=lambda text: isinstance(text, Comment)):
                        comment.extract()
                    
                    # 移除广告和无关内容
                    ad_classes = ['recommend', 'related', 'footer', 'ad', 'bottom']
                    for ad_class in ad_classes:
                        ad_class_pattern = ad_class  # 在循环外定义变量
                        for div in content_tag.find_all(class_=lambda c: c and ad_class_pattern in str(c).lower()):
                            div.decompose()
                    
                    # 获取文本内容
                    content = content_tag.get_text('\n').strip()
                    
                    # 清理内容
                    content = re.sub(r'\n+', '\n', content)  # 移除多余换行
                    content = re.sub(r'\s+', ' ', content)   # 移除多余空格
                    
                    return content
            
            return None
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("提取正文内容失败: %s", str(e))
            return None
    
    def _extract_author(self, soup):
        """
        提取作者/来源
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 作者/来源
        """
        try:
            # 尝试多种可能的作者/来源选择器
            author_selectors = [
                'div.author',
                'div.source',
                'div.article-info span.source',
                'div.article-info span.author',
                'div.info span.source',
                'div.info span.author',
                'meta[name="author"]'
            ]
            
            for selector in author_selectors:
                author_tag = soup.select_one(selector)
                if author_tag:
                    if author_tag.name == 'meta':
                        author = author_tag.get('content', '')
                    else:
                        author = author_tag.get_text().strip()
                    
                    # 清理作者信息
                    author = re.sub(r'^来源[:：]', '', author)
                    author = re.sub(r'^作者[:：]', '', author)
                    
                    return author.strip()
            
            return '新浪财经'
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("提取作者/来源失败: %s", str(e))
            return '新浪财经'
    
    def _extract_title(self, soup):
        """
        从页面中提取标题
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
        
        Returns:
            str: 标题
        """
        # 尝试多种可能的标题选择器
        title_selectors = [
            'h1.main-title',
            'h1.title',
            'h1.article-title',
            'h1.news-title',
            'h1',
            'title'
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = title_element.text.strip()
                # 确保标题是有效的UTF-8字符串
                try:
                    title = title.encode('utf-8').decode('utf-8')
                except UnicodeError:
                    try:
                        title = title.encode('latin1').decode('utf-8')
                    except UnicodeError:
                        title = title.encode('utf-8', 'ignore').decode('utf-8')
                
                # 移除多余空白字符
                title = re.sub(r'\s+', ' ', title)
                
                # 移除标题中的特殊字符
                title = re.sub(r'[\r\n\t]', '', title)
                
                if title and len(title) > 3:  # 确保标题长度合理
                    return title
        
        # 如果上述选择器都没有找到标题，尝试从meta标签中提取
        meta_title = soup.find('meta', {'property': 'og:title'}) or soup.find('meta', {'name': 'title'})
        if meta_title and meta_title.get('content'):
            title = meta_title.get('content').strip()
            # 确保标题是有效的UTF-8字符串
            try:
                title = title.encode('utf-8').decode('utf-8')
            except UnicodeError:
                try:
                    title = title.encode('latin1').decode('utf-8')
                except UnicodeError:
                    title = title.encode('utf-8', 'ignore').decode('utf-8')
        
            # 移除多余空白字符
            title = re.sub(r'\s+', ' ', title)
        
            # 移除标题中的特殊字符
            title = re.sub(r'[\r\n\t]', '', title)
        
            if title and len(title) > 3:  # 确保标题长度合理
                return title
        
        return None
    
    def _extract_keywords(self, soup, content):
        """
        提取关键词
        
        Args:
            soup: BeautifulSoup对象
            content: 正文内容
            
        Returns:
            list: 关键词列表
        """
        keywords = []
        try:
            # 尝试从meta标签中提取关键词
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and meta_keywords.get('content'):
                keywords_str = meta_keywords['content']
                # 确保关键词是列表格式
                if isinstance(keywords_str, str):
                    # 处理不同的分隔符
                    if ',' in keywords_str:
                        kw_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
                    elif '，' in keywords_str:
                        kw_list = [k.strip() for k in keywords_str.split('，') if k.strip()]
                    elif ' ' in keywords_str:
                        kw_list = [k.strip() for k in keywords_str.split() if k.strip()]
                    else:
                        kw_list = [keywords_str.strip()] if keywords_str.strip() else []
                
                keywords.extend(kw_list)
                logger.debug("从meta标签提取到关键词: %s", keywords)
        
            # 尝试从标签中获取关键词
            tag_selectors = [
                'div.keywords a',
                'div.tags a',
                'div.article-tags a',
                'div.tag a',
                'div.article-tag a',
                'div.topic-tag a'
            ]
        
            for selector in tag_selectors:
                tags = soup.select(selector)
                for tag in tags:
                    keyword = tag.get_text().strip()
                    if keyword and keyword not in keywords:
                        keywords.append(keyword)
        
            # 如果没有找到关键词，从标题中提取
            if not keywords:
                title = self._extract_title(soup)
                if title:
                    # 简单的关键词提取：分词并过滤停用词
                    words = re.findall(r'[\w\u4e00-\u9fa5]+', title)
                    # 过滤掉太短的词
                    keywords = [w for w in words if len(w) > 1]
                    logger.debug("从标题提取到关键词: %s", keywords)
        
            # 确保返回的是列表
            if not isinstance(keywords, list):
                keywords = [keywords] if keywords else []
        
            return keywords
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("提取关键词失败: %s", str(e))
            return []
    
    def _extract_images(self, soup):
        """
        提取图片URL
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            list: 图片URL列表
        """
        image_urls = []
        try:
            # 尝试多种可能的图片选择器
            content_selectors = [
                'div.article-content',
                'div.article',
                'div#artibody',
                'div.main-content',
                'div.content',
                'article'
            ]
            
            for selector in content_selectors:
                content_tag = soup.select_one(selector)
                if content_tag:
                    for img in content_tag.find_all('img'):
                        img_url = img.get('src')
                        if img_url and img_url.startswith('http') and img_url not in image_urls:
                            image_urls.append(img_url)
            
            return image_urls
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("提取图片URL失败: %s", str(e))
            return []
    
    def _extract_related_stocks(self, soup):
        """
        提取相关股票
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            list: 相关股票列表
        """
        related_stocks = []
        try:
            # 尝试多种可能的股票选择器
            stock_selectors = [
                'div.stock-info',
                'div.related-stocks',
                'div.stock-wrap'
            ]
            
            for selector in stock_selectors:
                stock_tags = soup.select(f'{selector} a')
                for tag in stock_tags:
                    stock_code = tag.get_text().strip()
                    # 检查是否是股票代码格式（数字或字母+数字）
                    if re.match(r'^[A-Za-z0-9]+$', stock_code) and stock_code not in related_stocks:
                        related_stocks.append(stock_code)
            
            return related_stocks
        except (AttributeError, TypeError, ValueError) as e:
            logger.error("提取相关股票失败: %s", str(e))
            return []
    
    def _is_news_in_date_range(self, news_data):
        """
        检查新闻是否在指定日期范围内
        
        Args:
            news_data (dict): 新闻数据
            
        Returns:
            bool: 是否在范围内
        """
        try:
            # 获取爬取开始日期
            days = getattr(self, 'days', 1)  # 默认为1天
            start_date = datetime.now() - timedelta(days=days)
            start_date = datetime(start_date.year, start_date.month, start_date.day)
            
            # 解析新闻日期
            news_date_str = news_data.get('pub_time', '')
            if not news_date_str:
                logger.debug("新闻没有日期信息，默认保留")
                return True  # 如果没有日期信息，默认保留
                
            # 尝试解析日期
            news_date = None
            try:
                # 尝试解析完整日期时间
                news_date = datetime.strptime(news_date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # 尝试解析日期部分
                    news_date = datetime.strptime(news_date_str.split(' ')[0], '%Y-%m-%d')
                except (ValueError, IndexError):
                    logger.warning("无法解析新闻日期: %s，默认保留", news_date_str)
                    return True  # 如果无法解析日期，默认保留
        
            # 比较日期
            if news_date and news_date >= start_date:
                return True
            else:
                logger.debug("新闻日期 %s 不在范围内（早于 %s）", news_date_str, start_date.strftime('%Y-%m-%d'))
                # 如果日期较早但仍在合理范围内，也保留
                if news_date and news_date >= start_date - timedelta(days=30):
                    logger.debug("新闻日期虽早但仍在合理范围内，保留")
                    return True
                return False
        except (ValueError, TypeError, IndexError, AttributeError) as e:
            logger.warning("解析新闻日期失败: %s, 错误: %s", news_data.get('pub_time', ''), str(e))
            return True  # 如果无法解析日期，默认保留

    def _save_news(self, news):
        """
        保存新闻
        
        Args:
            news (dict): 新闻数据
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 检查数据库路径是否存在
            if not self.db_path:
                logger.error("数据库路径未设置")
                return False
            
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建新闻表（如果不存在）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                url TEXT,
                title TEXT,
                content TEXT,
                pub_time TEXT,
                author TEXT,
                keywords TEXT,
                source TEXT,
                category TEXT,
                crawl_time TEXT
            )
            ''')
            
            # 检查新闻是否已存在
            cursor.execute('SELECT id FROM news WHERE id = ?', (news['id'],))
            if cursor.fetchone():
                logger.debug("新闻已存在: %s", news['title'])
                conn.close()
                return True
            
            # 确保所有文本字段使用UTF-8编码
            for key in ['title', 'content', 'author']:
                if key in news and news[key]:
                    # 确保是字符串类型
                    if not isinstance(news[key], str):
                        news[key] = str(news[key])
                    
                    # 确保使用UTF-8编码
                    try:
                        # 先尝试解码为UTF-8
                        news[key] = news[key].encode('utf-8', 'ignore').decode('utf-8')
                    except UnicodeError:
                        # 如果失败，尝试其他编码
                        try:
                            news[key] = news[key].encode('latin1').decode('utf-8')
                        except UnicodeError:
                            # 如果仍然失败，使用ASCII编码，忽略错误
                            news[key] = news[key].encode('ascii', 'ignore').decode('ascii')
        
            # 将关键词列表转换为字符串
            if 'keywords' in news and isinstance(news['keywords'], list):
                news['keywords'] = ','.join(news['keywords'])
            
            # 插入新闻
            cursor.execute('''
            INSERT INTO news (id, url, title, content, pub_time, author, keywords, source, category, crawl_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                news['id'],
                news['url'],
                news['title'],
                news['content'],
                news['pub_time'],
                news.get('author', ''),
                news.get('keywords', ''),
                news['source'],
                news.get('category', ''),
                news['crawl_time']
            ))
            
            # 提交事务
            conn.commit()
            conn.close()
            
            logger.info("成功保存新闻: %s", news['title'])
            print(f"成功保存新闻: {news['title']}")
            return True
        except (IOError, ValueError, AttributeError, TypeError) as e:
            logger.error("保存新闻失败: %s, 错误: %s", news.get('title', '未知标题'), str(e))
            print(f"保存新闻失败: {news.get('title', '未知标题')}, 错误: {str(e)}")
            return False

    def crawl_category(self, category, max_pages=3):
        """
        爬取指定分类的新闻
        
        Args:
            category (str): 分类名称
            max_pages (int): 最大爬取页数
        """
        logger.info("开始爬取分类: %s, URL: %s", category, self.CATEGORY_URLS[category])
        print(f"开始爬取分类: {category}, URL: {self.CATEGORY_URLS[category]}")
        
        try:
            # 检查分类是否存在
            if category not in self.CATEGORY_URLS:
                logger.error("分类不存在: %s", category)
                print(f"分类不存在: {category}")
                return
        
            # 获取分类页面内容
            html = self.fetch_page(self.CATEGORY_URLS[category])
            if not html:
                logger.error("获取分类页面内容失败: %s", category)
                print(f"获取分类页面内容失败: {category}")
                return
            
            # 解析页面内容
            try:
                soup = BeautifulSoup(html, 'html.parser')
                if not soup:
                    logger.error("创建BeautifulSoup对象失败: %s", category)
                    print(f"创建BeautifulSoup对象失败: {category}")
                    return
            except Exception as e:
                logger.error("解析HTML内容失败: %s, 错误: %s", category, str(e))
                print(f"解析HTML内容失败: {category}, 错误: {str(e)}")
                return
        
            # 提取新闻链接
            news_links = self._extract_news_links(soup)
            
            # 过滤链接，只保留有效链接
            valid_links = []
            for link in news_links:
                if self.validate_url(link):
                    valid_links.append(link)
            
            logger.info("从分类 %s 中提取到 %d 条新闻链接", category, len(valid_links))
            print(f"从分类 {category} 中提取到 {len(valid_links)} 条新闻链接")
            
            # 处理新闻链接
            if valid_links:
                self._process_news_links(valid_links, category)
            else:
                logger.warning("分类 %s 未找到有效新闻链接", category)
                print(f"分类 {category} 未找到有效新闻链接")
    
            logger.info("分类 %s 爬取完成", category)
            print(f"分类 {category} 爬取完成")
        except Exception as e:
            logger.error("爬取分类 %s 时发生异常: %s", category, str(e))
            logger.error("异常详情: %s", traceback.format_exc())
            print(f"爬取分类 {category} 时发生异常: {str(e)}")

    def _extract_news_links(self, soup):
        """
        从页面中提取新闻链接
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
        
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        
        # 确保soup是BeautifulSoup对象
        if not isinstance(soup, BeautifulSoup):
            logger.error("soup不是BeautifulSoup对象，而是 %s", type(soup))
            return news_links
        
        # 查找所有可能包含新闻链接的元素
        link_elements = soup.find_all('a')
        
        for link in link_elements:
            href = link.get('href')
            if href and self._is_news_link(href):
                # 确保链接是完整的URL
                if href.startswith('//'):
                    href = 'https:' + href
                elif not href.startswith(('http://', 'https://')):
                    continue
                
                # 添加到链接列表
                if href not in news_links:
                    news_links.append(href)
        
        # 打印提取到的链接数量，便于调试
        logger.debug("提取到 %d 条新闻链接", len(news_links))
        return news_links

    def _is_news_link(self, url):
        """
        判断URL是否为新闻链接
        
        Args:
            url (str): URL
        
        Returns:
            bool: 是否为新闻链接
        """
        # 新浪财经新闻URL特征
        news_patterns = [
            'finance.sina.com.cn/[a-z]/detail',
            'finance.sina.com.cn/[a-z]/[0-9]{4}-[0-9]{2}-[0-9]{2}',
            'finance.sina.com.cn/stock',
            'finance.sina.com.cn/money',
            'finance.sina.com.cn/china',
            'finance.sina.com.cn/world',
            'finance.sina.com.cn/roll',
            'finance.sina.com.cn/tech',
            'tech.sina.com.cn',
            'sina.com.cn/[a-z]/[0-9]{4}-[0-9]{2}-[0-9]{2}'
        ]
        
        # 检查URL是否匹配新闻模式
        for pattern in news_patterns:
            if re.search(pattern, url):
                return True
            
        return False

    def _save_news(self, news):
        """
        保存新闻
        
        Args:
            news (dict): 新闻数据
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 检查数据库路径是否存在
            if not self.db_path:
                logger.error("数据库路径未设置")
                return False
            
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建新闻表（如果不存在）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                url TEXT,
                title TEXT,
                content TEXT,
                pub_time TEXT,
                author TEXT,
                keywords TEXT,
                source TEXT,
                category TEXT,
                crawl_time TEXT
            )
            ''')
            
            # 检查新闻是否已存在
            cursor.execute('SELECT id FROM news WHERE id = ?', (news['id'],))
            if cursor.fetchone():
                logger.debug("新闻已存在: %s", news['title'])
                conn.close()
                return True
            
            # 确保所有文本字段使用UTF-8编码
            for key in ['title', 'content', 'author']:
                if key in news and news[key]:
                    # 确保是字符串类型
                    if not isinstance(news[key], str):
                        news[key] = str(news[key])
                    
                    # 确保使用UTF-8编码
                    try:
                        # 先尝试解码为UTF-8
                        news[key] = news[key].encode('utf-8', 'ignore').decode('utf-8')
                    except UnicodeError:
                        # 如果失败，尝试其他编码
                        try:
                            news[key] = news[key].encode('latin1').decode('utf-8')
                        except UnicodeError:
                            # 如果仍然失败，使用ASCII编码，忽略错误
                            news[key] = news[key].encode('ascii', 'ignore').decode('ascii')
        
            # 将关键词列表转换为字符串
            if 'keywords' in news and isinstance(news['keywords'], list):
                news['keywords'] = ','.join(news['keywords'])
            
            # 插入新闻
            cursor.execute('''
            INSERT INTO news (id, url, title, content, pub_time, author, keywords, source, category, crawl_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                news['id'],
                news['url'],
                news['title'],
                news['content'],
                news['pub_time'],
                news.get('author', ''),
                news.get('keywords', ''),
                news['source'],
                news.get('category', ''),
                news['crawl_time']
            ))
            
            # 提交事务
            conn.commit()
            conn.close()
            
            logger.info("成功保存新闻: %s", news['title'])
            return True
        except (IOError, ValueError, AttributeError, TypeError) as e:
            logger.error("保存新闻失败: %s, 错误: %s", news.get('title', '未知标题'), str(e))
            return False
