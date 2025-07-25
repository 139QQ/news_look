#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 网易财经爬虫
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

from backend.app.crawlers.base import BaseCrawler
from backend.app.utils.logger import get_crawler_logger
from backend.app.utils.text_cleaner import clean_html, extract_keywords
from backend.app.db.SQLiteManager import SQLiteManager
from backend.app.utils.ad_filter import AdFilter  # 导入广告过滤器模块
from backend.app.utils.image_detector import ImageDetector  # 导入图像识别模块

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('netease')

class NeteaseCrawler(BaseCrawler):
    """网易财经爬虫，用于爬取网易财经的财经新闻"""
    
    # 新闻分类URL
    CATEGORY_URLS = {
        '财经': 'https://money.163.com/finance/',
        '股票': 'https://money.163.com/stock/',
        '理财': 'https://money.163.com/licai/',
        '基金': 'https://money.163.com/fund/',
        '宏观': 'https://money.163.com/macro/',
        '国际': 'https://money.163.com/world/',
    }
    
    # 内容选择器
    CONTENT_SELECTOR = 'div.post_body'
    
    # 时间选择器
    TIME_SELECTOR = 'div.post_time_source'
    
    # 作者选择器
    AUTHOR_SELECTOR = 'div.post_time_source span'
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, **kwargs):
        """
        初始化网易财经爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
        """
        self.source = "网易财经"
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, use_source_db=use_source_db, **kwargs)
        
        # 初始化广告过滤器
        self.ad_filter = AdFilter(source_name=self.source)
        # 初始化图像检测器
        self.image_detector = ImageDetector(cache_dir='./image_cache')
        
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
        
        logger.info(f"网易财经爬虫初始化完成，数据库路径: {self.db_path}")
    
    def crawl(self, days=1, max_news=10):
        """
        爬取网易财经的财经新闻
        
        Args:
            days: 爬取最近几天的新闻
            max_news: 最大新闻数量
        
        Returns:
            list: 爬取的新闻列表
        """
        logger.info(f"开始爬取网易财经新闻，爬取天数: {days}")
        
        # 清空新闻数据列表
        self.news_data = []
        
        # 重置广告过滤计数 - 已禁用URL广告过滤
        # self.ad_filter.reset_filter_count()
        # 重置广告图片过滤计数 - 已禁用图片过滤
        # self.image_detector.reset_ad_count()
        
        # 计算开始日期
        start_date = datetime.now() - timedelta(days=days)
        
        # 尝试直接从首页获取新闻
        try:
            logger.info("尝试从首页获取新闻")
            home_url = "https://money.163.com/"
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
                    self.save_news_to_db(news_data)
                    self.news_data.append(news_data)
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
                        logger.warning(f"解析新闻日期失败: {news_data['pub_time']}")
                    
                    # 保存新闻数据
                    self.save_news_to_db(news_data)
                    self.news_data.append(news_data)
                    
                # 如果已经获取足够数量的新闻，停止爬取
                if len(self.news_data) >= max_news:
                    logger.info(f"已经爬取 {len(self.news_data)} 条新闻，达到最大数量 {max_news}")
                    break
                
                # 随机休眠，避免被反爬
                self.random_sleep(2, 5)
            except Exception as e:
                logger.error(f"爬取分类 '{category}' 失败: {str(e)}")
        
        logger.info(f"网易财经爬取完成，共爬取新闻: {len(self.news_data)} 条")
        return self.news_data
    
    def extract_news_links_from_home(self, html, category):
        """
        从首页提取新闻链接
        
        Args:
            html: 页面HTML
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取所有链接
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
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
            html: 页面HTML
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 根据分类不同，可能需要不同的选择器
            news_list = soup.select('ul.news_list li')
            if not news_list:
                news_list = soup.select('div.data_row')
            if not news_list:
                news_list = soup.select('div.news_item')
            
            if not news_list:
                # 如果没有找到特定的新闻列表，尝试提取所有链接
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
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
        if not url:
            return False
            
        # 检查URL是否为广告 - 已移除广告过滤
        # if self.ad_filter.is_ad_url(url):
        #     logger.info(f"过滤广告URL: {url}")
        #     return False
            
        # 网易财经新闻URL通常包含以下特征
        patterns = [
            r'https?://money\.163\.com/\d+/\d+/\d+/\w+\.html',
            r'https?://money\.163\.com/\w+/\d+/\d+/\d+/\w+\.html',
            r'https?://www\.163\.com/money/article/\w+\.html',
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
            # 判断URL是否为广告 - 已移除广告过滤
            # if self.ad_filter.is_ad_url(url):
            #     logger.info(f"跳过广告URL: {url}")
            #     return None
                
            html = self.fetch_page(url)
            if not html:
                logger.warning(f"无法获取页面内容: {url}")
                return None
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title_tag = soup.find('h1')
            if not title_tag:
                logger.warning(f"无法找到标题标签: {url}")
                return None
                
            title = title_tag.get_text(strip=True)
            if not title:
                logger.warning(f"标题为空: {url}")
                return None
                
            # 提取内容
            content_div = soup.select_one(self.CONTENT_SELECTOR)
            if not content_div:
                logger.warning(f"无法找到内容选择器: {url}")
                return None
                
            # 保存原始HTML以便处理图片
            content_html = str(content_div)
            
            # 清理HTML
            content = clean_html(str(content_div))
            
            # 判断内容是否为广告
            if self.ad_filter.is_ad_content(content, title=title, category=category):
                logger.info(f"跳过广告内容: {title}")
                return None
            
            # 提取发布时间
            pub_time = self.extract_pub_time(soup)
            if not pub_time:
                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 提取作者
            author = self.extract_author(soup)
            
            # 检测和过滤广告图片 - 已移除图片过滤
            image_content_soup = BeautifulSoup(content_html, 'html.parser')
            image_urls = []
            
            for img in image_content_soup.find_all('img'):
                img_url = img.get('src')
                if img_url:
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                        
                    # 不再过滤广告图片，保留所有图片
                    # if self.image_detector.is_ad_image(img_url, context={'category': category}):
                    #     logger.info(f"过滤广告图片: {img_url}")
                    #     img.decompose()  # 从HTML中移除广告图片
                    #     ad_images_removed = True
                    # else:
                    #     image_urls.append(img_url)
                    image_urls.append(img_url)
            
            # 提取关键词
            keywords = extract_keywords(title + ' ' + content)
            
            # 提取相关股票
            related_stocks = self.extract_related_stocks(soup)
            
            # 生成新闻ID
            news_id = self.generate_news_id(url, title)
            
            # 分析情感
            sentiment = 0
            if hasattr(self, 'sentiment_analyzer'):
                try:
                    sentiment = self.sentiment_analyzer.analyze(title, content)
                except Exception as e:
                    logger.error(f"情感分析失败: {str(e)}")
            
            # 构建新闻数据
            news_data = {
                'id': news_id,
                'title': title,
                'content': content,
                'content_html': content_html,
                'pub_time': pub_time,
                'author': author,
                'source': self.source,
                'url': url,
                'keywords': ','.join(keywords) if keywords else '',
                'sentiment': sentiment,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'category': category,
                'images': ','.join(image_urls),
                'related_stocks': ','.join(related_stocks) if related_stocks else ''
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
            meta_tag = soup.select_one('meta[name="publishdate"]')
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
                author_match = re.search(r'来源[：:]\s*([^\s]+)', author_text)
                if author_match:
                    return author_match.group(1)
                return author_text
            
            # 尝试其他方式提取作者
            meta_tag = soup.select_one('meta[name="author"]')
            if meta_tag and 'content' in meta_tag.attrs:
                return meta_tag['content']
            
            return "网易财经"
        except Exception as e:
            logger.error(f"提取作者失败: {str(e)}")
            return "网易财经"
    
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
        stocks = []
        try:
            stock_tags = soup.select('a.stock_code')
            for tag in stock_tags:
                stock_code = tag.text.strip()
                if stock_code and re.match(r'^\d{6}$', stock_code):
                    stocks.append(stock_code)
        except Exception as e:
            logger.error(f"提取相关股票失败: {str(e)}")
        
        return stocks
    
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
        combined = url + title
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def random_sleep(self, min_seconds=1, max_seconds=3):
        """
        随机休眠一段时间，避免被反爬
        
        Args:
            min_seconds: 最小休眠时间（秒）
            max_seconds: 最大休眠时间（秒）
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        logger.debug(f"随机休眠 {sleep_time:.2f} 秒")
        time.sleep(sleep_time)
    
    def save_news_to_db(self, news):
        """
        保存新闻到数据库
        
        Args:
            news: 新闻数据
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if hasattr(self, 'sqlite_manager') and self.sqlite_manager:
                return self.sqlite_manager.save_news(news)
            return super().save_news(news)
        except Exception as e:
            logger.error(f"保存新闻到数据库失败: {str(e)}")
            return False


if __name__ == "__main__":
    # 测试爬虫
    crawler = NeteaseCrawler(use_proxy=False, use_source_db=True)
    news_list = crawler.crawl(days=1, max_news=5)
    print(f"爬取到新闻数量: {len(news_list)}")
    for news in news_list:
        print(f"标题: {news['title']}")
        print(f"发布时间: {news['pub_time']}")
        print(f"来源: {news['source']}")
        print("-" * 50) 