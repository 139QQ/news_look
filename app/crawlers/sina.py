#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 新浪财经爬虫
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
import logging
from urllib.parse import urlparse

from app.crawlers.base import BaseCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords, decode_unicode_escape, decode_html_entities, decode_url_encoded

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('sina')

class SinaCrawler(BaseCrawler):
    """新浪财经爬虫，用于爬取新浪财经的财经新闻"""
    
    # 新闻分类URL
    CATEGORY_URLS = {
        '财经': 'https://finance.sina.com.cn/roll/index.d.html?cid=56592&page={}',
        '股票': 'https://finance.sina.com.cn/roll/index.d.html?cid=56588&page={}',
        '公司': 'https://finance.sina.com.cn/roll/index.d.html?cid=57526&page={}',
        '产业': 'https://finance.sina.com.cn/roll/index.d.html?cid=57522&page={}',
        '宏观': 'https://finance.sina.com.cn/roll/index.d.html?cid=57524&page={}',
        '国际': 'https://finance.sina.com.cn/roll/index.d.html?cid=56590&page={}',
    }
    
    # 内容选择器
    CONTENT_SELECTOR = 'div.article-content-left'
    
    # 时间选择器
    TIME_SELECTOR = 'span.date'
    
    # 作者选择器
    AUTHOR_SELECTOR = 'span.source'
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False):
        """
        初始化新浪财经爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
        """
        self.source = "新浪财经"
        self.name = "sina"  # 添加name属性
        self.status = "idle"  # 添加爬虫状态属性
        self.last_run = None  # 添加上次运行时间属性
        self.next_run = None  # 添加下次运行时间属性
        self.error_count = 0  # 添加错误计数属性
        self.success_count = 0  # 添加成功计数属性
        
        # 新浪财经特有的请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://finance.sina.com.cn/'
        }
        
        super().__init__(db_manager=db_manager, db_path=db_path, use_proxy=use_proxy, use_source_db=use_source_db)
    
    def fetch_page(self, url, params=None, headers=None, max_retries=None, timeout=None):
        """
        重写获取页面内容方法，处理新浪财经特有的编码问题
        
        Args:
            url: 页面URL
            params: 请求参数
            headers: 自定义请求头
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
            
        Returns:
            页面内容或None
        """
        # 调用父类的fetch_page方法获取响应
        response = super().fetch_page(url, params, headers, max_retries, timeout)
        
        if response is None:
            return None
        
        # 解决新浪财经的编码问题
        try:
            # 尝试检测编码
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
            
            # 应用额外的解码处理
            content = decode_html_entities(content)
            content = decode_unicode_escape(content)
            content = decode_url_encoded(content)
            
            return content
        except Exception as e:
            logger.error(f"处理页面编码时出错: {url}, 错误: {str(e)}")
            return response.text  # 出错时返回原始文本
    
    def crawl(self, days=1):
        """
        爬取新浪财经的财经新闻
        
        Args:
            days: 爬取最近几天的新闻
        
        Returns:
            list: 爬取的新闻列表
        """
        logger.info(f"开始爬取新浪财经新闻，爬取天数: {days}")
        
        # 清空新闻数据列表
        self.news_data = []
        
        # 计算开始日期
        start_date = datetime.now() - timedelta(days=days)
        
        # 尝试直接从首页获取新闻
        try:
            logger.info("尝试从首页获取新闻")
            home_url = "https://finance.sina.com.cn/"
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
            logger.error(f"从首页获取新闻失败: {str(e)}")
        
        # 如果从首页获取的新闻不足，再尝试从分类页获取
        if len(self.news_data) < 10:
            # 爬取每个分类的新闻
            for category, url_template in self.CATEGORY_URLS.items():
                logger.info(f"爬取分类: {category}")
                
                # 爬取前5页
                for page in range(1, 6):
                    url = url_template.format(page)
                    logger.info(f"爬取页面: {url}")
                    
                    # 获取页面内容
                    html = self.fetch_page(url)
                    if not html:
                        logger.warning(f"获取页面失败: {url}")
                        continue
                    
                    # 解析页面，提取新闻链接
                    news_links = self.extract_news_links(html, category)
                    logger.info(f"提取到新闻链接数量: {len(news_links)}")
                    
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
                    
                    # 随机休眠，避免被反爬
                    self.random_sleep(2, 5)
        
        logger.info(f"新浪财经爬取完成，共爬取新闻: {len(self.news_data)} 条")
        return self.news_data
    
    def extract_news_links(self, html, category):
        """
        从页面中提取新闻链接
        
        Args:
            html: 页面内容
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找新闻列表
            news_list = soup.select('ul.list_009 li')
            
            for news_item in news_list:
                # 提取链接
                link_tag = news_item.select_one('a')
                if not link_tag:
                    continue
                
                link = link_tag.get('href')
                if not link:
                    continue
                
                # 验证链接
                if not self.validate_url(link):
                    continue
                
                # 添加到链接列表
                news_links.append(link)
        except Exception as e:
            logger.error(f"提取新闻链接失败: {category}, 错误: {str(e)}")
        
        return news_links
    
    def validate_url(self, url):
        """
        验证URL是否有效
        
        Args:
            url: URL
        
        Returns:
            bool: 是否有效
        """
        # 检查URL是否为空
        if not url:
            return False
        
        # 检查URL是否为绝对URL
        if not url.startswith('http'):
            return False
        
        # 检查URL是否为新浪财经的URL
        if 'sina.com.cn' not in url:
            return False
        
        return True
    
    def crawl_news_detail(self, url, category):
        """
        爬取新闻详情
        
        Args:
            url: 新闻URL
            category: 新闻分类
        
        Returns:
            dict: 新闻数据
        """
        try:
            logger.info(f"爬取新闻详情: {url}")
            
            # 获取页面内容
            html = self.fetch_page(url)
            if not html:
                logger.warning(f"获取新闻详情页面失败: {url}")
                return None
            
            # 解析页面
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title_elem = soup.select_one('h1.main-title')
            if not title_elem:
                title_elem = soup.select_one('h1.title')
            
            if not title_elem:
                logger.warning(f"未找到标题: {url}")
                return None
            
            title = title_elem.text.strip()
            # 确保标题没有乱码
            title = decode_html_entities(title)
            title = decode_unicode_escape(title)
            title = decode_url_encoded(title)
            
            if not title:
                logger.warning(f"标题为空: {url}")
                return None
            
            # 提取发布时间
            pub_time = self.extract_pub_time(soup)
            
            # 提取作者/来源
            author = self.extract_author(soup)
            
            # 尝试从URL推断来源
            if not author or author == "未知":
                domain = urlparse(url).netloc
                if "finance.sina.com.cn" in domain:
                    author = "新浪财经"
                elif "sina.com.cn" in domain:
                    author = "新浪新闻"
                
            # 提取正文
            content_tag = soup.select_one(self.CONTENT_SELECTOR)
            if not content_tag:
                # 尝试其他可能的选择器
                content_tag = soup.select_one('div.article')
                if not content_tag:
                    content_tag = soup.select_one('#artibody')
            
            if not content_tag:
                logger.warning(f"未找到正文: {url}")
                return None
            
            # 提取图片
            images = self.extract_images(content_tag)
            
            # 提取正文内容
            for script in content_tag.find_all('script'):
                script.decompose()
            for style in content_tag.find_all('style'):
                style.decompose()
            
            # 移除广告和无关元素
            for div in content_tag.find_all('div', class_=lambda c: c and ('recommend' in c.lower() or 'footer' in c.lower() or 'ad' in c.lower() or 'bottom' in c.lower())):
                div.decompose()
            
            content = content_tag.get_text('\n').strip()
            # 确保内容没有乱码
            content = decode_html_entities(content)
            content = decode_unicode_escape(content)
            content = decode_url_encoded(content)
            
            # 提取关键词
            keywords = extract_keywords(content)
            
            # 提取相关股票
            related_stocks = self.extract_related_stocks(soup)
            
            # 生成新闻ID
            news_id = self.generate_news_id(url, title)
            
            # 构建新闻数据
            news_data = {
                'news_id': news_id,
                'title': title,
                'content': content,
                'pub_time': pub_time,
                'source': self.source,
                'author': author,
                'category': category,
                'url': url,
                'keywords': ','.join(keywords),
                'images': ','.join(images),
                'related_stocks': ','.join(related_stocks),
                'sentiment': 0,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 分析情感
            if content:
                try:
                    sentiment = self.sentiment_analyzer.analyze(title, content)
                    news_data['sentiment'] = sentiment
                except Exception as e:
                    logger.error(f"情感分析失败: {str(e)}")
            
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
            if not time_tag:
                return None
            
            time_text = time_tag.text.strip()
            
            # 使用正则表达式提取时间
            time_pattern = r'(\d{4}年\d{2}月\d{2}日\s\d{2}:\d{2})'
            match = re.search(time_pattern, time_text)
            if match:
                # 将中文日期格式转换为标准格式
                date_str = match.group(1)
                date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                return date_str + ':00'
            
            # 如果没有匹配到完整时间，尝试匹配日期
            date_pattern = r'(\d{4}年\d{2}月\d{2}日)'
            match = re.search(date_pattern, time_text)
            if match:
                # 将中文日期格式转换为标准格式
                date_str = match.group(1)
                date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                return date_str + ' 00:00:00'
            
            return None
        except Exception as e:
            logger.warning(f"提取发布时间失败: {str(e)}")
            return None
    
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
            if not author_tag:
                return "新浪财经"
            
            author_text = author_tag.text.strip()
            
            # 使用正则表达式提取作者
            author_pattern = r'来源：(.*?)$'
            match = re.search(author_pattern, author_text)
            if match:
                return match.group(1).strip()
            
            return author_text
        except Exception as e:
            logger.warning(f"提取作者失败: {str(e)}")
            return "新浪财经"
    
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
            img_tags = content_tag.select('img')
            for img_tag in img_tags:
                src = img_tag.get('src')
                if src and src.startswith('http'):
                    images.append(src)
        except Exception as e:
            logger.warning(f"提取图片失败: {str(e)}")
        
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
            # 查找相关股票标签
            stock_tags = soup.select('div.stock-info a')
            for stock_tag in stock_tags:
                stock_text = stock_tag.text.strip()
                if stock_text:
                    related_stocks.append(stock_text)
        except Exception as e:
            logger.warning(f"提取相关股票失败: {str(e)}")
        
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
        # 使用URL和标题生成唯一ID
        text = url + title
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def extract_news_links_from_home(self, html, category):
        """
        从首页提取新闻链接
        
        Args:
            html: 页面内容
            category: 新闻分类
        
        Returns:
            list: 新闻链接列表
        """
        news_links = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找新闻链接
            news_items = soup.select('a[href*="finance.sina.com.cn"]')
            
            for news_item in news_items:
                link = news_item.get('href')
                if not link:
                    continue
                
                # 验证链接，确保是新闻页面而不是分类页面
                if not self.validate_url(link):
                    continue
                
                # 确保链接包含数字（新闻ID），过滤掉分类页面
                if not any(c.isdigit() for c in link):
                    continue
                
                # 添加到链接列表，避免重复
                if link not in news_links:
                    news_links.append(link)
        except Exception as e:
            logger.error(f"从首页提取新闻链接失败: {category}, 错误: {str(e)}")
        
        return news_links


if __name__ == "__main__":
    # 测试爬虫
    crawler = SinaCrawler(use_proxy=False, use_source_db=True)
    news_list = crawler.crawl(days=1)
    print(f"爬取到新闻数量: {len(news_list)}")
