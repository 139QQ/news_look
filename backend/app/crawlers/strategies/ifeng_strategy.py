#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 凤凰财经爬虫策略
专门针对凤凰财经网站的爬取策略实现
"""

import re
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from backend.app.crawlers.strategies.base_strategy import BaseCrawlerStrategy
from backend.app.utils.text_cleaner import clean_html, decode_html_entities

class IfengStrategy(BaseCrawlerStrategy):
    """凤凰财经网站爬虫策略"""
    
    def __init__(self, source="凤凰财经"):
        """初始化策略"""
        super().__init__(source)
        
        # 列表页URL模板
        self.list_url_templates = {
            "首页": "https://finance.ifeng.com/",
            "财经": "https://finance.ifeng.com/shanklist/{}/1/",
            "股票": "https://finance.ifeng.com/stock/",
            "基金": "https://finance.ifeng.com/fund/",
            "理财": "https://finance.ifeng.com/money/",
            "宏观": "https://finance.ifeng.com/macro/",
            "国际": "https://finance.ifeng.com/world/",
            "公司": "https://finance.ifeng.com/company/special/"
        }
        
        # 列表页规则
        self.list_selectors = {
            "首页": "div.box-list.mg-t30 ul li",
            "财经": "div.news-stream-basic-news-list ul li",
            "股票": "ul.news-stream-newsStream-newsStream-list-item li",
            "基金": "div.column-content a",
            "理财": "div.article-list",
            "宏观": "ul.list01 li",
            "国际": "div.news-stream-basic-news-list",
            "公司": "div.content-list-box div.content-list-item"
        }
    
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
        
        # 如果指定了具体分类
        if category and category in self.list_url_templates:
            if category == "财经":
                # 凤凰财经特殊格式
                for page in range(1, min(days + 1, 4)):  # 最多取3页
                    urls.append(self.list_url_templates[category].format(page))
            else:
                urls.append(self.list_url_templates[category])
        # 如果未指定分类，获取所有分类的列表页
        else:
            for cat, url in self.list_url_templates.items():
                if cat == "财经":
                    urls.append(url.format(1))  # 只取第一页
                else:
                    urls.append(url)
                
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
        
        # 根据不同的页面格式选择不同的解析方法
        # 策略1: 提取列表项
        if category in self.list_selectors:
            selector = self.list_selectors[category]
            items = soup.select(selector)
            
            for item in items:
                try:
                    # 查找链接
                    link = item.select_one('a')
                    if not link:
                        # 如果当前元素没有链接，尝试本身就是链接
                        if item.name == 'a':
                            link = item
                        else:
                            continue
                            
                    news_url = link.get('href', '')
                    
                    # 检查URL
                    if not news_url or not self.should_crawl_url(news_url):
                        continue
                        
                    # 确保URL为绝对路径
                    if not news_url.startswith(('http://', 'https://')):
                        news_url = urljoin('https://finance.ifeng.com', news_url)
                    
                    # 获取标题
                    title_element = link.select_one('h3') or link
                    title = title_element.text.strip()
                    if not title:
                        title = link.get('title', '').strip()
                    
                    # 获取发布时间
                    time_element = item.select_one('.time, .date')
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
                    print(f"解析凤凰财经列表项时出错: {str(e)}")
        
        # 如果没有找到文章，尝试其他方式解析
        if not articles:
            # 策略2: 提取所有链接，检查URL模式
            for link in soup.select('a[href]'):
                try:
                    news_url = link.get('href', '')
                    
                    # 只提取文章链接
                    if not news_url or not re.search(r'\/c\/\d{1,20}\.shtml', news_url):
                        continue
                        
                    # 确保URL为绝对路径
                    if not news_url.startswith(('http://', 'https://')):
                        news_url = urljoin('https://finance.ifeng.com', news_url)
                    
                    # 获取标题
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
                    print(f"解析凤凰财经链接时出错: {str(e)}")
                    
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
            title_element = soup.select_one('h1.article-title, h1.topic-title, h1.entry-title')
            if title_element:
                article['title'] = title_element.text.strip()
                
        # 提取发布时间
        if 'pub_time' not in article or not article['pub_time']:
            time_element = soup.select_one('span.ss01, div.timeBref, span.time, div.time, time.publish-time')
            if time_element:
                article['pub_time'] = time_element.text.strip()
                
        # 提取作者/来源
        if 'author' not in article or not article['author']:
            author_element = soup.select_one('span.ss03, div.source, .source-name, span.author')
            if author_element:
                article['author'] = author_element.text.strip()
                
        # 提取正文内容
        content_element = soup.select_one('#main_content, div.article-content, div.main-content, div.entry-content')
        if content_element:
            # 去除内部可能的广告元素
            for ad in content_element.select('div.adv, div.textlink, div.relate_bottom, div.wph-sdk-wrapper'):
                ad.decompose()
                
            # 获取HTML内容和纯文本
            article['content_html'] = str(content_element)
            article['content'] = content_element.get_text('\n', strip=True)
            
        # 提取分类，如果basic_info中没有
        if 'category' not in article or not article['category']:
            article['category'] = self._get_category_from_url(url)
            
        # 提取关键词
        keywords_element = soup.select_one('meta[name="keywords"]')
        if keywords_element and 'content' in keywords_element.attrs:
            article['keywords'] = keywords_element['content']
            
        # 提取图片
        if 'content_html' in article:
            img_soup = BeautifulSoup(article['content_html'], 'html.parser')
            images = []
            for img in img_soup.select('img'):
                if img.get('src'):
                    img_url = img['src']
                    # 过滤广告图片
                    if 'adv_' in img_url or '/adv/' in img_url:
                        continue
                    if not img_url.startswith(('http://', 'https://')):
                        img_url = urljoin(url, img_url)
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
        # 凤凰财经的URL规律
        if '/stock/' in url:
            return '股票'
        elif '/fund/' in url:
            return '基金'
        elif '/money/' in url:
            return '理财'
        elif '/macro/' in url:
            return '宏观'
        elif '/world/' in url:
            return '国际'
        elif '/company/' in url:
            return '公司'
            
        # 列表URL的分类判断
        for category, template in self.list_url_templates.items():
            if template.split('{}')[0] in url:
                return category
                
        # 默认分类
        return '财经' 