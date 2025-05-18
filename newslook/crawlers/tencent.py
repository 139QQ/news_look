#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 腾讯财经爬虫
"""

import os
import re
import sys
import time
import hashlib
import random
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
import sqlite3

from app.crawlers.base import BaseCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords
from app.db.SQLiteManager import SQLiteManager
from app.utils.ad_filter import AdFilter  # 导入广告过滤器模块
from app.utils.image_detector import ImageDetector  # 导入图像识别模块

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('tencent')

class TencentCrawler(BaseCrawler):
    """腾讯财经爬虫，用于爬取腾讯财经的财经新闻"""
    
    # 新闻分类URL
    CATEGORY_URLS = {
        '财经': 'https://news.qq.com/ch/finance/',
        '股票': 'https://news.qq.com/ch/stock/',
        '公司': 'https://news.qq.com/ch/finance_company/',
        '产业': 'https://news.qq.com/ch/chuangye/',
        '宏观': 'https://news.qq.com/ch/finance_macro/',
        '国际': 'https://news.qq.com/ch/world/',
    }
    
    # 新闻API URL模板
    API_URL_TEMPLATE = "https://i.news.qq.com/trpc.qqnews_web.kv_srv.kv_srv_http_proxy/list?sub_srv_id={sub_srv_id}&srv_id=pc&offset={offset}&limit={limit}&strategy=1&ext={{\"pool\":[\"top\",\"hot\"],\"is_filter\":7,\"check_type\":true}}"
    
    # 分类与API参数映射
    CATEGORY_API_MAP = {
        '财经': 'finance',
        '股票': 'stock',
        '公司': 'finance_company',
        '产业': 'chuangye',
        '宏观': 'finance_macro',
        '国际': 'world'
    }
    
    # 内容选择器
    CONTENT_SELECTOR = 'div.content-article'
    
    # 时间选择器
    TIME_SELECTOR = 'div.article-time'
    
    # 作者选择器
    AUTHOR_SELECTOR = 'div.article-author'
    
    # 广告URL特征
    AD_URL_PATTERNS = [
        'download', 
        'app',
        'promotion',
        'activity',
        'zhuanti',
        'special',
        'advert',
        'subscribe',
        'vip',
        'client',
        'special',
        'topic',
        'hot',
        'apk',
        'store.qq.com'
    ]
    
    # 广告内容关键词
    AD_CONTENT_KEYWORDS = [
        '下载APP',
        '腾讯新闻APP',
        '腾讯财经APP',
        '扫描下载',
        '立即下载',
        '下载腾讯',
        '扫码下载',
        '专属福利',
        '点击下载',
        '安装腾讯',
        '腾讯新闻客户端',
        '独家活动',
        '活动详情',
        '注册即送',
        '点击安装',
        '官方下载',
        'APP专享',
        '扫一扫下载',
        '新人专享',
        '首次下载'
    ]
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化腾讯财经爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
        """
        # 设置来源和初始化基类
        self.source = "腾讯财经"
        self.name = "tencent"  # 添加name属性
        self.status = "idle"  # 添加爬虫状态属性
        self.last_run = None  # 添加上次运行时间属性
        self.next_run = None  # 添加下次运行时间属性
        self.error_count = 0  # 添加错误计数属性
        self.success_count = 0  # 添加成功计数属性
        self.proxy_manager = None  # 添加代理管理器属性
        self.delay = 5  # 默认延迟5秒
        self.selenium_timeout = 10  # Selenium超时时间
        self.use_selenium = False  # 默认不使用Selenium
        self.driver = None
        self.cookies = None
        self.max_retries = 3
        self.ad_filtered_count = 0  # 添加广告过滤计数器
        
        # 初始化父类
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, use_source_db=use_source_db, **kwargs)
        
        # 初始化会话
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 初始化广告过滤器
        self.ad_filter = AdFilter(source_name=self.source)
        # 初始化图像检测器
        self.image_detector = ImageDetector(cache_dir='./image_cache')
        
        # 设置默认日期范围
        self.default_days = 1
        
        # 如果提供了db_manager并且不是SQLiteManager类型，创建SQLiteManager
        if db_manager and not isinstance(db_manager, SQLiteManager):
            if hasattr(db_manager, 'db_path'):
                self.sqlite_manager = SQLiteManager(db_manager.db_path)
            else:
                # 使用传入的db_path或默认路径
                self.sqlite_manager = SQLiteManager(db_path or self.db_path)
        elif not db_manager:
            # 如果没有提供db_manager，创建SQLiteManager
            self.sqlite_manager = SQLiteManager(db_path or self.db_path)
        else:
            # 否则使用提供的db_manager
            self.sqlite_manager = db_manager
        
        logger.info(f"腾讯财经爬虫初始化完成，数据库路径: {self.db_path}")
    
    def crawl(self, days=1, max_pages=3):
        """
        爬取腾讯财经的新闻
        
        Args:
            days: 爬取的天数范围，默认为1天
            max_pages: 每个分类最多爬取的页数，默认为3页
        
        Returns:
            list: 爬取的新闻列表
        """
        logger.info(f"开始爬取腾讯财经新闻，天数范围: {days}天，每个分类最多爬取: {max_pages}页")
        
        # 清空新闻数据列表
        self.news_data = []
        
        # 重置广告过滤计数
        self.ad_filter.reset_filter_count()
        # 重置图像广告过滤计数
        self.image_detector.reset_ad_count()
        
        # 计算开始日期
        start_date = datetime.now() - timedelta(days=days)
        
        # 1. 首先尝试使用API获取新闻
        try:
            logger.info("尝试使用API获取腾讯财经新闻")
            success = self._crawl_from_api(max_pages, start_date)
            if success and self.news_data:
                logger.info(f"API获取成功，已获取 {len(self.news_data)} 条新闻")
            else:
                logger.info("API获取失败或未获取到新闻，尝试传统方法")
        except Exception as e:
            logger.error(f"使用API获取新闻失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 2. 如果API获取失败或没有足够的新闻，尝试从网页获取
        if not self.news_data or (max_pages is not None and len(self.news_data) < max_pages):
            remaining = max_pages - len(self.news_data) if max_pages is not None else None
            
            try:
                logger.info(f"尝试从网页获取腾讯财经新闻，还需 {remaining} 条") if remaining else logger.info("尝试从网页获取腾讯财经新闻")
                self._crawl_from_web(days, remaining, start_date)
            except Exception as e:
                logger.error(f"从网页获取新闻失败: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        # 3. 如果仍然没有足够的新闻，尝试使用备用URL
        if not self.news_data or (max_pages is not None and len(self.news_data) < max_pages):
            remaining = max_pages - len(self.news_data) if max_pages is not None else None
            
            logger.info("网页爬取未获取到足够新闻，尝试使用备用URL")
            try:
                self._crawl_from_backup_urls(remaining, start_date)
            except Exception as e:
                logger.error(f"从备用URL获取新闻失败: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        # 统计爬取结果
        logger.info(f"腾讯财经爬虫运行完成，共爬取 {len(self.news_data)} 条新闻")
        
        # 按分类统计
        category_counts = {}
        for news in self.news_data:
            category = news.get('category', '未分类')
            if category not in category_counts:
                category_counts[category] = 0
            category_counts[category] += 1
        
        for category, count in category_counts.items():
            logger.info(f"分类 '{category}' 爬取: {count} 条新闻")
        
        # 爬取结束后，确保数据被保存到数据库
        if hasattr(self, 'news_data') and self.news_data:
            saved_count = 0
            for news in self.news_data:
                if self.save_news_to_db(news):
                    saved_count += 1
            
            logger.info(f"成功保存 {saved_count}/{len(self.news_data)} 条新闻到数据库")
        
        # 在最后返回结果之前添加完成日志
        logger.info(f"腾讯财经爬取完成，共爬取新闻: {len(self.news_data)} 条，过滤广告: {self.ad_filter.get_filter_count()} 条，过滤广告图片: {self.image_detector.get_ad_count()} 张")
        return self.news_data
    
    def _crawl_from_api(self, max_pages, start_date):
        """
        通过API爬取腾讯财经新闻
        
        Args:
            max_pages: 最大新闻数量
            start_date: 开始日期
            
        Returns:
            bool: 是否成功获取新闻
        """
        total_fetched = 0
        
        # 遍历每个分类
        for category, sub_srv_id in self.CATEGORY_API_MAP.items():
            logger.info(f"通过API获取分类 '{category}' 的新闻")
            
            if max_pages is not None and total_fetched >= max_pages:
                logger.info(f"已达到最大新闻数量: {max_pages}，停止获取")
                break
            
            offset = 0
            page_size = 20
            retry_count = 0
            max_retries = 3
            
            while True:
                # 如果已达到最大数量，跳出循环
                if max_pages is not None and total_fetched >= max_pages:
                    logger.info(f"已达到最大新闻数量: {max_pages}，停止获取")
                    break
                
                # 计算当前页要获取的数量
                current_limit = page_size
                if max_pages is not None:
                    remaining = max_pages - total_fetched
                    if remaining < page_size:
                        current_limit = remaining
                
                # 构建API URL
                api_url = self.API_URL_TEMPLATE.format(
                    sub_srv_id=sub_srv_id,
                    offset=offset,
                    limit=current_limit
                )
                
                logger.info(f"请求API: {api_url}")
                
                # 发送请求
                try:
                    headers = {
                        'User-Agent': self.get_random_user_agent(),
                        'Referer': self.CATEGORY_URLS.get(category, 'https://news.qq.com/'),
                        'Accept': 'application/json, text/plain, */*',
                        'Origin': 'https://news.qq.com',
                        'Host': 'i.news.qq.com'
                    }
                    
                    response = requests.get(api_url, headers=headers, timeout=10)
                    
                    if response.status_code != 200:
                        logger.warning(f"API请求失败，状态码: {response.status_code}")
                        retry_count += 1
                        if retry_count >= max_retries:
                            logger.error(f"达到最大重试次数，跳过分类 '{category}'")
                            break
                        continue
                    
                    # 解析JSON响应
                    data = response.json()
                    
                    # 验证响应数据结构
                    if not data or 'data' not in data or 'list' not in data['data']:
                        logger.warning(f"API响应数据结构异常: {data}")
                        retry_count += 1
                        if retry_count >= max_retries:
                            logger.error(f"达到最大重试次数，跳过分类 '{category}'")
                            break
                        continue
                    
                    news_items = data['data']['list']
                    logger.info(f"API返回 {len(news_items)} 条新闻")
                    
                    if not news_items:
                        logger.info(f"分类 '{category}' 没有更多新闻，跳转到下一个分类")
                        break
                    
                    # 处理每条新闻
                    fetched_in_this_page = 0
                    for item in news_items:
                        try:
                            # 提取基本信息
                            news_url = item.get('url', '')
                            title = item.get('title', '')
                            
                            if not news_url or not title:
                                continue
                            
                            # 提取发布时间
                            pub_time_str = item.get('publish_time', '') or item.get('time', '')
                            pub_time = self._parse_api_time(pub_time_str)
                            
                            # 跳过旧新闻
                            if pub_time and pub_time < start_date:
                                logger.debug(f"新闻日期 {pub_time} 早于开始日期 {start_date}，跳过")
                                continue
                            
                            # 随机休眠，避免频繁请求
                            self.random_sleep(1, 2)
                            
                            # 爬取新闻详情
                            news_data = self.crawl_news_detail(news_url, category)
                            
                            if not news_data:
                                # 如果获取详情失败，创建一个基本的新闻对象
                                logger.info(f"获取新闻详情失败，创建基本新闻对象: {title}")
                                
                                # 提取封面图片
                                image_url = ''
                                if 'thumb_nail' in item and item['thumb_nail']:
                                    image_url = item['thumb_nail'].get('url', '')
                                
                                # 提取摘要
                                abstract = item.get('abstract', '') or item.get('intro', '')
                                
                                # 生成新闻ID
                                news_id = self.generate_news_id(news_url, title)
                                
                                news_data = {
                                    'id': news_id,
                                    'title': title,
                                    'content': abstract,
                                    'pub_time': pub_time.strftime('%Y-%m-%d %H:%M:%S') if pub_time else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'author': item.get('media_name', '') or item.get('source', '') or '腾讯财经',
                                    'source': self.source,
                                    'url': news_url,
                                    'keywords': '',
                                    'sentiment': 0,  # 中性
                                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'category': category,
                                    'images': image_url,
                                    'related_stocks': ''
                                }
                            
                            # 保存新闻数据
                            self.save_news_to_db(news_data)
                            self.news_data.append(news_data)
                            fetched_in_this_page += 1
                            total_fetched += 1
                            
                            logger.info(f"成功从API获取新闻: {title}")
                            
                            # 如果已达到最大数量，跳出循环
                            if max_pages is not None and total_fetched >= max_pages:
                                logger.info(f"已达到最大新闻数量: {max_pages}，停止获取")
                                break
                                
                        except Exception as e:
                            logger.error(f"处理API返回的新闻项失败: {str(e)}")
                            continue
                    
                    # 如果这一页没有获取到有效新闻，或者返回的数量小于请求的数量，说明没有更多新闻了
                    if fetched_in_this_page == 0 or len(news_items) < current_limit:
                        logger.info(f"分类 '{category}' 没有更多新闻，跳转到下一个分类")
                        break
                    
                    # 更新偏移量，获取下一页
                    offset += current_limit
                    
                    # 随机休眠，避免频繁请求
                    self.random_sleep(2, 4)
                    
                except Exception as e:
                    logger.error(f"API请求异常: {str(e)}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error(f"达到最大重试次数，跳过分类 '{category}'")
                        break
                    continue
        
        logger.info(f"通过API共获取 {total_fetched} 条新闻")
        return total_fetched > 0
    
    def _parse_api_time(self, time_str):
        """
        解析API返回的时间字符串
        
        Args:
            time_str: 时间字符串
            
        Returns:
            datetime: 日期时间对象
        """
        if not time_str:
            return None
        
        try:
            # 尝试解析Unix时间戳（秒或毫秒）
            if time_str.isdigit():
                timestamp = int(time_str)
                if timestamp > 9999999999:  # 如果是毫秒时间戳
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp)
            
            # 尝试解析常见日期格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%Y年%m月%d日 %H:%M:%S',
                '%Y年%m月%d日 %H:%M',
                '%Y年%m月%d日'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except:
                    continue
            
            logger.warning(f"无法解析时间字符串: {time_str}")
            return None
        except Exception as e:
            logger.error(f"解析时间字符串失败: {time_str}, 错误: {str(e)}")
            return None
    
    def _crawl_from_web(self, days, max_pages, start_date):
        """
        从网页爬取腾讯财经新闻
        
        Args:
            days: 爬取天数
            max_pages: 最大新闻数量
            start_date: 开始日期
        """
        total_fetched = 0
        
        # 爬取首页
        try:
            logger.info("尝试从首页获取新闻")
            home_url = "https://news.qq.com/ch/finance/"
            html = self.fetch_page(home_url)
            if html:
                news_links = self.extract_news_links_from_home(html, "财经")
                logger.info(f"从首页提取到新闻链接数量: {len(news_links)}")
                
                # 爬取每个新闻详情
                for news_link in news_links:
                    # 如果已经达到最大数量，跳出循环
                    if max_pages is not None and total_fetched >= max_pages:
                        logger.info(f"已达到最大新闻数量: {max_pages}，停止获取")
                        break
                    
                    # 随机休眠，避免被反爬
                    self.random_sleep(1, 3)
                    
                    # 爬取新闻详情
                    news_data = self.crawl_news_detail(news_link, "财经")
                    if not news_data:
                        continue
                    
                    # 检查新闻日期是否在指定范围内
                    try:
                        news_date = datetime.strptime(news_data['pub_time'].split(' ')[0], '%Y-%m-%d')
                        if news_date < start_date:
                            logger.debug(f"新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                            continue
                    except Exception as e:
                        logger.warning(f"解析新闻日期失败: {news_data['pub_time']}, 错误: {str(e)}")
                    
                    # 保存新闻数据
                    self.save_news_to_db(news_data)
                    self.news_data.append(news_data)
                    total_fetched += 1
                    logger.info(f"成功爬取新闻: {news_data['title']}")
        except Exception as e:
            logger.error(f"从首页爬取新闻失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 爬取各个分类的新闻
        for category, url in self.CATEGORY_URLS.items():
            # 如果已经达到最大数量，跳出循环
            if max_pages is not None and total_fetched >= max_pages:
                logger.info(f"已达到最大新闻数量: {max_pages}，停止获取")
                break
            
            try:
                logger.info(f"开始爬取分类: {category}, URL: {url}")
                html = self.fetch_page(url)
                if not html:
                    continue
                
                news_links = self.extract_news_links_from_page(html, category)
                logger.info(f"分类 '{category}' 找到 {len(news_links)} 个潜在新闻项")
                
                # 爬取每个新闻详情
                for news_link in news_links:
                    # 如果已经达到最大数量，跳出循环
                    if max_pages is not None and total_fetched >= max_pages:
                        logger.info(f"已达到最大新闻数量: {max_pages}，停止获取")
                        break
                    
                    # 随机休眠，避免被反爬
                    self.random_sleep(1, 3)
                    
                    # 爬取新闻详情
                    news_data = self.crawl_news_detail(news_link, category)
                    if not news_data:
                        continue
                    
                    # 检查新闻日期是否在指定范围内
                    try:
                        news_date = datetime.strptime(news_data['pub_time'].split(' ')[0], '%Y-%m-%d')
                        if news_date < start_date:
                            logger.debug(f"新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                            continue
                    except Exception as e:
                        logger.warning(f"解析新闻日期失败: {news_data['pub_time']}, 错误: {str(e)}")
                    
                    # 保存新闻数据
                    self.save_news_to_db(news_data)
                    self.news_data.append(news_data)
                    total_fetched += 1
                    logger.info(f"成功爬取新闻: {news_data['title']}")
            except Exception as e:
                logger.error(f"爬取分类 '{category}' 失败: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info(f"从网页共爬取 {total_fetched} 条新闻")
    
    def extract_news_links_from_home(self, html, category):
        """
        从首页提取新闻链接
        
        Args:
            html: 首页HTML内容
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. 尝试获取js中的数据
            script_data = self.extract_js_data(soup)
            if script_data:
                for url in script_data:
                    if self.is_valid_news_url(url):
                        news_links.append(url)
                        
            # 2. 尝试获取轮播图新闻
            carousel_items = soup.select('.swiper-slide, .slider-item, .swiper-item, [class*="banner"], [class*="slide"]')
            for item in carousel_items:
                a_tag = item.select_one('a')
                if a_tag and 'href' in a_tag.attrs:
                    href = a_tag['href']
                    if self.is_valid_news_url(href):
                        news_links.append(href)
            
            # 3. 尝试获取新闻列表
            news_items = soup.select('.list li, .news-list li, .news-item, article, .item, .txt-list li, [class*="news"] li, [class*="article"]')
            for item in news_items:
                a_tag = item.select_one('a')
                if a_tag and 'href' in a_tag.attrs:
                    href = a_tag['href']
                    if self.is_valid_news_url(href):
                        news_links.append(href)
            
            # 4. 尝试获取标题为链接的新闻
            title_links = soup.select('h1 a, h2 a, h3 a, .title a, .art_title a, [class*="title"] a')
            for a_tag in title_links:
                if 'href' in a_tag.attrs:
                    href = a_tag['href']
                    if self.is_valid_news_url(href):
                        news_links.append(href)
            
            # 5. 如果以上都没找到，尝试寻找所有可能的新闻链接
            if not news_links:
                logger.info("尝试查找所有可能的新闻链接")
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if self.is_valid_news_url(href):
                        news_links.append(href)
            
            # 修复链接，去重
            news_links = [self.fix_url(link) for link in news_links]
            news_links = list(set(news_links))
            logger.info(f"从首页提取到 {len(news_links)} 个新闻链接")
            
        except Exception as e:
            logger.error(f"从首页提取新闻链接失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return news_links
    
    def extract_news_links_from_page(self, html, category):
        """
        从HTML中提取新闻链接列表
        
        Args:
            html: HTML内容
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        if not html:
            return []
        
        news_links = []
        
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找包含新闻链接的元素
            link_elements = []
            
            # 方法1：查找所有链接元素
            all_links = soup.find_all('a', href=True)
            
            # 只保留可能是新闻链接的元素
            for link in all_links:
                href = link.get('href', '')
                if self.is_valid_news_url(href):
                    link_elements.append(link)
            
            # 方法2：查找特定新闻卡片中的链接
            news_cards = soup.select('.list-card, .channel-card, .card, article, .list-item, .item, .txp-waterfall-item, .news-list-item')
            for card in news_cards:
                links = card.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if self.is_valid_news_url(href) and link not in link_elements:
                        link_elements.append(link)
            
            # 方法3：查找特定新闻标题中的链接
            title_links = soup.select('.title a, .tt a, h3 a, h2 a, .content-title a')
            for link in title_links:
                href = link.get('href', '')
                if self.is_valid_news_url(href) and link not in link_elements:
                    link_elements.append(link)
            
            # 提取所有有效的新闻链接
            for link in link_elements:
                href = link.get('href', '')
                # 处理相对URL
                if href.startswith('/'):
                    href = f"https://news.qq.com{href}"
                # 检查URL是否有效
                if self.is_valid_news_url(href):
                    if href not in news_links:
                        news_links.append(href)
            
            logger.info(f"从分类 '{category}' 页面提取到 {len(news_links)} 个新闻链接")
        except Exception as e:
            logger.error(f"提取新闻链接失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return news_links
    
    def fix_url(self, url):
        """
        修复URL，确保是完整的URL
        
        Args:
            url: 原始URL
        
        Returns:
            str: 修复后的URL
        """
        if url.startswith('//'):
            return 'https:' + url
        elif not url.startswith('http'):
            if url.startswith('/'):
                return 'https://finance.qq.com' + url
            else:
                return 'https://finance.qq.com/' + url
        return url
    
    def is_valid_news_url(self, url):
        """
        判断URL是否是有效的新闻URL（增强版）
        
        Args:
            url: URL字符串
        
        Returns:
            bool: 是否是有效的新闻URL
        """
        if not url:
            return False
            
        # 检查URL是否为广告
        if self.is_ad_url(url):
            logger.info(f"过滤广告URL: {url}")
            self.ad_filtered_count += 1
            return False
        
        # 转为小写进行比较
        url_lower = url.lower()
        
        # 排除不是新闻内容的URL
        exclude_keywords = [
            '/tag/', '/vlike/', '/download/', '/about/', '/privacy/', '/terms/', 
            '/login', '/register', '/search', '/app/', '/video/', '/live/', 
            '/map/', '/sitemap', '/rss/', '/feed/', '/comment/', '/user/', 
            '/account/', '/profile/', '/help/', '/faq/', '/support/', 
            '/special/', '/topic/', '/column/', '/home/', '/index/', 
            '/photo/', '/gallery/', '/picture/', '/image/', '/img/', '/podcast/',
            'javascript:', 'mailto:', 'tel:', '#', 'javascript:void', 'javascript:;',
            'javascript:void(0)', 'javascript:;', 'javascript:void(0);'
        ]
        
        for keyword in exclude_keywords:
            if keyword in url_lower:
                return False
        
        # 判断是否是腾讯新闻链接
        tencent_patterns = [
            'new.qq.com', 'news.qq.com', 'finance.qq.com', 'stock.qq.com',
            'money.qq.com', 'view.inews.qq.com', 'view.news.qq.com'
        ]
        
        # 腾讯新闻文章URL的常见模式
        article_patterns = [
            '/a/', '/rain/a/', '/omn/', '/cmsn/', '/20', '/article_', 
            '/rain/a', 'inews.gtimg.com', '.html'
        ]
        
        is_tencent = any(pattern in url_lower for pattern in tencent_patterns)
        is_article = any(pattern in url_lower for pattern in article_patterns)
        
        return is_tencent and is_article
    
    def is_ad_url(self, url):
        """
        判断URL是否为广告URL
        
        Args:
            url: URL地址
            
        Returns:
            bool: 是否为广告URL
        """
        if not url:
            return False
            
        # 检查URL是否包含广告特征
        for pattern in self.AD_URL_PATTERNS:
            if pattern in url:
                logger.debug(f"检测到广告URL: {url}, 匹配模式: {pattern}")
                return True
                
        # 检查URL是否是腾讯APP下载页
        if 'download.qq.com' in url or 'dldir1.qq.com' in url:
            logger.debug(f"检测到APP下载页URL: {url}")
            return True
        
        return False
    
    def is_ad_content(self, text):
        """
        判断文本内容是否包含广告关键词
        
        Args:
            text: 文本内容
            
        Returns:
            bool: 是否包含广告关键词
        """
        if not text:
            return False
            
        # 检查文本是否包含广告关键词
        for keyword in self.AD_CONTENT_KEYWORDS:
            if keyword in text:
                logger.debug(f"检测到广告关键词: {keyword}")
                return True
                
        # 检查APP下载相关内容
        app_download_patterns = [
            r'扫码下载.*app',
            r'扫码.*下载.*腾讯',
            r'下载.*腾讯.*app',
            r'下载.*腾讯.*客户端',
            r'腾讯.*app.*下载',
            r'官方.*app.*下载',
            r'app.*扫码.*下载'
        ]
        
        for pattern in app_download_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"检测到APP下载正则匹配: {pattern}")
                return True
                
        return False
    
    def crawl_news_detail(self, url, category, index=0, max_retries=3, **kwargs):
        """
        爬取新闻详情
        
        Args:
            url: 新闻URL
            category: 新闻分类
            index: 新闻索引，用于日志和延迟处理
            max_retries: 最大重试次数
        
        Returns:
            dict: 新闻详情数据
        """
        # 检查URL是否为广告
        if self.ad_filter.is_ad_url(url):
            logger.info(f"URL已被识别为广告，跳过: {url}")
            return None
            
        # 使用广告过滤器检查URL
        if any(pattern in url for pattern in self.AD_URL_PATTERNS):
            logger.info(f"URL包含广告特征，跳过: {url}")
            self.ad_filter.increment_filter_count()
            return None
        
        # 尝试多次获取页面内容
        for retry in range(max_retries):
            try:
                # 随机延迟
                time.sleep(random.uniform(1, 3))
                
                # 获取页面内容
                response = self.session.get(url, headers=self.get_random_headers(), timeout=10)
                response.raise_for_status()
                
                # 解析页面内容
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # 提取新闻内容
                content_element = soup.select_one(self.CONTENT_SELECTOR)
                if not content_element:
                    logger.warning(f"未找到内容区域: {url}")
                    continue
                    
                # 提取标题
                title = soup.select_one('h1').text.strip() if soup.select_one('h1') else "未知标题"
                
                # 检查内容是否为广告
                if self.ad_filter.is_ad_content(content_element.text):
                    logger.info(f"内容被识别为广告，跳过: {url}")
                    self.ad_filter.increment_filter_count()
                    return None
            
                # 处理图片，过滤广告图片
                img_tags = content_element.find_all('img')
                for img in img_tags:
                    img_url = img.get('src', '')
                    if img_url and self.image_detector.is_ad_image(img_url):
                        logger.info(f"检测到广告图片，已移除: {img_url}")
                        img.decompose()
            
                # 提取发布时间
                pub_time_element = soup.select_one(self.TIME_SELECTOR)
                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if pub_time_element:
                    try:
                        time_text = pub_time_element.text.strip()
                        # 处理时间格式
                        pub_time = self.parse_date(time_text)
                    except:
                        logger.warning(f"解析发布时间失败，使用当前时间")
            
                # 提取作者
                author_element = soup.select_one(self.AUTHOR_SELECTOR)
                author = author_element.text.strip() if author_element else "腾讯财经"
                
                # 提取内容
                content_html = str(content_element)
                content_text = clean_html(content_html)
            
                # 构建新闻数据
                news_data = {
                    'url': url,
                    'title': title,
                    'source': self.source,
                    'category': category,
                    'content': content_text,
                    'content_html': content_html,
                    'pub_time': pub_time,
                    'author': author,
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                return news_data

            except Exception as e:
                logger.error(f"爬取新闻失败 (尝试 {retry+1}/{max_retries}): {str(e)}")
                if retry == max_retries - 1:
                    logger.error(f"达到最大重试次数，放弃爬取: {url}")
        
        return None
    
    def parse_date(self, date_str):
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
        
        Returns:
            str: 格式化的日期字符串
        """
        try:
            # 清理日期字符串
            date_str = date_str.strip()
            date_str = re.sub(r'发布时间[:：]\s*', '', date_str)  # 移除"发布时间:"
            
            # 处理"今天"、"昨天"等相对日期
            now = datetime.now()
            if '今天' in date_str:
                date_str = date_str.replace('今天', now.strftime('%Y-%m-%d'))
            elif '昨天' in date_str:
                yesterday = now - timedelta(days=1)
                date_str = date_str.replace('昨天', yesterday.strftime('%Y-%m-%d'))
            
            # 处理各种日期格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y年%m月%d日 %H:%M:%S',
                '%Y年%m月%d日 %H:%M',
                '%Y年%m月%d日',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d %H:%M',
                '%Y/%m/%d'
            ]
            
            # 尝试各种格式
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            
            # 如果以上格式都不匹配，尝试提取日期和时间
            date_match = re.search(r'(\d{4})[-年/](\d{1,2})[-月/](\d{1,2})[日]?', date_str)
            time_match = re.search(r'(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?', date_str)
            
            if date_match:
                year, month, day = date_match.groups()
                hour, minute, second = '0', '0', '0'
                
                if time_match:
                    hour, minute = time_match.groups()[:2]
                    second = time_match.groups()[2] if time_match.groups()[2] else '0'
                
                return f"{year}-{int(month):02d}-{int(day):02d} {int(hour):02d}:{int(minute):02d}:{int(second):02d}"
        
        except Exception as e:
            logger.error(f"解析日期失败: {date_str}, 错误: {str(e)}")
        
        # 如果解析失败，返回当前时间
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def random_sleep(self, min_seconds=1, max_seconds=3):
        """
        随机休眠一段时间，避免被反爬
        
        Args:
            min_seconds: 最小休眠时间（秒）
            max_seconds: 最大休眠时间（秒）
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time) 
    
    def fetch_page(self, url, retry_count=3, delay=2):
        """
        获取页面内容，并处理反爬机制
        
        Args:
            url: 页面URL
            retry_count: 重试次数
            delay: 请求之间的延迟时间（秒）
            
        Returns:
            str: 页面内容，获取失败则返回None
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://news.qq.com/',
            'Upgrade-Insecure-Requests': '1',
            'sec-ch-ua': '"Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        
        for attempt in range(retry_count):
            try:
                # 使用代理（如果启用）
                proxies = None
                if self.use_proxy and self.proxy_manager:
                    proxy = self.proxy_manager.get_proxy()
                    if proxy:
                        proxies = {'http': proxy, 'https': proxy}
                
                # 发送请求
                logger.info(f"请求页面 {url}，第 {attempt+1} 次尝试")
                session = requests.Session()
                response = session.get(
                    url, 
                    headers=headers, 
                    proxies=proxies, 
                    timeout=10
                )
                
                # 检查是否是成功的响应
                if response.status_code != 200:
                    logger.warning(f"请求失败，状态码: {response.status_code}, URL: {url}")
                    time.sleep(delay + random.uniform(1, 3))  # 额外添加随机延迟
                    continue
                
                # 检查是否被重定向到反爬页面
                if "验证" in response.text or "安全检查" in response.text:
                    logger.warning(f"可能遇到反爬措施，内容长度: {len(response.text)}，URL: {url}")
                    
                    # 检查是否是响应类型问题
                    if 'application/json' in response.headers.get('Content-Type', ''):
                        logger.warning(f"响应类型为JSON而非HTML，尝试解析JSON")
                        try:
                            # 尝试从JSON响应中提取URL
                            data = response.json()
                            if 'url' in data:
                                new_url = data['url']
                                logger.info(f"从JSON响应中找到新URL: {new_url}，重新请求")
                                return self.fetch_page(new_url, retry_count - attempt - 1, delay)
                        except:
                            pass
                    
                    # 更换User-Agent再试
                    headers['User-Agent'] = self.get_random_user_agent()
                    
                    # 增加延迟时间
                    time.sleep(delay + random.uniform(3, 6))
                    continue
                
                # 处理编码问题
                if response.encoding == 'ISO-8859-1':
                    # 对于误判为ISO-8859-1的页面，先尝试utf-8
                    try:
                        content = response.content.decode('utf-8')
                    except UnicodeDecodeError:
                        # 如果utf-8解码失败，尝试GBK
                        try:
                            content = response.content.decode('gbk')
                        except UnicodeDecodeError:
                            # 如果GBK也失败，使用gb18030（超集）
                            content = response.content.decode('gb18030')
                else:
                    # 使用响应的编码
                    content = response.text
                
                return content
            
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {str(e)}, URL: {url}")
                time.sleep(delay)
        
        logger.error(f"获取页面内容失败，已达到最大重试次数: {retry_count}, URL: {url}")
        return None
    
    def get_random_user_agent(self):
        """获取随机User-Agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Mobile/15E148 Safari/604.1',
        ]
        return random.choice(user_agents)
    
    def extract_js_data(self, soup):
        """
        从JS脚本中提取数据
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            list: 提取的URL列表
        """
        urls = []
        try:
            # 查找所有脚本标签
            for script in soup.find_all('script'):
                if not script.string:
                    continue
                
                # 查找定义新闻数据的JavaScript变量
                if 'var data' in script.string or 'window.DATA' in script.string or 'newslist' in script.string:
                    # 提取URL
                    links = re.findall(r'\"url\":\"(http[^\"]+)\"', script.string)
                    urls.extend(links)
                    
                    # 提取href
                    hrefs = re.findall(r'\"href\":\"(http[^\"]+)\"', script.string)
                    urls.extend(hrefs)
        except Exception as e:
            logger.error(f"从JS脚本提取数据失败: {str(e)}")
        
        # 解码URL中的转义字符
        decoded_urls = []
        for url in urls:
            try:
                # 去除多余的转义字符
                url = url.replace('\\', '')
                decoded_urls.append(url)
            except Exception as e:
                logger.error(f"解码URL失败: {url}, 错误: {str(e)}")
        
        return decoded_urls
    
    def _crawl_from_backup_urls(self, max_pages, start_date):
        """
        从备用URL列表爬取新闻
        
        Args:
            max_pages: 最大新闻数量
            start_date: 开始日期
        
        Returns:
            bool: 是否成功获取了新闻
        """
        # 备用URL基础列表 - 按分类组织
        backup_urls = {
            "财经": [
                "https://new.qq.com/rain/a/20240322A01N6300",
                "https://new.qq.com/rain/a/20240322A01IVF00",
                "https://new.qq.com/rain/a/20240321A03RZ900",
                "https://new.qq.com/rain/a/20240322A00MOH00",
                "https://new.qq.com/omn/20240322/20240322A01CLT00.html",
                "https://finance.qq.com/a/20240322/001021.htm",
            ],
            "股票": [
                "https://new.qq.com/rain/a/20240322A00CTO00", 
                "https://new.qq.com/rain/a/20240322A00L0700",
                "https://new.qq.com/omn/20240322/20240322A0272G00.html",
                "https://stock.qq.com/a/20240322/002931.htm",
            ],
            "公司": [
                "https://new.qq.com/rain/a/20240322A00KAO00",
                "https://new.qq.com/rain/a/20240322A00JE000",
                "https://finance.qq.com/a/20240322/001124.htm",
            ],
            "宏观": [
                "https://new.qq.com/rain/a/20240322A00HS500",
                "https://new.qq.com/rain/a/20240322A00GP700",
                "https://new.qq.com/omn/20240322/20240322A02YWO00.html",
            ],
            "国际": [
                "https://new.qq.com/rain/a/20240322A00FS800",
                "https://new.qq.com/rain/a/20240322A00F9F00", 
                "https://new.qq.com/omn/20240322/20240322A040CF00.html",
            ]
        }
        
        # 备用新闻列表页URL
        backup_list_pages = [
            "https://new.qq.com/ch/finance/",
            "https://new.qq.com/ch/stock/",
            "https://finance.qq.com/",
            "https://finance.qq.com/stock/",
            "https://finance.qq.com/roll.shtml",
            "https://stock.qq.com/",
            "https://new.qq.com/zt/template/?id=FIN2017092703",  # 财经专题
        ]
        
        # 可能的腾讯新闻URL模式
        url_patterns = [
            "https://new.qq.com/rain/a/{date}{part1}{d}{part2}00",
            "https://new.qq.com/omn/{date}/{date}{part1}{d}{part2}00.html",
            "https://finance.qq.com/a/{date}/{d}{part1}{part2}.htm",
        ]
        
        # 生成一些基于模式的URL
        pattern_urls = []
        date_patterns = []
        
        # 添加最近几天的日期
        for i in range(7):
            day = datetime.now() - timedelta(days=i)
            date_pattern = day.strftime('%Y%m%d')
            date_patterns.append(date_pattern)
        
        # 生成不同字母组合的URL
        for date in date_patterns:
            for pattern in url_patterns:
                # 限制生成的URL数量
                if len(pattern_urls) > 200:  # 限制生成的URL数量
                    break
                    
                for part1 in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:5]:  # 限制字母范围以控制数量
                    for d in range(5):  # 限制数字范围
                        for part2 in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:5]:
                            # 随机采样，减少URL数量
                            if random.random() < 0.05:  # 只有5%的概率生成该URL
                                try:
                                    url = pattern.format(date=date, part1=part1, d=d, part2=part2)
                                    pattern_urls.append(url)
                                except:
                                    continue
        
        # 将所有URL整合到一个列表中
        all_urls = []
        
        # 首先添加已知有效的备用URL
        for category, urls in backup_urls.items():
            for url in urls:
                all_urls.append((url, category))
        
        # 添加从备用新闻列表页提取的URL
        for list_page in backup_list_pages:
            try:
                logger.info(f"尝试从备用列表页获取新闻链接: {list_page}")
                # 使用Selenium获取页面，因为这些页面通常需要JS渲染
                html = self.fetch_page_with_selenium(list_page, wait_time=8)
                if html:
                    # 提取新闻链接
                    links = self.extract_news_links_from_page(html, "财经")
                    for link in links:
                        # 根据链接特征判断分类
                        category = self.determine_category_from_url(link)
                        all_urls.append((link, category))
                    logger.info(f"从列表页 {list_page} 提取到 {len(links)} 个新闻链接")
                
                # 随机休眠，避免反爬
                self.random_sleep(3, 5)
            except Exception as e:
                logger.error(f"从列表页 {list_page} 提取链接失败: {str(e)}")
                continue
        
        # 然后添加生成的模式URL，并标记为通用分类
        for url in pattern_urls:
            category = self.determine_category_from_url(url)
            all_urls.append((url, category))
        
        # 打乱URL列表，增加随机性
        random.shuffle(all_urls)
        
        # 限制URL数量
        if len(all_urls) > 500:  # 设置合理的上限以避免过多请求
            all_urls = all_urls[:500]
        
        logger.info(f"备用URL总数: {len(all_urls)}")
        
        # 爬取新闻
        total_fetched = 0
        selenium_initialized = False
        selenium_driver = None
        
        for url, category in all_urls:
            # 如果已经达到最大数量，跳出循环
            if max_pages is not None and total_fetched >= max_pages:
                logger.info(f"已达到最大新闻数量: {max_pages}，停止获取")
                break
            
            # 随机休眠，避免被反爬
            self.random_sleep(1, 3)
            
            # 爬取新闻详情
            try:
                # 先使用常规方法尝试
                news_data = self.crawl_news_detail(url, category)
                
                # 如果失败，使用增强版方法
                if not news_data:
                    logger.info(f"常规方法获取失败，使用增强版方法: {url}")
                    
                    # 使用Selenium直接爬取
                    if not selenium_initialized:
                        try:
                            # 仅当需要时才初始化Selenium
                            from selenium import webdriver
                            from selenium.webdriver.chrome.options import Options
                            from selenium.webdriver.chrome.service import Service
                            from webdriver_manager.chrome import ChromeDriverManager
                            
                            # 配置Chrome选项
                            chrome_options = Options()
                            chrome_options.add_argument("--headless")
                            chrome_options.add_argument("--disable-gpu")
                            chrome_options.add_argument("--no-sandbox")
                            chrome_options.add_argument("--disable-dev-shm-usage")
                            chrome_options.add_argument(f"user-agent={self.get_random_user_agent()}")
                            
                            # 初始化WebDriver
                            service = Service(ChromeDriverManager().install())
                            selenium_driver = webdriver.Chrome(service=service, options=chrome_options)
                            selenium_driver.set_page_load_timeout(30)
                            selenium_initialized = True
                            logger.info("Selenium WebDriver初始化成功")
                        except Exception as e:
                            logger.error(f"初始化Selenium失败: {str(e)}")
                            selenium_initialized = False
                    
                    # 使用已初始化的WebDriver获取页面
                    if selenium_initialized and selenium_driver:
                        try:
                            logger.info(f"使用Selenium直接访问: {url}")
                            selenium_driver.get(url)
                            # 等待页面加载
                            selenium_driver.implicitly_wait(5)
                            
                            # 获取页面内容
                            html = selenium_driver.page_source
                            
                            # 使用BeautifulSoup解析
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # 提取标题
                            title_element = soup.select_one('h1, .title, .content-title, .article-title, .main-title')
                            if title_element:
                                title = title_element.get_text().strip()
                                
                                # 提取内容
                                content_element = soup.select_one('.content-article, article, .article-content, .content')
                                content = ""
                                if content_element:
                                    # 获取所有段落文本
                                    paragraphs = []
                                    for p in content_element.select('p'):
                                        text = p.get_text().strip()
                                        if text:
                                            paragraphs.append(text)
                                    
                                    content = '\n'.join(paragraphs)
                                
                                if content:
                                    # 提取发布时间
                                    pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    time_element = soup.select_one('.time, .article-time, .pubtime, .publish-time, .date')
                                    if time_element:
                                        time_text = time_element.get_text().strip()
                                        # 尝试解析时间
                                        try:
                                            pub_time = self.parse_date(time_text)
                                            if not pub_time:
                                                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                            else:
                                                pub_time = pub_time.strftime('%Y-%m-%d %H:%M:%S')
                                        except:
                                            pass
                                    
                                    # 提取作者/来源
                                    author = "腾讯财经"
                                    author_element = soup.select_one('.author, .article-author, .source')
                                    if author_element:
                                        author = author_element.get_text().strip()
                                        author = author.replace("来源：", "").replace("作者：", "").strip()
                                    
                                    # 生成新闻ID
                                    news_id = self.generate_news_id(url, title)
                                    
                                    # 构建新闻数据
                                    news_data = {
                                        'id': news_id,
                                        'title': title,
                                        'content': content,
                                        'content_html': '',
                                        'pub_time': pub_time,
                                        'author': author,
                                        'source': self.source,
                                        'url': url,
                                        'keywords': '',
                                        'images': '',
                                        'related_stocks': '',
                                        'sentiment': 0,
                                        'category': category,
                                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    }
                                    
                                    logger.info(f"使用Selenium成功获取新闻: {title}")
                        except Exception as e:
                            logger.error(f"Selenium获取页面失败: {url}, 错误: {str(e)}")
                
                if not news_data:
                    continue
                
                # 检查新闻日期是否在指定范围内
                try:
                    pub_time = news_data['pub_time']
                    if isinstance(pub_time, str):
                        news_date = datetime.strptime(pub_time.split(' ')[0], '%Y-%m-%d')
                    else:
                        news_date = pub_time
                        
                    if news_date < start_date:
                        logger.debug(f"新闻日期 {news_date} 早于开始日期 {start_date}，跳过")
                        continue
                except Exception as e:
                    logger.warning(f"解析新闻日期失败: {news_data.get('pub_time', '')}, 错误: {str(e)}")
                
                # 保存新闻数据
                self.save_news_to_db(news_data)
                self.news_data.append(news_data)
                total_fetched += 1
                logger.info(f"成功从备用URL爬取新闻: {news_data['title']}")
                
                # 如果已经成功获取了10条新闻，增加休眠时间以避免被封
                if total_fetched % 10 == 0:
                    logger.info(f"已成功获取 {total_fetched} 条新闻，增加休眠时间")
                    self.random_sleep(5, 8)
            except Exception as e:
                logger.error(f"爬取备用URL失败: {url}, 错误: {str(e)}")
                continue
        
        # 清理资源
        if selenium_initialized and selenium_driver:
            try:
                selenium_driver.quit()
                logger.info("Selenium WebDriver已关闭")
            except:
                pass
        
        logger.info(f"从备用URL列表共爬取 {total_fetched} 条新闻")
        return total_fetched > 0
        
    def determine_category_from_url(self, url):
        """
        根据URL确定新闻分类
        
        Args:
            url: 新闻URL
        
        Returns:
            str: 新闻分类
        """
        url_lower = url.lower()
        
        # 股票相关
        if any(keyword in url_lower for keyword in ['stock', 'market', '股票', '行情', '大盘']):
            return '股票'
        
        # 公司相关
        if any(keyword in url_lower for keyword in ['company', 'finance_company', 'business', '公司']):
            return '公司'
        
        # 宏观相关
        if any(keyword in url_lower for keyword in ['macro', 'economy', 'finance_macro', '宏观', '经济']):
            return '宏观'
        
        # 国际相关
        if any(keyword in url_lower for keyword in ['world', 'global', 'international', '国际']):
            return '国际'
        
        # 默认为财经
        return '财经'
        
    def fetch_page_with_selenium(self, url, wait_time=5):
        """
        使用Selenium获取页面内容，处理JS渲染内容
        
        Args:
            url: 页面URL
            wait_time: 等待页面加载的时间（秒）
            
        Returns:
            str: 页面内容，获取失败则返回None
        """
        try:
            # 检查是否已安装selenium
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from webdriver_manager.chrome import ChromeDriverManager
            except ImportError:
                logger.error("未安装Selenium相关包，无法使用Selenium获取页面")
                return None
            
            logger.info(f"使用Selenium获取页面: {url}")
            
            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 无头模式
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"user-agent={self.get_random_user_agent()}")
            
            # 添加更多选项来避免检测
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            # 初始化WebDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 执行额外的脚本来规避检测
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 设置页面加载超时
            driver.set_page_load_timeout(30)
            
            try:
                # 访问URL
                driver.get(url)
                
                # 等待页面加载完成，最多等待wait_time秒
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # 额外等待一段时间，让JavaScript充分执行
                import time
                time.sleep(2)
                
                # 尝试查找新闻内容元素
                try:
                    content_element = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".content-article, article, .article-content, .content"))
                    )
                    logger.info("找到内容元素，页面加载完成")
                except:
                    logger.info("未找到特定内容元素，但页面已加载")
                
                # 获取页面内容
                html = driver.page_source
                
                # 关闭WebDriver
                driver.quit()
                
                return html
            except Exception as e:
                # 捕获访问URL时可能发生的异常
                logger.error(f"Selenium访问URL时发生错误: {str(e)}")
                driver.quit()
                return None
        except Exception as e:
            logger.error(f"使用Selenium获取页面失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def generate_news_id(self, url, title):
        """
        生成新闻ID
        
        Args:
            url: 新闻URL
            title: 新闻标题
        
        Returns:
            str: 新闻ID
        """
        # 使用URL和标题的组合生成唯一ID
        id_str = f"{url}_{title}"
        return hashlib.md5(id_str.encode('utf-8')).hexdigest()
    
    def save_news_to_db(self, news):
        """
        保存新闻到数据库
        
        Args:
            news: 新闻数据字典
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 直接使用sqlite3连接将新闻保存到数据库
            # 确保目录存在
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建表（如果不存在）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                pub_time TEXT,
                author TEXT,
                source TEXT,
                url TEXT UNIQUE,
                keywords TEXT,
                sentiment REAL,
                crawl_time TEXT,
                category TEXT,
                images TEXT,
                related_stocks TEXT,
                content_html TEXT,
                classification TEXT
            )
            ''')
            conn.commit()
            
            # 准备SQL语句
            sql = """
            INSERT OR REPLACE INTO news (
                id, title, content, pub_time, author, source, url, 
                keywords, sentiment, crawl_time, category, images, 
                related_stocks, content_html, classification
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """
            
            # 准备数据
            values = (
                news.get('id', ''),
                news.get('title', ''),
                news.get('content', ''),
                news.get('pub_time', ''),
                news.get('author', ''),
                news.get('source', self.source),  # 使用爬虫的source属性作为默认值
                news.get('url', ''),
                news.get('keywords', ''),
                news.get('sentiment', 0),  # 默认为中性
                news.get('crawl_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                news.get('category', ''),
                news.get('images', ''),
                news.get('related_stocks', ''),
                news.get('content_html', ''),
                news.get('classification', '')
            )
            
            # 执行SQL
            cursor.execute(sql, values)
            conn.commit()
            conn.close()
            
            logger.info(f"新闻已保存到数据库: {news.get('title', '未知标题')}")
            return True
            
        except Exception as e:
            logger.error(f"保存新闻到数据库失败: {news.get('title', '未知标题')}, 错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_random_headers(self):
        """
        获取随机请求头
        
        Returns:
            dict: 随机请求头
        """
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        return headers 