#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一爬虫架构 - 声明式爬虫
允许通过配置文件定义爬虫，无需编写代码
"""

import re
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from backend.app.utils.logger import get_logger
from backend.app.crawlers.strategies.base_strategy import BaseCrawlerStrategy
from backend.app.utils.text_cleaner import clean_html, decode_html_entities

logger = get_logger('declarative_crawler')


class DeclarativeCrawlerStrategy(BaseCrawlerStrategy):
    """
    声明式爬虫策略
    通过配置定义爬虫行为，无需编写代码
    """
    
    def __init__(self, source: str, config: Dict[str, Any]):
        """
        初始化声明式爬虫策略
        
        Args:
            source: 数据源名称
            config: 配置字典
        """
        super().__init__(source)
        self.config = config
        
        # 列表页URL模板
        self.list_url_templates = config.get('list_urls', {})
        
        # 选择器
        self.selectors = config.get('selectors', {})
        
        # 正则表达式规则
        self.patterns = config.get('patterns', {})
        
        logger.info(f"声明式爬虫策略初始化完成: {source}")
    
    @property
    def categories(self) -> Dict[str, str]:
        """
        获取支持的新闻分类和对应的URL模板
        
        Returns:
            Dict[str, str]: {分类名: URL模板}
        """
        return self.list_url_templates
    
    def get_list_urls(self, category: str = None, days: int = 1) -> List[str]:
        """
        获取指定分类、指定天数范围内的列表页URL
        
        Args:
            category: 分类名称，为None时获取所有分类
            days: 获取最近几天的新闻列表
            
        Returns:
            List[str]: 列表页URL列表
        """
        urls = []
        
        # 根据配置生成URL列表
        pagination_rule = self.config.get('pagination', {})
        max_pages = min(pagination_rule.get('max_pages', 3), days + 2)
        page_param = pagination_rule.get('page_param', '{}')
        
        # 如果指定了具体分类
        if category and category in self.list_url_templates:
            template = self.list_url_templates[category]
            
            # 如果URL包含占位符，表示支持分页
            if '{}' in template:
                for page in range(1, max_pages + 1):
                    urls.append(template.format(page))
            else:
                urls.append(template)
        # 如果未指定分类，获取所有分类的列表页
        else:
            for cat, template in self.list_url_templates.items():
                if '{}' in template:
                    # 默认只取第一页
                    urls.append(template.format(1))
                else:
                    urls.append(template)
                
        return urls
    
    def parse_list_page(self, html: str, url: str) -> List[Dict[str, Any]]:
        """
        解析列表页，提取文章链接和基本信息
        
        Args:
            html: 列表页HTML内容
            url: 列表页URL
            
        Returns:
            List[Dict[str, Any]]: 文章信息列表，每个字典至少包含url字段
        """
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        
        # 获取当前分类
        category = self._get_category_from_url(url)
        
        # 获取列表项选择器
        list_item_selectors = self.selectors.get('list_items', [])
        if isinstance(list_item_selectors, str):
            list_item_selectors = [list_item_selectors]
            
        # 遍历所有选择器，尝试查找列表项
        for selector in list_item_selectors:
            items = soup.select(selector)
            if items:
                for item in items:
                    try:
                        # 获取链接
                        link_selector = self.selectors.get('list_link', 'a')
                        link = item.select_one(link_selector)
                        if not link:
                            continue
                            
                        news_url = link.get('href', '')
                        if not news_url or not self.should_crawl_url(news_url):
                            continue
                            
                        # 确保URL为绝对路径
                        if not news_url.startswith(('http://', 'https://')):
                            base_url = self.config.get('base_url', '')
                            news_url = urljoin(base_url or url, news_url)
                        
                        # 获取标题
                        title_selector = self.selectors.get('list_title', '')
                        title_element = item.select_one(title_selector) if title_selector else link
                        title = title_element.text.strip() if title_element else link.get('title', '').strip()
                        
                        # 获取发布时间
                        time_selector = self.selectors.get('list_time', '')
                        time_element = item.select_one(time_selector) if time_selector else None
                        pub_time = time_element.text.strip() if time_element else None
                        
                        # 基本信息
                        article_info = {
                            'url': news_url,
                            'title': title,
                            'source': self.source,
                            'category': category
                        }
                        
                        if pub_time:
                            article_info['pub_time'] = pub_time
                            
                        articles.append(article_info)
                    except Exception as e:
                        logger.error(f"解析列表项出错: {str(e)}")
                        
                # 如果找到了文章，不再尝试其他选择器
                if articles:
                    break
        
        # 如果没有找到文章，尝试直接查找所有链接
        if not articles:
            # 获取URL规则
            url_pattern = self.patterns.get('article_url', '')
            if url_pattern:
                for link in soup.select('a[href]'):
                    try:
                        news_url = link.get('href', '')
                        
                        # 检查URL是否匹配规则
                        if not news_url or not re.search(url_pattern, news_url):
                            continue
                            
                        # 确保URL为绝对路径
                        if not news_url.startswith(('http://', 'https://')):
                            base_url = self.config.get('base_url', '')
                            news_url = urljoin(base_url or url, news_url)
                        
                        title = link.text.strip() or link.get('title', '').strip()
                        if not title:
                            continue
                            
                        # 基本信息
                        article_info = {
                            'url': news_url,
                            'title': title,
                            'source': self.source,
                            'category': category
                        }
                        
                        articles.append(article_info)
                    except Exception as e:
                        logger.error(f"解析链接出错: {str(e)}")
                    
        return articles
    
    def parse_detail_page(self, html: str, url: str, basic_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解析详情页，提取文章完整内容
        
        Args:
            html: 详情页HTML内容
            url: 详情页URL
            basic_info: 从列表页提取的基本信息
            
        Returns:
            Dict[str, Any]: 完整的文章信息字典
        """
        if not html:
            return {}
            
        # 初始化基本信息
        article = basic_info.copy() if basic_info else {'url': url, 'source': self.source}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取标题
        if 'title' not in article or not article['title']:
            title_selector = self.selectors.get('title', '')
            if title_selector:
                title_element = soup.select_one(title_selector)
                if title_element:
                    article['title'] = title_element.text.strip()
                    
        # 提取发布时间
        if 'pub_time' not in article or not article['pub_time']:
            time_selector = self.selectors.get('publish_time', '')
            if time_selector:
                time_element = soup.select_one(time_selector)
                if time_element:
                    article['pub_time'] = time_element.text.strip()
                    
        # 提取作者/来源
        if 'author' not in article or not article['author']:
            author_selector = self.selectors.get('author', '')
            if author_selector:
                author_element = soup.select_one(author_selector)
                if author_element:
                    author_text = author_element.text.strip()
                    # 处理"来源:"前缀
                    if '来源:' in author_text or '来源：' in author_text:
                        author_text = re.sub(r'来源[：:]\s*', '', author_text)
                    article['author'] = author_text
                    
        # 提取正文内容
        content_selector = self.selectors.get('content', '')
        if content_selector:
            content_element = soup.select_one(content_selector)
            if content_element:
                # 移除可能的广告元素
                ad_selectors = self.selectors.get('ad_elements', [])
                for ad_selector in ad_selectors:
                    for ad in content_element.select(ad_selector):
                        ad.decompose()
                        
                # 获取HTML内容和纯文本
                article['content_html'] = str(content_element)
                article['content'] = content_element.get_text('\n', strip=True)
                
        # 提取分类，如果basic_info中没有
        if 'category' not in article or not article['category']:
            article['category'] = self._get_category_from_url(url)
            
        # 提取关键词
        keywords_selector = self.selectors.get('keywords', 'meta[name="keywords"]')
        keywords_element = soup.select_one(keywords_selector)
        if keywords_element and 'content' in keywords_element.attrs:
            article['keywords'] = keywords_element['content']
            
        # 提取图片
        if 'content_html' in article:
            img_soup = BeautifulSoup(article['content_html'], 'html.parser')
            images = []
            
            # 图片选择器
            img_selector = self.selectors.get('images', 'img')
            
            for img in img_soup.select(img_selector):
                img_url = img.get('src') or img.get('data-src', '')
                if not img_url:
                    continue
                    
                # 过滤广告图片
                ad_img_pattern = self.patterns.get('ad_image', '')
                if ad_img_pattern and re.search(ad_img_pattern, img_url):
                    continue
                    
                # 确保URL为绝对路径
                if not img_url.startswith(('http://', 'https://')):
                    base_url = self.config.get('base_url', '')
                    img_url = urljoin(base_url or url, img_url)
                    
                images.append(img_url)
                
            if images:
                article['images'] = json.dumps(images)
                
        # 添加爬取时间
        article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return article
    
    def _get_category_from_url(self, url: str) -> str:
        """
        从URL中提取分类
        
        Args:
            url: 文章URL
            
        Returns:
            str: 分类名称
        """
        # 使用配置中的URL规则判断分类
        category_patterns = self.config.get('category_patterns', {})
        for pattern, category in category_patterns.items():
            if re.search(pattern, url):
                return category
                
        # 查看是否匹配列表URL模板
        for category, template in self.list_url_templates.items():
            base_template = template.split('{}')[0] if '{}' in template else template
            if base_template in url:
                return category
                
        # 使用默认分类
        return self.config.get('default_category', '财经') 