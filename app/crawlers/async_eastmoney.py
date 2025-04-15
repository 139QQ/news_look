#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 东方财富网异步爬虫
使用aiohttp库实现异步爬取，提高效率
"""

import os
import re
import sys
import time
import random
import logging
import hashlib
import asyncio
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from app.crawlers.async_crawler import AsyncCrawler
from app.utils.logger import get_crawler_logger
from app.utils.text_cleaner import clean_html, extract_keywords

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('东方财富_异步')

class AsyncEastMoneyCrawler(AsyncCrawler):
    """东方财富网异步爬虫，用于高效爬取东方财富网的财经新闻"""
    
    def __init__(self, db_manager=None, db_path=None, use_proxy=False, use_source_db=False, 
                 max_concurrency=5, timeout=30, **kwargs):
        """
        初始化东方财富网异步爬虫
        
        Args:
            db_manager: 数据库管理器对象
            db_path: 数据库路径，如果为None则使用默认路径
            use_proxy: 是否使用代理
            use_source_db: 是否使用来源专用数据库
            max_concurrency: 最大并发请求数
            timeout: 请求超时时间（秒）
            **kwargs: 其他参数
        """
        self.source = "东方财富"
        super().__init__(
            db_manager=db_manager, 
            db_path=db_path, 
            use_proxy=use_proxy, 
            use_source_db=use_source_db,
            max_concurrency=max_concurrency,
            timeout=timeout,
            **kwargs
        )
        
        # 分类URL映射
        self.category_urls = {
            '财经': ['https://finance.eastmoney.com/'],
            '股票': ['https://stock.eastmoney.com/'],
            '基金': ['https://fund.eastmoney.com/'],
            '债券': ['https://bond.eastmoney.com/'],
        }
        
        logger.info(f"东方财富网异步爬虫初始化完成，数据库路径: {self.db_path}")
    
    def get_headers(self):
        """获取HTTP请求头"""
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.eastmoney.com/'
        }
    
    async def _crawl_implementation(self, days, max_news, start_date, **kwargs):
        """
        异步爬取实现
        
        Args:
            days: 爬取的天数范围
            max_news: 最多爬取的新闻数量
            start_date: 开始日期
            **kwargs: 其他参数
        """
        category = kwargs.get('category', None)
        categories = [category] if category else list(self.category_urls.keys())
        
        for cat in categories:
            if cat not in self.category_urls:
                logger.warning(f"未知分类: {cat}")
                continue
            
            # 获取该分类下的所有URL
            cat_urls = self.category_urls.get(cat, [])
            
            # 爬取每个URL
            for url in cat_urls:
                if len(self.news_data) >= max_news:
                    logger.info(f"已达到最大新闻数量: {max_news}")
                    return
                
                # 爬取该分类页面的新闻链接
                await self._process_category_page(url, cat, max_news, start_date)
    
    async def _process_category_page(self, url, category, max_news, start_date):
        """
        处理分类页面
        
        Args:
            url: 分类页面URL
            category: 分类名称
            max_news: 最大爬取新闻数量
            start_date: 开始日期
        """
        try:
            logger.info(f"爬取分类页面: {url}, 分类: {category}")
            
            # 获取页面内容
            html = await self.async_fetch_page(url)
            if not html:
                logger.warning(f"获取分类页面失败: {url}")
                return
            
            # 提取新闻链接
            news_links = self._extract_news_links(html)
            logger.info(f"从分类 {category} 提取到 {len(news_links)} 个新闻链接")
            
            # 对链接进行去重和过滤
            news_links = list(set(news_links))
            valid_links = [link for link in news_links if self._is_valid_news_url(link)]
            logger.info(f"分类 {category} 有效链接数量: {len(valid_links)}")
            
            # 限制爬取的链接数量
            remaining = max_news - len(self.news_data)
            if remaining <= 0:
                return
            
            links_to_crawl = valid_links[:remaining]
            
            # 并发爬取新闻详情
            tasks = []
            for link in links_to_crawl:
                tasks.append(self._crawl_news_detail(link, category, start_date))
            
            # 等待所有任务完成
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"处理分类页面出错: {url}, 分类: {category}, 错误: {str(e)}")
    
    def _extract_news_links(self, html):
        """
        从HTML中提取新闻链接
        
        Args:
            html: HTML内容
            
        Returns:
            list: 新闻链接列表
        """
        if not html:
            return []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            # 提取所有链接
            for a in soup.find_all('a', href=True):
                href = a.get('href', '').strip()
                
                # 忽略空链接或JavaScript链接
                if not href or href.startswith('javascript:') or href == '#':
                    continue
                
                # 转换相对URL为绝对URL
                if not href.startswith('http'):
                    if href.startswith('//'):
                        href = 'https:' + href
                    else:
                        # 解析当前页面的基础URL
                        base_url = 'https://www.eastmoney.com'
                        href = urljoin(base_url, href)
                
                links.append(href)
            
            return links
        except Exception as e:
            logger.error(f"提取新闻链接失败: {str(e)}")
            return []
    
    def _is_valid_news_url(self, url):
        """
        判断URL是否为有效的新闻链接
        
        Args:
            url: 链接URL
            
        Returns:
            bool: 是否为有效的新闻链接
        """
        if not url:
            return False
        
        # 东方财富网新闻URL通常包含以下特征
        patterns = [
            r'https?://finance\.eastmoney\.com/a/\d+,\d+\.html',
            r'https?://finance\.eastmoney\.com/news/\d+,\d+\.html',
            r'https?://stock\.eastmoney\.com/a/\d+,\d+\.html',
            r'https?://fund\.eastmoney\.com/a/\d+,\d+\.html',
            r'https?://bond\.eastmoney\.com/a/\d+,\d+\.html',
            r'https?://forex\.eastmoney\.com/a/\d+,\d+\.html'
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        
        return False
    
    async def _crawl_news_detail(self, url, category, start_date):
        """
        异步爬取新闻详情
        
        Args:
            url: 新闻URL
            category: 新闻分类
            start_date: 开始日期
            
        Returns:
            dict: 新闻详情
        """
        try:
            logger.info(f"爬取新闻详情: {url}")
            
            # 获取页面内容
            html = await self.async_fetch_page(url)
            if not html:
                logger.warning(f"获取新闻详情失败: {url}")
                return None
            
            # 解析新闻详情
            news_data = self._parse_news_detail(html, url, category)
            
            if not news_data:
                logger.warning(f"解析新闻详情失败: {url}")
                return None
            
            # 检查新闻日期是否在指定范围内
            try:
                pub_time = news_data.get('pub_time', '')
                if pub_time:
                    news_date = datetime.strptime(pub_time.split(' ')[0], '%Y-%m-%d')
                    if news_date < start_date:
                        logger.info(f"新闻日期 {news_date} 早于起始日期 {start_date}，跳过")
                        return None
            except Exception as e:
                logger.warning(f"解析新闻日期失败: {pub_time}, 错误: {str(e)}")
            
            # 保存新闻数据
            self.news_data.append(news_data)
            
            # 保存到数据库
            self.save_news(news_data)
            
            logger.info(f"爬取新闻成功: {news_data.get('title', '未知标题')}")
            return news_data
            
        except Exception as e:
            logger.error(f"爬取新闻详情失败: {url}, 错误: {str(e)}")
            return None
    
    def _parse_news_detail(self, html, url, category):
        """
        解析新闻详情
        
        Args:
            html: HTML内容
            url: 新闻URL
            category: 新闻分类
            
        Returns:
            dict: 新闻详情
        """
        if not html:
            return None
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取标题
            title_elem = soup.find('h1')
            if not title_elem:
                logger.warning(f"未找到标题: {url}")
                return None
            
            title = title_elem.text.strip()
            
            # 提取发布时间
            time_elem = soup.select_one('.time, .time-source, .date, .newsContent .time, .Info_L')
            if time_elem:
                pub_time = time_elem.text.strip()
                # 尝试标准化时间格式
                try:
                    # 匹配常见的时间格式
                    time_pattern = r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s*?(\d{1,2}):(\d{1,2})'
                    match = re.search(time_pattern, pub_time)
                    if match:
                        year, month, day, hour, minute = match.groups()
                        pub_time = f"{year}-{month.zfill(2)}-{day.zfill(2)} {hour.zfill(2)}:{minute.zfill(2)}:00"
                    else:
                        # 如果没有匹配到时间格式，使用当前时间
                        pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                pub_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 提取作者/来源
            source_elem = soup.select_one('.source, .author, .data-source, .newsContent .source')
            if source_elem:
                author = source_elem.text.strip().replace('来源：', '')
            else:
                author = "东方财富网"
            
            # 提取内容
            content_elem = soup.select_one('#ContentBody, .newsContent, .Body, .article-body')
            if not content_elem:
                logger.warning(f"未找到内容: {url}")
                return None
            
            # 移除不需要的元素
            for selector in ['.reading', '.c_review_list', '.go_sorts', '.sorts']:
                for elem in content_elem.select(selector):
                    elem.decompose()
            
            # 提取纯文本内容
            content = clean_html(str(content_elem))
            
            # 提取图片
            images = []
            for img in content_elem.find_all('img'):
                img_url = img.get('src', '')
                if img_url:
                    # 确保是完整的URL
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif not img_url.startswith('http'):
                        img_url = urljoin('https://www.eastmoney.com', img_url)
                    
                    images.append(img_url)
            
            # 提取关键词
            keywords = extract_keywords(title + ' ' + content)
            
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
                'author': author,
                'source': self.source,
                'url': url,
                'category': category,
                'keywords': ','.join(keywords) if keywords else '',
                'images': ','.join(images) if images else '',
                'related_stocks': ','.join(related_stocks) if related_stocks else '',
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return news_data
            
        except Exception as e:
            logger.error(f"解析新闻详情失败: {url}, 错误: {str(e)}")
            return None
    
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
            # 查找可能包含股票代码的元素
            stock_elems = soup.select('.stockcontent .stockname, .stock-name, .stock_name, .stock_link')
            
            for elem in stock_elems:
                text = elem.text.strip()
                # 提取股票代码
                code_match = re.search(r'(\d{6})', text)
                if code_match:
                    code = code_match.group(1)
                    related_stocks.append(code)
            
            # 去重
            related_stocks = list(set(related_stocks))
            
        except Exception as e:
            logger.warning(f"提取相关股票失败: {str(e)}")
        
        return related_stocks
    
    def _generate_news_id(self, url, title):
        """
        生成新闻唯一ID
        
        Args:
            url: 新闻URL
            title: 新闻标题
            
        Returns:
            str: 新闻唯一ID
        """
        # 尝试从URL中提取ID
        id_match = re.search(r'/(\d+,\d+)\.html', url)
        if id_match:
            return f"eastmoney_{id_match.group(1)}"
        
        # 使用URL和标题的组合生成哈希值
        unique_string = f"{url}_{title}_{self.source}"
        return f"eastmoney_{hashlib.md5(unique_string.encode('utf-8')).hexdigest()}"
    
    def _fallback_sync_crawl(self, days, max_news, **kwargs):
        """
        同步爬取回退方案
        
        Args:
            days: 爬取的天数范围
            max_news: 最多爬取的新闻数量
            **kwargs: 其他参数
            
        Returns:
            list: 爬取的新闻列表
        """
        from app.crawlers.eastmoney import EastMoneyCrawler
        
        logger.info("回退到同步爬取方式...")
        
        # 创建同步爬虫实例
        sync_crawler = EastMoneyCrawler(
            db_manager=self.db_manager, 
            db_path=self.db_path, 
            use_proxy=self.use_proxy, 
            use_source_db=True
        )
        
        # 执行同步爬取
        category = kwargs.get('category', None)
        return sync_crawler.crawl(days=days, max_news=max_news, category=category)


if __name__ == "__main__":
    # 测试异步爬虫
    crawler = AsyncEastMoneyCrawler(use_source_db=True)
    news_list = crawler.crawl(days=1, max_news=10)
    print(f"爬取到 {len(news_list)} 条新闻")
    for news in news_list[:3]:  # 打印前3条新闻
        print(f"标题: {news['title']}")
        print(f"日期: {news['pub_time']}")
        print(f"URL: {news['url']}")
        print("-" * 50) 