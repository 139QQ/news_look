#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 网易财经爬虫策略
专门针对网易财经网站的爬取策略实现
"""

import re
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from backend.app.crawlers.strategies.base_strategy import BaseCrawlerStrategy
from backend.app.utils.text_cleaner import clean_html, decode_html_entities, decode_unicode_escape

class NeteaseStrategy(BaseCrawlerStrategy):
    """网易财经网站爬虫策略"""
    
    def __init__(self, source="网易财经"):
        """初始化策略"""
        super().__init__(source)
        
        # 列表页URL模板
        self.list_url_templates = {
            "首页": "https://money.163.com/",
            "股票": "https://money.163.com/stock/",
            "理财": "https://money.163.com/special/00251LJV/news3_json.js?page={}",
            "基金": "https://money.163.com/fund/",
            "债券": "https://money.163.com/special/00251LJV/news5_json.js?page={}",
            "外汇": "https://money.163.com/special/00251LJV/news6_json.js?page={}",
            "期货": "https://money.163.com/special/00251LJV/news7_json.js?page={}",
            "产经": "https://money.163.com/special/00251LJV/news8_json.js?page={}"
        }
        
        # 设置分类字典，父类属性
        self.categories = self.list_url_templates.copy()
    
    def get_list_page_urls(self, days: int = 1, category: Optional[str] = None) -> List[str]:
        """
        获取指定分类、指定天数范围内的列表页URL
        
        Args:
            days: 获取最近几天的新闻列表
            category: 分类名称，为None时获取所有分类
            
        Returns:
            List[str]: 列表页URL列表
        """
        urls = []
        
        # 根据天数确定页数（每页约20条，一天约60条）
        page_count = max(1, min(3, days))
        
        # 如果指定了具体分类
        if category and category in self.list_url_templates:
            template = self.list_url_templates[category]
            # 添加页面
            for page in range(1, page_count + 1):
                urls.append(template.format(page))
        # 如果未指定分类，获取所有分类的列表页
        else:
            for cat, template in self.list_url_templates.items():
                # 每个分类取第一页
                urls.append(template.format(1))
                
        return urls
    
    def parse_list_page(self, html: str, url: str) -> List[str]:
        """
        解析列表页，提取文章链接
        
        Args:
            html: 列表页HTML内容或JSON字符串
            url: 列表页URL
            
        Returns:
            List[str]: 文章URL列表
        """
        if not html:
            return []
            
        article_urls = []
        
        # 网易财经的列表页是jsonp格式的
        # 尝试提取json部分
        json_match = re.search(r'var data=(\[.*?\]);', html)
        if json_match:
            try:
                # 解析json
                json_str = json_match.group(1)
                json_str = decode_unicode_escape(json_str)
                news_list = json.loads(json_str)
                
                for news in news_list:
                    try:
                        news_url = news.get('docurl', '')
                        # 确保URL有效
                        if news_url and self.should_crawl_url(news_url):
                            article_urls.append(news_url)
                    except Exception as e:
                        print(f"解析列表项时出错: {str(e)}")
                        
            except Exception as e:
                print(f"解析JSON时出错: {str(e)}")
        
        # 如果JSON解析失败，尝试使用HTML解析
        if not article_urls:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 尝试查找列表项
            for item in soup.select('.list_item, .news_item'):
                try:
                    link = item.select_one('h2 a, .title a')
                    if not link:
                        continue
                        
                    news_url = link.get('href', '')
                    if news_url and self.should_crawl_url(news_url):
                        article_urls.append(news_url)
                except Exception as e:
                    print(f"HTML解析列表项时出错: {str(e)}")
                    
        return article_urls
    
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
            title_element = soup.select_one('h1.post_title, h1.title')
            if title_element:
                article['title'] = title_element.text.strip()
        
        # 提取发布时间
        time_element = soup.select_one('.post_time, .post_info time, .pub_time')
        if time_element:
            article['pub_time'] = time_element.text.strip()
            
        # 提取作者/来源
        source_element = soup.select_one('.post_source, .source')
        if source_element:
            author_text = source_element.text.strip()
            # 提取来源中的作者信息
            if '来源:' in author_text or '来源：' in author_text:
                author_text = re.sub(r'来源[：:]\s*', '', author_text)
            article['author'] = author_text
            
        # 提取正文内容
        content_element = soup.select_one('#endText, .post_body, .post_text')
        if content_element:
            # 移除可能的广告和无用元素
            for ad in content_element.select('.gg200x300, .ep-header, .ep-source, .post_btns, .feed-recommend'):
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
                    # 网易的图片URL通常需要处理
                    if img_url.startswith('data:image'):
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
        # 网易财经的URL规律
        if "news1_json" in url:
            return "财经"
        elif "news2_json" in url:
            return "股票"
        elif "news3_json" in url:
            return "理财"
        elif "news4_json" in url:
            return "基金"
        elif "news5_json" in url:
            return "债券"
        elif "news6_json" in url:
            return "外汇"
        elif "news7_json" in url:
            return "期货"
        elif "news8_json" in url:
            return "产经"
        # 其他分类判断，基于URL路径
        elif "/stock/" in url:
            return "股票"
        elif "/fund/" in url:
            return "基金"
        elif "/forex/" in url:
            return "外汇"
        elif "/future/" in url:
            return "期货"
        elif "/licai/" in url:
            return "理财"
        elif "/bonds/" in url:
            return "债券"
        
        # 默认分类
        return "财经"
    
    def should_crawl_url(self, url: str) -> bool:
        """Check if URL should be crawled"""
        return bool(url and url.startswith(('http://', 'https://')) and 'money.163.com' in url) 