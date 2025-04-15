#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 凤凰财经爬虫
"""

import os
import re
import time
import random
import urllib.parse
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
import hashlib
import json
import logging
import chardet

# 修复导入路径
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.db_manager import DatabaseManager
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html_content, extract_keywords, decode_html_entities, decode_unicode_escape, decode_url_encoded
from app.crawlers.base import BaseCrawler
from app.utils.ad_filter import AdFilter  # 导入广告过滤器模块
from app.utils.image_detector import ImageDetector  # 导入图像识别模块

# 确保日志目录存在
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs', '凤凰财经')
os.makedirs(log_dir, exist_ok=True)

# 使用专门的爬虫日志记录器，并配置文件输出
today = datetime.now().strftime('%Y%m%d')
log_file = os.path.join(log_dir, f"凤凰财经_{today}.log")

# 创建自定义的日志记录器
logger = logging.getLogger('ifeng_crawler')
logger.setLevel(logging.INFO)

# 添加控制台输出
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s'))
logger.addHandler(console_handler)

# 添加文件输出
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s'))
logger.addHandler(file_handler)

# 避免日志重复
logger.propagate = False

class IfengCrawler(BaseCrawler):
    """凤凰财经爬虫，用于爬取凤凰财经的财经新闻"""
    
    # 来源名称
    source = "凤凰财经"
    
    # 新闻分类URL
    CATEGORY_URLS = {
        '财经': 'https://finance.ifeng.com/',
        '股票': 'https://finance.ifeng.com/stock/',
        '绿色发展': 'https://finance.ifeng.com/greenfinance/',
        '中国深度财经': 'https://finance.ifeng.com/deepfinance/',
        '上市公司': 'https://finance.ifeng.com/listedcompany/',
        '银行财眼': 'https://finance.ifeng.com/bankingeye/',
        '国际财经': 'https://finance.ifeng.com/world/',
        'IPO观察哨': 'https://finance.ifeng.com/ipo/',
    }
    
    # API URL模板 - 凤凰财经的API接口
    API_URL_TEMPLATE = "https://api.3g.ifeng.com/ipadtestdoc?gv=5.8.5&os=ios&uid={uid}&aid={aid}&id={id}&pageSize={page_size}"
    
    # 内容选择器 - 更新以适应各种网页结构
    CONTENT_SELECTOR = 'div.main_content, div.text_area, div.article-main, div.text-3w2e3DBc, div.main-content-section, div.js-video-content, div.content, div.article_content, article.article-main-content, div.detailArticle-content, div#artical_real, div.yc-artical, div.art_content, div.article-cont, div.news-content, div.news_txt, div.c-article-content, div#main_content, div.hqy-ArticleInfo-article, div.article-main-inner, div.article__content, div.c-article-body'
    
    # 时间选择器
    TIME_SELECTOR = 'span.ss01, span.date, div.time, p.time, span.time, span.date-source, span.ss01, time.time'
    
    # 作者选择器
    AUTHOR_SELECTOR = 'span.ss03, span.source, div.source, p.source, span.author, span.ss03, span.source-name'
    
    # 标题选择器
    TITLE_SELECTOR = 'h1.title, h1.headline-title, div.headline-title, h1.news-title-h1, h1.yc-title, h1.c-article-title, h1.news_title'
    
    # 用户代理列表 - 更新为最新的浏览器User-Agent
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0',
    ]
    
    # 新凤凰财经API端点
    NEW_API_ENDPOINT = "https://finance.ifeng.com/mapi/getfeeds"
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化凤凰财经爬虫
        
        Args:
            db_manager: 数据库管理器
            db_path: 数据库路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用源数据库
        """
        super().__init__(db_manager, db_path, use_proxy, use_source_db, **kwargs)
        self.ad_filter = AdFilter(source_name="凤凰财经")  # 初始化广告过滤器，提供source_name参数
        
        # 初始化图像识别模块
        self.image_detector = ImageDetector(cache_dir='./image_cache')
        
        # 设置db属性，用于数据库操作
        self.db = None
        
        # 添加编码修复功能的标志，用于调试
        self.encoding_fix_enabled = True
        logger.info("已启用编码修复功能，自动处理中文乱码问题")
        
        # 确保SQLiteManager已正确导入
        try:
            from app.db.sqlite_manager import SQLiteManager
            
            # 如果提供了db_manager并且不是SQLiteManager类型，创建SQLiteManager
            if db_manager and not isinstance(db_manager, SQLiteManager):
                if hasattr(db_manager, 'db_path'):
                    self.sqlite_manager = SQLiteManager(db_manager.db_path)
                    self.db = self.sqlite_manager
                else:
                    # 使用传入的db_path或默认路径
                    self.sqlite_manager = SQLiteManager(db_path or self.db_path)
                    self.db = self.sqlite_manager
            elif not db_manager:
                # 如果没有提供db_manager，创建SQLiteManager
                self.sqlite_manager = SQLiteManager(db_path or self.db_path)
                self.db = self.sqlite_manager
            else:
                # 否则使用提供的db_manager
                self.sqlite_manager = db_manager
                self.db = db_manager
        except ImportError as e:
            logger.error(f"无法导入SQLiteManager: {str(e)}")
            self.sqlite_manager = None
            self.db = None
        
        logger.info("凤凰财经爬虫初始化完成，数据库路径: %s", self.db_path)
    
    def crawl(self, days=1, max_news=10):
        """
        爬取凤凰财经新闻
        
        Args:
            days: 爬取的天数范围，默认为1天
            max_news: 最大爬取新闻数量，默认为10条
            
        Returns:
            list: 爬取的新闻数据列表
        """
        # 存储爬取的新闻数据
        news_data = []
        
        # 计算起始日期
        start_date = datetime.now() - timedelta(days=days)
        
        logger.info("开始爬取凤凰财经新闻，爬取天数: %d", days)
        
        # 确保数据库和表结构正确
        self._ensure_db_ready()
        
        try:
            # 先尝试从首页获取新闻
            logger.info("尝试从首页获取新闻")
            # 随机休眠，避免请求过快
            sleep_time = random.uniform(1, 2)
            logger.debug("随机休眠 %.2f 秒", sleep_time)
            time.sleep(sleep_time)
            
            # 获取首页新闻链接
            home_url = "https://finance.ifeng.com/"
            home_links = self.get_news_links(home_url, "首页")
            
            logger.info("从首页提取到新闻链接数量: %d", len(home_links) if home_links else 0)
            
            # 处理首页新闻
            for link in home_links:
                # 检查是否达到最大新闻数量
                if len(news_data) >= max_news:
                    logger.info("已达到最大新闻数量 %d 条，停止爬取", max_news)
                    break
                
                try:
                    # 随机休眠，避免请求过快
                    sleep_time = random.uniform(1, 5)
                    logger.debug("随机休眠 %.2f 秒", sleep_time)
                    time.sleep(sleep_time)
                    
                    # 获取新闻详情
                    news = self.get_news_detail(link, "首页")
                    
                    if not news:
                        logger.warning("无法获取新闻详情：%s", link)
                        continue
                    
                    # 检查新闻日期是否在指定范围内
                    news_date = datetime.strptime(news['pub_time'], '%Y-%m-%d %H:%M:%S')
                    if news_date < start_date:
                        logger.info("新闻日期 %s 早于起始日期 %s，跳过", news['pub_time'], start_date.strftime('%Y-%m-%d %H:%M:%S'))
                        continue
                    
                    # 保存新闻到数据库
                    self._save_news_to_db(news)
                    
                    # 添加到新闻数据列表
                    news_data.append(news)
                    
                    # 记录新闻信息
                    logger.info("成功爬取新闻：%s", news['title'])
                    
                except Exception as e:
                    logger.error("处理新闻链接出错：%s，错误：%s", link, str(e))
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
        except Exception as e:
            logger.error("从首页提取新闻链接失败: %s", str(e))
            import traceback
            logger.error(traceback.format_exc())
        
        # 遍历所有分类
        for category, url in self.CATEGORY_URLS.items():
            try:
                # 检查是否达到最大新闻数量
                if len(news_data) >= max_news:
                    logger.info("已达到最大新闻数量 %d 条，停止爬取", max_news)
                    break
                
                # 记录当前分类爬取信息
                logger.info("开始爬取分类: %s, URL: %s", category, url)
                
                # 随机休眠，避免请求过快
                sleep_time = random.uniform(1, 5)
                logger.debug("随机休眠 %.2f 秒", sleep_time)
                time.sleep(sleep_time)
                
                # 获取分类页面的新闻链接
                news_links = self.get_news_links(url, category)
                
                if not news_links:
                    logger.warning("未找到分类 %s 的新闻链接", category)
                    continue
                
                logger.info("分类 '%s' 找到 %d 个潜在新闻项", category, len(news_links))
                
                # 随机休眠，避免请求过快
                sleep_time = random.uniform(1, 5)
                logger.debug("随机休眠 %.2f 秒", sleep_time)
                time.sleep(sleep_time)
                
                # 遍历新闻链接
                for link in news_links:
                    # 检查是否达到最大新闻数量
                    if len(news_data) >= max_news:
                        logger.info("已达到最大新闻数量 %d 条，停止爬取", max_news)
                        break
                    
                    try:
                        # 随机休眠，避免请求过快
                        sleep_time = random.uniform(1, 3)
                        logger.debug("随机休眠 %.2f 秒", sleep_time)
                        time.sleep(sleep_time)
                        
                        # 获取新闻详情
                        news = self.get_news_detail(link, category)
                        
                        if not news:
                            logger.warning("无法获取新闻详情：%s", link)
                            continue
                        
                        # 检查新闻日期是否在指定范围内
                        news_date = datetime.strptime(news['pub_time'], '%Y-%m-%d %H:%M:%S')
                        if news_date < start_date:
                            logger.info("新闻日期 %s 早于起始日期 %s，跳过", news['pub_time'], start_date.strftime('%Y-%m-%d %H:%M:%S'))
                            continue
                        
                        # 保存新闻到数据库
                        self._save_news_to_db(news)
                        
                        # 添加到新闻数据列表
                        news_data.append(news)
                        
                        # 记录新闻信息
                        logger.info("成功爬取新闻：%s", news['title'])
                        
                    except Exception as e:
                        logger.error("处理新闻链接出错：%s，错误：%s", link, str(e))
                        import traceback
                        logger.error(traceback.format_exc())
                        continue
                
            except Exception as e:
                logger.error("从分类页面提取新闻链接失败: %s, 错误: %s", category, str(e))
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        # 记录爬取结束信息
        logger.info("凤凰财经新闻爬取完成，共爬取 %d 条新闻", len(news_data))
        
        return news_data
    
    def _ensure_db_ready(self):
        """
        确保数据库和表结构已经准备好
        """
        try:
            # 检查sqlite_manager是否可用
            if hasattr(self, 'sqlite_manager') and self.sqlite_manager:
                if hasattr(self.sqlite_manager, 'ensure_source_table_exists'):
                    self.sqlite_manager.ensure_source_table_exists("凤凰财经")
                    logger.info("已确保数据库表结构正确")
                    return True
            
            # 检查db_manager是否可用
            if hasattr(self, 'db_manager') and self.db_manager:
                if hasattr(self.db_manager, 'ensure_source_table_exists'):
                    self.db_manager.ensure_source_table_exists("凤凰财经")
                    logger.info("已确保数据库表结构正确")
                    return True
                    
            # 检查db是否可用
            if hasattr(self, 'db') and self.db:
                if hasattr(self.db, 'ensure_source_table_exists'):
                    self.db.ensure_source_table_exists("凤凰财经")
                    logger.info("已确保数据库表结构正确")
                    return True
                    
            # 如果以上都不可用，尝试直接使用sqlite3
            import sqlite3
            if hasattr(self, 'db_path') and self.db_path:
                # 确保目录存在
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 创建新闻表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS news (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    content_html TEXT,
                    pub_time TEXT,
                    author TEXT,
                    source TEXT,
                    url TEXT UNIQUE,
                    keywords TEXT,
                    images TEXT,
                    related_stocks TEXT,
                    sentiment TEXT,
                    classification TEXT,
                    category TEXT,
                    crawl_time TEXT
                )
                ''')
                
                # 提交更改
                conn.commit()
                conn.close()
                
                logger.info("已使用sqlite3直接创建数据库表")
                return True
                
            logger.warning("无法确保数据库表结构，可能无法保存数据")
            return False
            
        except Exception as e:
            logger.error(f"确保数据库准备时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _save_news_to_db(self, news):
        """
        将新闻保存到数据库
        
        Args:
            news: 新闻数据字典
        
        Returns:
            bool: 是否成功保存
        """
        try:
            # 添加爬取时间
            if 'crawl_time' not in news:
                news['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
            # 1. 尝试使用sqlite_manager
            if hasattr(self, 'sqlite_manager') and self.sqlite_manager:
                if hasattr(self.sqlite_manager, 'save_news'):
                    self.sqlite_manager.save_news(news)
                    logger.info(f"使用sqlite_manager保存新闻: {news['title']}")
                    return True
            
            # 2. 尝试使用db_manager
            if hasattr(self, 'db_manager') and self.db_manager:
                if hasattr(self.db_manager, 'save_news'):
                    self.db_manager.save_news(news)
                    logger.info(f"使用db_manager保存新闻: {news['title']}")
                    return True
            
            # 3. 尝试使用db
            if hasattr(self, 'db') and self.db:
                if hasattr(self.db, 'save_news'):
                    self.db.save_news(news)
                    logger.info(f"使用db保存新闻: {news['title']}")
                    return True
            
            # 4. 尝试直接使用sqlite3
            import sqlite3
            if hasattr(self, 'db_path') and self.db_path:
                # 尝试使用sqlite3直接保存
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 准备插入语句
                insert_sql = '''
                INSERT OR REPLACE INTO news (
                    id, title, content, pub_time, author, source, url, 
                    keywords, images, related_stocks, category, crawl_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                # 准备数据
                data = (
                    news['id'],
                    news['title'],
                    news['content'],
                    news['pub_time'],
                    news['author'],
                    news['source'],
                    news['url'],
                    news.get('keywords', ''),
                    news.get('images', ''),
                    news.get('related_stocks', ''),
                    news.get('category', '未分类'),
                    news.get('crawl_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                
                # 执行插入
                cursor.execute(insert_sql, data)
                
                # 提交并关闭
                conn.commit()
                conn.close()
                
                logger.info(f"使用sqlite3直接保存新闻: {news['title']}")
                return True
                
            logger.warning(f"无法保存新闻到数据库: {news['title']}")
            return False
            
        except Exception as e:
            logger.error(f"保存新闻到数据库时出错: {str(e)}, 标题: {news.get('title', 'Unknown')}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 发生错误时尝试回退到基本sqlite3保存
            try:
                if hasattr(self, 'db_path') and self.db_path:
                    # 尝试使用更基础的方式保存
                    import sqlite3
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    # 简化的插入，只保存最基础的字段
                    basic_sql = '''
                    INSERT OR REPLACE INTO news (id, title, content, source, url, crawl_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                    '''
                    
                    basic_data = (
                        news['id'],
                        news['title'],
                        news['content'],
                        news['source'],
                        news['url'],
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    
                    cursor.execute(basic_sql, basic_data)
                    conn.commit()
                    conn.close()
                    
                    logger.info(f"使用基础sqlite3方法保存新闻: {news['title']}")
                    return True
            except Exception as fallback_e:
                logger.error(f"基础sqlite3保存也失败: {str(fallback_e)}")
                
            return False
    
    def get_news_links(self, url, category):
        """
        获取分类页面的新闻链接
        
        Args:
            url (str): 分类页面URL
            category (str): 分类名称
            
        Returns:
            list: 新闻链接列表
        """
        try:
            # 请求分类页面
            headers = {'User-Agent': random.choice(self.USER_AGENTS)}
            
            # 创建新会话，避免连接被重置问题
            session = requests.Session()
            
            # 禁用SSL验证，避免某些证书问题
            try:
                from requests.packages.urllib3.exceptions import InsecureRequestWarning
                requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
            except ImportError:
                pass

            try:
                # 使用新创建的session对象，而不是self.session
                response = session.get(
                    url, 
                    headers=headers, 
                    timeout=15,
                    verify=False  # 禁用SSL验证 
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"请求分类页面失败: {str(e)}, URL: {url}")
                # 重试一次
                time.sleep(random.uniform(2, 5))
                try:
                    # 使用新创建的session对象进行重试
                    response = session.get(
                        url,
                        headers=headers,
                        timeout=20,  # 增加超时时间
                        verify=False
                    )
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    logger.error(f"第二次请求分类页面失败: {str(e)}, URL: {url}")
                    return []
            
            # 检测并处理编码
            if hasattr(self, '_handle_encoding'):
                html_content = self._handle_encoding(response)
            else:
                # 尝试自动检测编码
                encoding = self.detect_encoding(response.content) if hasattr(self, 'detect_encoding') else 'utf-8'
                html_content = response.content.decode(encoding, errors='ignore')
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取新闻链接
            news_links = []
            
            # 1. 从普通链接获取
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                # 确保链接是完整的URL
                if href.startswith('//'):
                    href = 'https:' + href
                elif not href.startswith('http'):
                    # 相对路径转绝对路径
                    if href.startswith('/'):
                        base_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(url))
                        href = base_url + href
                    else:
                        continue  # 跳过不完整的链接
                
                # 过滤非新闻链接
                if self.is_valid_news_url(href):
                    news_links.append(href)
            
            # 2. 特别处理首页上的特色栏目（如"操盘热点"、"IPO观察哨"等）
            hot_sections = [
                'Trading Hotspots', 'Hot List', 'Financial News', 
                'IPO观察哨', '操盘热点', '热榜', '财经要闻', '全球快报'
            ]
            
            for section in hot_sections:
                # 查找可能表示栏目的元素
                section_headers = soup.find_all(['h2', 'h3', 'div', 'span', 'a'], 
                                               string=lambda s: s and section in s)
                
                for header in section_headers:
                    # 查找栏目的父容器
                    container = header
                    for _ in range(3):  # 向上查找最多3层
                        if container.parent:
                            container = container.parent
                        else:
                            break
                    
                    # 从容器中提取链接
                    if container:
                        for link in container.find_all('a', href=True):
                            href = link['href']
                            
                            # 格式化URL
                            if href.startswith('//'):
                                href = 'https:' + href
                            elif not href.startswith('http'):
                                if href.startswith('/'):
                                    base_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(url))
                                    href = base_url + href
                                else:
                                    continue
                            
                            if self.is_valid_news_url(href):
                                news_links.append(href)
            
            # 3. 爬取"中国深度财经"、"IPO观察哨"等特色栏目
            if category in ['中国深度财经', 'IPO观察哨', '上市公司', '绿色发展']:
                # 查找文章卡片和列表项
                article_cards = soup.find_all(['div', 'li'], class_=lambda c: c and any(
                    term in str(c).lower() for term in ['card', 'article', 'news-item', 'list-item']))
                
                for card in article_cards:
                    links = card.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        
                        # 格式化URL
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif not href.startswith('http'):
                            if href.startswith('/'):
                                base_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(url))
                                href = base_url + href
                            else:
                                continue
                        
                        if self.is_valid_news_url(href):
                            news_links.append(href)
            
            # 去重
            news_links = list(set(news_links))
            
            logger.info("分类 %s 找到 %d 条新闻链接", category, len(news_links))
            return news_links
        except requests.exceptions.RequestException as e:
            logger.error("请求分类页面出错：%s，错误：%s", url, str(e))
            return []
        except Exception as e:
            logger.error("处理分类页面出错：%s，错误：%s", url, str(e))
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def detect_encoding(self, content):
        """
        检测内容的编码格式
        
        Args:
            content: 二进制内容
            
        Returns:
            str: 检测到的编码
        """
        try:
            # 使用chardet检测编码
            result = chardet.detect(content)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            logger.debug("检测到编码: %s, 置信度: %.2f", encoding, confidence)
            
            # 如果置信度较低，使用常见中文编码尝试解码
            if confidence < 0.7:
                encodings = ['utf-8', 'gbk', 'gb18030', 'big5']
                for enc in encodings:
                    try:
                        content.decode(enc)
                        logger.info("低置信度情况下成功使用 %s 解码", enc)
                        return enc
                    except UnicodeDecodeError:
                        continue
            
            return encoding or 'utf-8'
        except Exception as e:
            logger.warning("编码检测失败: %s", str(e))
            return 'utf-8'
    
    def _handle_encoding(self, response):
        """
        处理响应的编码问题
        
        Args:
            response: 响应对象
            
        Returns:
            str: 处理后的文本内容
        """
        try:
            # 检查是否是ISO-8859-1编码（通常是误判）
            if response.encoding == 'ISO-8859-1' or response.encoding is None:
                # 使用chardet检测实际编码
                detected_encoding = self.detect_encoding(response.content)
                
                # 尝试使用检测到的编码解码
                try:
                    content = response.content.decode(detected_encoding)
                    logger.debug("使用检测到的编码 %s 成功解码", detected_encoding)
                    return content
                except UnicodeDecodeError:
                    # 检测失败，尝试常用中文编码
                    encodings = ['utf-8', 'gbk', 'gb18030']
                    for enc in encodings:
                        try:
                            content = response.content.decode(enc)
                            logger.debug("成功使用 %s 解码", enc)
                            return content
                        except UnicodeDecodeError:
                            continue
                    
                    # 所有尝试都失败，使用errors='ignore'强制解码
                    logger.warning("所有编码尝试失败，使用ignore模式强制解码")
                    return response.content.decode('utf-8', errors='ignore')
            else:
                # 使用响应的原始编码
                return response.text
        except Exception as e:
            logger.error("处理编码时出错: %s", str(e))
            # 发生错误时，使用ignore模式强制解码
            return response.content.decode('utf-8', errors='ignore')
    
    def clean_text(self, text):
        """
        清理文本，处理特殊字符和乱码
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        # 确保输入是字符串
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return ""
        
        # 处理潜在的乱码
        try:
            # 如果文本看起来是乱码，尝试检测并修复
            if any(ord(c) > 127 for c in text[:20]) and any(c in text[:30] for c in 'äåæçèéêëìíîï'):
                # 可能是latin1误编码的utf-8
                try:
                    text = text.encode('latin1').decode('utf-8')
                except UnicodeError:
                    pass
        except Exception:
            pass
        
        # 应用多种解码处理
        text = decode_html_entities(text)
        text = decode_unicode_escape(text)
        text = decode_url_encoded(text)
        
        # 替换常见问题字符
        text = text.replace('\xa0', ' ')  # 替换不间断空格
        text = text.replace('\u3000', ' ')  # 替换全角空格
        
        # 处理多余空白
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    # 重写fetch_page方法，加强编码处理
    def fetch_page(self, url, params=None, headers=None, max_retries=3, timeout=15):
        """
        获取页面内容并处理编码
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            
        Returns:
            str: 页面内容或None
        """
        if not headers:
            headers = {
                'User-Agent': random.choice(self.USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://finance.ifeng.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
        
        for attempt in range(max_retries):
            try:
                session = requests.Session()
                response = session.get(url, params=params, headers=headers, timeout=timeout)
                response.raise_for_status()
                
                # 处理编码问题
                content = self._handle_encoding(response)
                
                # 应用文本清理
                content = self.clean_text(content)
                
                logger.debug("成功获取页面内容，URL: %s", url)
                return content
                
            except requests.exceptions.RequestException as e:
                logger.warning("请求异常 (尝试 %d/%d): %s, URL: %s", 
                              attempt + 1, max_retries, str(e), url)
                time.sleep(2 * (attempt + 1))  # 指数退避
        
        logger.error("获取页面内容失败，已达到最大重试次数: %d, URL: %s", max_retries, url)
        return None
    
    def get_news_detail(self, url, category=None, retry=0):
        """
        获取新闻详情
        
        Args:
            url: 新闻URL
            category: 分类名称（可选）
            retry: 重试次数
            
        Returns:
            dict: 新闻详情
        """
        if retry > 3:
            logger.error(f"获取新闻详情失败，已重试{retry}次，放弃: {url}")
            return None

        try:
            logger.info(f"获取新闻详情: {url}, 分类: {category or '未知'}")
            
            # 更健壮的请求处理
            try:
                # 禁用SSL验证，避免某些证书问题
                from requests.packages.urllib3.exceptions import InsecureRequestWarning
                requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
                
                # 创建自定义请求头
                headers = {
                    'User-Agent': random.choice(self.USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Referer': 'https://finance.ifeng.com/',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
                
                # 创建新会话避免之前的连接问题
                session = requests.Session()
                response = session.get(
                    url, 
                    headers=headers, 
                    timeout=30,
                    verify=False,  # 禁用SSL验证
                    stream=False   # 不使用流式传输
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求异常 (尝试 {retry+1}/3): {str(e)}, URL: {url}")
                if retry < 3:
                    # 指数退避策略
                    sleep_time = (2 ** retry) + random.uniform(0, 1)
                    logger.info(f"等待 {sleep_time:.2f} 秒后重试...")
                    time.sleep(sleep_time)
                    return self.get_news_detail(url, category, retry + 1)
                return None
            
            # 使用编码修复功能处理响应
            if hasattr(self, 'encoding_fix_enabled') and self.encoding_fix_enabled:
                html = self._handle_encoding(response)
            else:
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 获取标题 - 扩展标题获取方法
            title_elem = None
            for selector in ['.news-title', '.hl', 'h1', 'title', 'h1.title', 'h1.headline-title', 'h1.news-title-h1']:
                title_elem = soup.select_one(selector)
                if title_elem:
                    break
                
            title = title_elem.text.strip() if title_elem else ""
            
            # 移除标题中的网站名称（如"_凤凰网"）
            title = re.sub(r'_凤凰网$', '', title)
            title = re.sub(r'_.*?网$', '', title)
            title = re.sub(r'\s*\|\s*IPO观察哨$', '', title)
            
            # 使用编码修复功能处理标题
            if hasattr(self, 'encoding_fix_enabled') and self.encoding_fix_enabled and title:
                try:
                    title = self.clean_text(title)
                    logger.info(f"标题编码修复成功: {title}")
                except Exception as e:
                    logger.error(f"标题编码修复失败: {str(e)}")
            
            # 获取内容 - 使用更灵活的内容获取策略
            content_elem = None
            
            # 1. 首先尝试使用选择器列表
            selectors = [
                '.main_content', '.article', '.article-main', '.text-3w2e3DBc', 
                '.main-content-section', '.js-video-content', '.content', 
                '.article_content', 'article.article-main-content', 
                '.detailArticle-content', '#artical_real', '.yc-artical', 
                '.art_content', '.article-cont', '.news-content', '.news_txt', 
                '.c-article-content', '#main_content', '.hqy-ArticleInfo-article',
                '.article-main-inner', '.article__content', '.c-article-body'
            ]
            for selector in selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    logger.info(f"使用选择器 '{selector}' 找到内容")
                    break
            
            # 2. 如果选择器方法失败，尝试查找包含大量文本的div
            if not content_elem:
                logger.info("使用备用策略查找内容元素")
                # 查找所有div元素
                divs = soup.find_all('div')
                # 按文本长度排序
                divs_by_length = sorted(divs, key=lambda div: len(div.get_text()), reverse=True)
                # 如果有足够长的div，可能是内容区
                for div in divs_by_length[:5]:  # 检查前5个最长的div
                    text = div.get_text().strip()
                    if len(text) > 200 and not div.find_parent('script'):  # 排除脚本内的div
                        content_elem = div
                        logger.info(f"使用文本长度策略找到可能的内容元素，长度: {len(text)}")
                        break
            
            # 3. 尝试根据JavaScript数据对象提取内容（新版凤凰网常用这种方式）
            if not content_elem:
                logger.info("尝试从JS数据中提取内容")
                script_tags = soup.find_all('script')
                for script in script_tags:
                    script_text = script.string
                    if script_text and ('var article_data' in script_text or '"content":' in script_text):
                        # 查找JSON结构的内容字段
                        content_match = re.search(r'"content"\s*:\s*"(.+?[^\\])"', script_text, re.DOTALL)
                        if content_match:
                            content_json = content_match.group(1)
                            # 处理转义字符
                            content_json = content_json.replace('\\"', '"').replace('\\\\', '\\')
                            content_json = decode_unicode_escape(content_json)
                            # 创建一个临时的内容元素
                            content_elem = BeautifulSoup(f"<div>{content_json}</div>", 'html.parser')
                            logger.info("从JS数据中成功提取内容")
                            break
            
            # 如果仍未找到内容元素，保存HTML并返回失败
            if not content_elem:
                logger.error(f"无法找到内容元素，URL: {url}")
                # 尝试保存获取的HTML以便调试
                debug_file = f"debug_html_{datetime.now().strftime('%Y%m%d%H%M%S')}.html"
                try:
                    with open(debug_file, "w", encoding="utf-8") as f:
                        f.write(html)
                    logger.info(f"已保存HTML到文件: {debug_file}")
                except Exception as save_e:
                    logger.error(f"保存HTML失败: {str(save_e)}")
                return None
            
            # 剔除不需要的元素
            for selector in ['.textimg', 'table', 'style', '.ad', '.advertisement', 'script', '.share', '.tool', '.relate', '.recommend']:
                for elem in content_elem.select(selector):
                    elem.decompose()
            
            # 获取文本内容
            content = content_elem.get_text().strip()
            
            # 移除特定的广告或无关文本
            ad_patterns = [
                r'凤凰网财经讯.*?$',
                r'更多财经资讯.*?$',
                r'更多.*?资讯，请下载.*?$',
                r'APP内打开.*?$',
                r'原标题：.*?$',
                r'【声明】.*?$',
                r'【免责声明】.*?$'
            ]
            for pattern in ad_patterns:
                content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
            # 清理多余空白行
            content = re.sub(r'\n\s*\n', '\n\n', content)
            
            # 使用编码修复功能处理内容
            if hasattr(self, 'encoding_fix_enabled') and self.encoding_fix_enabled and content:
                try:
                    content = self.clean_text(content)
                    logger.info(f"内容编码修复成功: {content[:30]}...")
                except Exception as e:
                    logger.error(f"内容编码修复失败: {str(e)}")
            
            # 提取图片
            images = []
            img_elems = content_elem.select('img')
            for img in img_elems:
                src = img.get('src', '')
                if not src:
                    # 尝试从data-lazyload属性获取
                    src = img.get('data-lazyload', '')
                if not src:
                    # 尝试从data-original属性获取
                    src = img.get('data-original', '')
                    
                if src and src.startswith('http'):
                    images.append(src)
                elif src and src.startswith('//'):
                    images.append('https:' + src)
            
            # 如果从HTML中找不到图片，尝试从元数据中获取
            if not images:
                og_image = soup.select_one('meta[property="og:image"]')
                if og_image and og_image.get('content'):
                    images.append(og_image.get('content'))
            
            # 提取关键词
            keywords = []
            keywords_elem = soup.select_one('meta[name="keywords"]')
            if keywords_elem:
                keywords_content = keywords_elem.get('content', '')
                if keywords_content:
                    keywords = [k.strip() for k in keywords_content.split(',') if k.strip()]
                    
                    # 使用编码修复功能处理关键词
                    if hasattr(self, 'encoding_fix_enabled') and self.encoding_fix_enabled:
                        try:
                            keywords = [self.clean_text(k) for k in keywords]
                        except Exception as e:
                            logger.error(f"关键词编码修复失败: {str(e)}")
            
            # 提取发布时间
            pub_time = self.extract_pub_time(soup)
            
            # 提取作者
            author = self.extract_author(soup)
            
            # 生成新闻ID
            news_id = self.generate_news_id(url, title)
            
            # 构建结果
            result = {
                'id': news_id,
                'title': title,
                'content': content,
                'pub_time': pub_time,
                'author': author,
                'source': self.source,
                'url': url,
                'category': category or '未分类',
                'keywords': ','.join(keywords) if keywords else '',
                'images': ','.join(images) if images else '',
                'related_stocks': ''
            }
            
            logger.info(f"成功获取新闻详情：{title}")
            return result
        except Exception as e:
            logger.error(f"获取新闻详情异常: {str(e)}, URL: {url}")
            import traceback
            logger.error(traceback.format_exc())
            if retry < 3:
                # 指数退避策略
                sleep_time = (2 ** retry) + random.uniform(0, 1)
                logger.info(f"等待 {sleep_time:.2f} 秒后重试...")
                time.sleep(sleep_time)
                return self.get_news_detail(url, category, retry + 1)
            return None
    
    def extract_pub_time(self, soup):
        """
        提取发布时间
        
        Args:
            soup (BeautifulSoup): 解析后的HTML
            
        Returns:
            str: 发布时间
        """
        try:
            time_tag = soup.select_one(self.TIME_SELECTOR)
            if not time_tag:
                return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            time_text = time_tag.text.strip()
            
            # 使用正则表达式提取时间
            time_pattern = r'(\d{4})年(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})'
            match = re.search(time_pattern, time_text)
            if match:
                year, month, day, hour, minute = match.groups()
                return f"{year}-{month}-{day} {hour}:{minute}:00"
            
            # 如果没有匹配到时间，使用当前时间
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning("提取发布时间失败：%s", str(e))
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def extract_author(self, soup):
        """
        提取作者
        
        Args:
            soup (BeautifulSoup): 解析后的HTML
            
        Returns:
            str: 作者
        """
        try:
            author_tag = soup.select_one(self.AUTHOR_SELECTOR)
            if not author_tag:
                return "凤凰财经"
            
            author_text = author_tag.text.strip()
            
            # 使用正则表达式提取来源
            source_pattern = r'来源：(.*)'
            match = re.search(source_pattern, author_text)
            if match:
                return match.group(1).strip()
            
            return author_text or "凤凰财经"
        except Exception as e:
            logger.warning("提取作者失败：%s", str(e))
            return "凤凰财经"
    
    def extract_related_stocks(self, soup):
        """
        提取相关股票
        
        Args:
            soup (BeautifulSoup): 解析后的HTML
            
        Returns:
            list: 相关股票列表
        """
        try:
            # 尝试从页面提取相关股票信息
            stock_tags = soup.select('a.stock')
            related_stocks = []
            for stock_tag in stock_tags:
                stock_code = stock_tag.text.strip()
                if stock_code:
                    related_stocks.append(stock_code)
            
            return related_stocks
        except Exception as e:
            logger.warning("提取相关股票失败：%s", str(e))
            return []
    
    def generate_news_id(self, url, title):
        """
        生成新闻ID
        
        Args:
            url (str): 新闻URL
            title (str): 新闻标题
            
        Returns:
            str: 新闻ID
        """
        # 使用URL和标题的组合生成唯一ID
        text = url + title
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def is_valid_news_url(self, url):
        """
        判断URL是否为有效的新闻链接
        
        Args:
            url (str): 链接URL
            
        Returns:
            bool: 是否为有效的新闻链接
        """
        # 检查URL是否为空
        if not url:
            return False
            
        # 检查URL是否为广告
        if self.ad_filter.is_ad_url(url):
            logger.info("过滤广告URL：%s", url)
            return False
            
        # 凤凰财经新闻URL模式
        patterns = [
            r'https?://finance\.ifeng\.com/\w/\d+/\d+_\d+\.shtml',
            r'https?://finance\.ifeng\.com/c/[a-zA-Z0-9]+',  # 新版文章URL模式 /c/8eJNY7hopdJ
            r'https?://finance\.ifeng\.com/a/\d+/\d+_\d+\.shtml',
            r'https?://finance\.ifeng\.com/[a-z]+/[a-z0-9]+/detail_\d+_\d+\.shtml',
            r'https?://finance\.ifeng\.com/[a-z]+/[a-z0-9]+/[a-zA-Z0-9]+',
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
                
        # 2024年新增：检查是否包含关键词路径
        key_paths = ['/c/', '/deepfinance/', '/stock/', '/ipo/', '/listedcompany/', '/greenfinance/']
        for path in key_paths:
            if path in url and 'finance.ifeng.com' in url:
                return True
        
        return False


if __name__ == "__main__":
    # 测试爬虫
    crawler = IfengCrawler(use_proxy=False, use_source_db=True)
    news_list = crawler.crawl(days=1, max_news=5)
    print(f"爬取到新闻数量：{len(news_list)}")
    for news in news_list:
        print(f"标题：{news['title']}")
        print(f"发布时间：{news['pub_time']}")
        print(f"来源：{news['source']}")
        print("-" * 50) 