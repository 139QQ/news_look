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

from app.crawlers.base import BaseCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('tencent')

class TencentCrawler(BaseCrawler):
    """腾讯财经爬虫，用于爬取腾讯财经的财经新闻"""
    
    # 新闻分类URL
    CATEGORY_URLS = {
        '财经': 'https://finance.qq.com/roll.shtml',
        '股票': 'https://finance.qq.com/stock/',
        '公司': 'https://finance.qq.com/company/',
        '产业': 'https://finance.qq.com/chuangye/',
        '宏观': 'https://finance.qq.com/money/',
        '国际': 'https://finance.qq.com/world/',
    }
    
    # 内容选择器
    CONTENT_SELECTOR = 'div.content-article'
    
    # 时间选择器
    TIME_SELECTOR = 'div.article-time'
    
    # 作者选择器
    AUTHOR_SELECTOR = 'div.article-author'
    
    def __init__(self, db_path=None, use_proxy=False, use_source_db=False):
        """
        初始化腾讯财经爬虫
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
        """
        self.source = "腾讯财经"
        self.name = "tencent"  # 添加name属性
        self.status = "idle"  # 添加爬虫状态属性
        self.last_run = None  # 添加上次运行时间属性
        self.next_run = None  # 添加下次运行时间属性
        self.error_count = 0  # 添加错误计数属性
        self.success_count = 0  # 添加成功计数属性
        
        super().__init__(db_manager=None, db_path=db_path, use_proxy=use_proxy, use_source_db=use_source_db)
    
    def crawl(self, days=1):
        """
        爬取腾讯财经的财经新闻
        
        Args:
            days: 爬取最近几天的新闻
        
        Returns:
            list: 爬取的新闻列表
        """
        logger.info(f"开始爬取腾讯财经新闻，爬取天数: {days}")
        
        # 清空新闻数据列表
        self.news_data = []
        
        # 计算开始日期
        start_date = datetime.now() - timedelta(days=days)
        
        # 尝试直接从首页获取新闻
        try:
            logger.info("尝试从首页获取新闻")
            home_url = "https://finance.qq.com/"
            html = self.fetch_page(home_url)
            if html:
                news_links = self.extract_news_links_from_home(html, "财经")
                logger.info(f"从首页提取到新闻链接数量: {len(news_links)}")
                
                # 爬取每个新闻详情
                for news_link in news_links:
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
                    self.save_news(news_data)
        except Exception as e:
            logger.error(f"从首页爬取新闻失败: {str(e)}")
        
        # 爬取各个分类的新闻
        for category, url in self.CATEGORY_URLS.items():
            try:
                logger.info(f"开始爬取分类: {category}, URL: {url}")
                html = self.fetch_page(url)
                if not html:
                    continue
                
                news_links = self.extract_news_links(html, category)
                logger.info(f"分类 '{category}' 找到 {len(news_links)} 个潜在新闻项")
                
                # 爬取每个新闻详情
                for news_link in news_links:
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
                    self.save_news(news_data)
            except Exception as e:
                logger.error(f"爬取分类 '{category}' 失败: {str(e)}")
        
        # 统计爬取结果
        logger.info(f"腾讯财经爬虫运行完成，耗时: {(datetime.now() - (datetime.now() - timedelta(seconds=1))).total_seconds() + 1:.2f}秒")
        logger.info(f"共爬取 {len(self.news_data)} 条新闻")
        
        # 按分类统计
        category_counts = {}
        for news in self.news_data:
            category = news['category']
            if category not in category_counts:
                category_counts[category] = 0
            category_counts[category] += 1
        
        for category, count in category_counts.items():
            logger.info(f"分类 '{category}' 爬取: {count} 条新闻")
        
        return self.news_data
    
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
            
            # 查找所有可能的新闻链接
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                # 过滤非新闻链接
                if self.is_valid_news_url(href):
                    news_links.append(href)
            
            # 去重
            news_links = list(set(news_links))
            
        except Exception as e:
            logger.error(f"从首页提取新闻链接失败: {str(e)}")
        
        return news_links
    
    def extract_news_links(self, html, category):
        """
        从分类页面提取新闻链接
        
        Args:
            html: 分类页面HTML内容
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找新闻列表
            news_list = soup.select('div.list ul li')
            if not news_list:
                logger.warning("未找到新闻列表，尝试查找所有可能的新闻链接")
                # 如果找不到特定的新闻列表，尝试提取所有可能的新闻链接
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    
                    # 过滤非新闻链接
                    if self.is_valid_news_url(href):
                        news_links.append(href)
            else:
                # 从新闻列表中提取链接
                for item in news_list:
                    a_tag = item.find('a', href=True)
                    if a_tag:
                        href = a_tag['href']
                        if self.is_valid_news_url(href):
                            news_links.append(href)
            
            # 去重
            news_links = list(set(news_links))
            
        except Exception as e:
            logger.error(f"从分类页面提取新闻链接失败: {str(e)}")
        
        return news_links
    
    def is_valid_news_url(self, url):
        """
        判断URL是否为有效的新闻链接
        
        Args:
            url: 链接URL
        
        Returns:
            bool: 是否为有效的新闻链接
        """
        # 腾讯财经新闻URL通常包含以下特征
        patterns = [
            r'https?://finance\.qq\.com/a/\d+/\d+\.htm',
            r'https?://stock\.qq\.com/a/\d+/\d+\.htm',
            r'https?://money\.qq\.com/a/\d+/\d+\.htm',
            r'https?://finance\.qq\.com/\w+/\d+/\d+\.html',
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        
        return False
    
    def crawl_news_detail(self, url, category):
        """
        爬取新闻详情
        
        Args:
            url: 新闻URL
            category: 新闻分类
        
        Returns:
            dict: 新闻数据
        """
        logger.info(f"爬取新闻详情: {url}")
        try:
            # 获取新闻页面内容
            html = self.fetch_page(url)
            if not html:
                return None
            
            # 解析HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title = ""
            title_tag = soup.select_one('title')
            if title_tag:
                title_text = title_tag.text.strip()
                # 移除网站名称
                if '_腾讯财经' in title_text:
                    title = title_text.split('_腾讯财经')[0].strip()
                elif '_腾讯网' in title_text:
                    title = title_text.split('_腾讯网')[0].strip()
                else:
                    title = title_text
            
            # 如果从title标签中提取失败，尝试从h1标签中提取
            if not title:
                title_tag = soup.select_one('h1.title')
                if not title_tag:
                    title_tag = soup.select_one('h1')
                
                if title_tag:
                    title = title_tag.text.strip()
            
            if not title:
                logger.warning(f"提取标题失败: {url}")
                return None
            
            logger.debug(f"提取到标题: {title}")
            
            # 提取内容
            content_tag = soup.select_one(self.CONTENT_SELECTOR)
            if not content_tag:
                # 尝试其他选择器
                content_tag = soup.select_one('div#ArticleContent')
                if not content_tag:
                    content_tag = soup.select_one('div.article-content')
                    if not content_tag:
                        content_tag = soup.select_one('div.content')
            
            if not content_tag:
                logger.warning(f"提取内容失败: {url}")
                return None
            
            # 清理HTML内容
            content = clean_html(str(content_tag))
            
            # 提取发布时间
            pub_time = self.extract_pub_time(soup)
            if not pub_time:
                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 提取作者
            author = self.extract_author(soup)
            
            # 提取关键词
            keywords = extract_keywords(title + ' ' + content)
            
            # 提取图片
            images = self.extract_images(content_tag)
            
            # 提取相关股票
            related_stocks = self.extract_related_stocks(soup)
            
            # 生成新闻ID
            news_id = self.generate_news_id(url, title)
            
            # 分析情感
            sentiment = self.sentiment_analyzer.analyze(title, content)
            
            # 构建新闻数据
            news_data = {
                'id': news_id,
                'title': title,
                'content': content,
                'pub_time': pub_time,
                'author': author,
                'source': self.source,
                'url': url,
                'keywords': ','.join(keywords),
                'sentiment': sentiment,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'category': category,
                'images': ','.join(images),
                'related_stocks': ','.join(related_stocks)
            }
            
            logger.debug(f"爬取新闻详情成功: {title}")
            return news_data
        except Exception as e:
            logger.error(f"爬取新闻详情失败: {url}, 错误: {str(e)}")
            return None
    
    def extract_pub_time(self, soup):
        """
        提取发布时间
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 发布时间
        """
        try:
            time_tag = soup.select_one(self.TIME_SELECTOR)
            if time_tag:
                time_text = time_tag.text.strip()
                # 提取时间字符串
                time_match = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(:\d{2})?', time_text)
                if time_match:
                    time_str = time_match.group(0)
                    # 确保时间格式统一
                    if ':' in time_str and time_str.count(':') == 1:
                        time_str += ':00'
                    return time_str
            
            # 尝试其他方式提取时间
            meta_tag = soup.select_one('meta[name="pubdate"]')
            if meta_tag and 'content' in meta_tag.attrs:
                return meta_tag['content']
            
            meta_tag = soup.select_one('meta[property="article:published_time"]')
            if meta_tag and 'content' in meta_tag.attrs:
                return meta_tag['content']
            
            logger.warning(f"未找到发布时间，使用当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.error(f"提取发布时间失败: {str(e)}")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def extract_author(self, soup):
        """
        提取作者
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            str: 作者
        """
        try:
            author_tag = soup.select_one(self.AUTHOR_SELECTOR)
            if author_tag:
                author_text = author_tag.text.strip()
                # 提取作者名
                author_match = re.search(r'作者[：:]\s*([^\s]+)', author_text)
                if author_match:
                    return author_match.group(1)
                return author_text
            
            # 尝试其他方式提取作者
            meta_tag = soup.select_one('meta[name="author"]')
            if meta_tag and 'content' in meta_tag.attrs:
                return meta_tag['content']
            
            return "腾讯财经"
        except Exception as e:
            logger.error(f"提取作者失败: {str(e)}")
            return "腾讯财经"
    
    def extract_images(self, content_tag):
        """
        提取图片
        
        Args:
            content_tag: 内容标签
        
        Returns:
            list: 图片URL列表
        """
        images = []
        try:
            for img_tag in content_tag.find_all('img', src=True):
                src = img_tag['src']
                if src.startswith('//'):
                    src = 'https:' + src
                images.append(src)
        except Exception as e:
            logger.error(f"提取图片失败: {str(e)}")
        
        return images
    
    def extract_related_stocks(self, soup):
        """
        提取相关股票
        
        Args:
            soup: BeautifulSoup对象
        
        Returns:
            list: 相关股票列表
        """
        related_stocks = []
        try:
            # 查找股票代码
            stock_pattern = r'(\d{6})[\.，,\s]+([^\s,.，,]{2,})'
            content_text = soup.get_text()
            
            for match in re.finditer(stock_pattern, content_text):
                stock_code = match.group(1)
                stock_name = match.group(2)
                related_stocks.append(f"{stock_code}:{stock_name}")
            
            # 去重
            related_stocks = list(set(related_stocks))
        except Exception as e:
            logger.error(f"提取相关股票失败: {str(e)}")
        
        return related_stocks
    
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
    
    def random_sleep(self, min_seconds=1, max_seconds=3):
        """
        随机休眠一段时间，避免被反爬
        
        Args:
            min_seconds: 最小休眠时间（秒）
            max_seconds: 最大休眠时间（秒）
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time) 