#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 新浪财经爬虫策略
专门针对新浪财经网站的爬取策略实现
"""

import re
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from backend.app.crawlers.strategies.base_strategy import BaseCrawlerStrategy
from backend.app.utils.text_cleaner import clean_html, decode_html_entities

class SinaStrategy(BaseCrawlerStrategy):
    """新浪财经网站爬虫策略"""
    
    def __init__(self, source="新浪财经"):
        """初始化策略"""
        super().__init__(source)
        
        # 列表页URL模板
        self.list_url_templates = {
            "首页": "https://finance.sina.com.cn/",
            "财经": "https://finance.sina.com.cn/china/",
            "股票": "https://finance.sina.com.cn/stock/",
            "基金": "https://finance.sina.com.cn/fund/",
            "外汇": "https://finance.sina.com.cn/forex/",
            "期货": "https://finance.sina.com.cn/futures/",
            "港股": "https://finance.sina.com.cn/hk/",
            "美股": "https://finance.sina.com.cn/usstock/",
            "科技": "https://tech.sina.com.cn/",
            "宏观": "https://finance.sina.com.cn/roll/index.d.html?cid=56592"
        }
        
        # 设置分类字典，父类属性
        self.categories = self.list_url_templates.copy()
    
    def get_categories(self) -> Dict[str, str]:
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
            urls.append(self.list_url_templates[category])
        # 如果未指定分类，获取所有分类的列表页
        else:
            urls.extend(self.list_url_templates.values())
                
        return urls
    
    def get_list_page_urls(self, days: int = 1, category: Optional[str] = None) -> List[str]:
        """
        获取列表页URL
        
        Args:
            days: 爬取最近几天的新闻
            category: 新闻分类
            
        Returns:
            List[str]: 列表页URL列表
        """
        return self.get_list_urls(category, days)
    
    def parse_list_page(self, html: str, url: str) -> List[str]:
        """
        解析列表页，提取文章链接
        
        Args:
            html: 列表页HTML内容
            url: 列表页URL
            
        Returns:
            List[str]: 文章URL列表
        """
        articles = self.parse_list_page_full(html, url)
        return [article['url'] for article in articles if 'url' in article]
    
    def parse_list_page_full(self, html: str, url: str) -> List[Dict[str, Any]]:
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
        
        # 尝试各种可能的文章列表格式
        # 1. 新闻列表(常规)
        news_items = soup.select('ul.news-list li, div.news-item, div.box-list li')
        for item in news_items:
            try:
                # 获取链接
                link = item.select_one('a')
                if not link:
                    continue
                    
                news_url = link.get('href', '')
                if not news_url or not self.should_crawl_url(news_url):
                    continue
                    
                # 获取标题
                title = link.text.strip() or link.get('title', '').strip()
                
                # 获取时间
                time_element = item.select_one('span.time, span.date')
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
                print(f"解析新浪财经列表项时出错: {str(e)}")
                
        # 2. 特殊的滚动区域
        if not articles:
            roll_items = soup.select('div.r-nt2 li, div.feed-card-item, div.m-list li')
            for item in roll_items:
                try:
                    link = item.select_one('a')
                    if not link:
                        continue
                        
                    news_url = link.get('href', '')
                    if not news_url or not self.should_crawl_url(news_url):
                        continue
                        
                    title = link.text.strip() or link.get('title', '').strip()
                    
                    article_info = {
                        'url': news_url,
                        'title': title,
                        'source': self.source,
                        'category': category
                    }
                    
                    articles.append(article_info)
                except Exception as e:
                    print(f"解析新浪财经滚动列表项时出错: {str(e)}")
                    
        # 3. 搜索所有可能是新闻的链接
        if not articles:
            # 先找到可能的新闻区块
            news_blocks = soup.select('div.news-container, div.main-content, div.w-main')
            search_area = news_blocks[0] if news_blocks else soup
            
            # 在区块中查找所有链接
            for link in search_area.select('a[href]'):
                try:
                    news_url = link.get('href', '')
                    
                    # 过滤掉导航链接、广告链接等
                    if not news_url or not re.search(r'\d{4}-\d{2}-\d{2}', news_url) or not self.should_crawl_url(news_url):
                        continue
                        
                    title = link.text.strip() or link.get('title', '').strip()
                    if not title or len(title) < 10:  # 过滤过短的标题
                        continue
                        
                    article_info = {
                        'url': news_url,
                        'title': title,
                        'source': self.source,
                        'category': category
                    }
                    
                    articles.append(article_info)
                except Exception as e:
                    print(f"解析新浪财经链接时出错: {str(e)}")
                    
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
        
        # 新浪财经有多种文章页面格式，需要分别处理
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 提取标题
        if 'title' not in article or not article['title']:
            # 扩展标题选择器，适应更多布局
            title_selectors = [
                'h1.main-title', 
                'h1#artibodyTitle', 
                'h1.title', 
                'h1.article-title',
                'h1.m-title',       # 移动版页面标题
                'h1.focus-title',   # 焦点新闻标题
                'h1.content-title', # 内容页标题
                'div.page-header h1', # 某些板块使用的标题格式
                'div.txt-hd h1',    # 新财经频道标题
                'div.f_center h1',  # 旧版标题
                'div.headline h1'   # 头条新闻标题
            ]
            
            title_element = None
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    break
                    
            if title_element:
                article['title'] = title_element.text.strip()
        
        # 2. 提取发布时间
        if 'pub_time' not in article or not article['pub_time']:
            # 扩展时间选择器，适应更多布局
            time_selectors = [
                'span.date', 
                'div.date-source span.date', 
                'div.time-source span.time', 
                'p.date',
                'div.date', 
                'span.time', 
                'span.titer', 
                'div.article-info span.time',
                'div.date-author span.date',
                'div.source-intro span.time',
                'p.info span.time', 
                'div.pub_time'
            ]
            
            time_element = None
            for selector in time_selectors:
                time_element = soup.select_one(selector)
                if time_element:
                    break
                    
            if time_element:
                pub_time = time_element.text.strip()
                # 标准化时间格式，去除可能的多余信息
                pub_time = re.sub(r'[年月]', '-', pub_time)
                pub_time = re.sub(r'日\s*', ' ', pub_time)
                article['pub_time'] = pub_time
                
        # 3. 提取作者/来源
        if 'author' not in article or not article['author']:
            # 扩展来源选择器，适应更多布局
            source_selectors = [
                'div.date-source span.source', 
                'div.time-source span.source', 
                'a.source', 
                'p.source',
                'div.info a.source',
                'span.author',
                'div.source span',
                'div.source-intro span.source',
                'div.article-info a.media-name',
                'p.info a[data-sudaclick="media_name"]'
            ]
            
            source_element = None
            for selector in source_selectors:
                source_element = soup.select_one(selector)
                if source_element:
                    break
                    
            if source_element:
                author_text = source_element.text.strip()
                # 提取来源中的作者信息
                if '来源:' in author_text or '来源：' in author_text:
                    author_text = re.sub(r'来源[：:]\s*', '', author_text)
                article['author'] = author_text
                
        # 4. 提取正文内容
        # 扩展内容选择器，适应更多布局
        content_selectors = [
            '#artibody', 
            'div.article-content',
            'div.article', 
            'div#article_content',
            'div.article_content',
            'div.content',
            'div.m-content',
            'div.main-content',
            'div.main_content',
            'div.article-body',
            'div.art_main',
            'div.newsdetail',
            'div.con_txt',
            'div.article-body-content',
            'div.body'
        ]
        
        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break
                
        if content_element:
            # 移除可能的广告和无用元素
            ad_selectors = [
                'div.article-bottom', 
                'div.article-end-info', 
                'div.custom_txtContent', 
                'div.appendQr_normal', 
                'div.tech-quotation', 
                'div.statement',
                'div.recommend', 
                'div.related', 
                'div.module', 
                'div.share-box',
                'div.zb_rel_news', 
                'div.ad_', 
                'div.advert', 
                'div[id^="ad_"]',
                'div[id^="adv_"]',
                'div.bottom-bar',
                'div.footer-bar',
                'div.sinaads',
                'div.article-footer',
                'div.open-app',
                'div.author-info',
                'div[class*="ad-"]',
                'div.fin_m_txtimg',
                'div.art_rec',
                'div[class*="recommend"]',
                'div.j_related_news',
                'div.stockcontent',
                'div.otherContent_01',
                'iframe'
            ]
            
            for ad_selector in ad_selectors:
                for ad in content_element.select(ad_selector):
                    ad.decompose()
                    
            # 还需要移除内联的广告脚本和样式
            for script in content_element.find_all('script'):
                script.decompose()
                
            for style in content_element.find_all('style'):
                style.decompose()
                
            # 移除包含广告关键词的元素    
            ad_keywords = ['广告', '推广', '赞助', '下载', 'APP', '更多文章', '相关阅读', '推荐阅读', '更多精彩', '更多新闻']
            for element in content_element.find_all(text=lambda text: any(keyword in text for keyword in ad_keywords) if text else False):
                parent = element.parent
                if parent and parent.name not in ['title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    parent.decompose()
                
            # 获取HTML内容和纯文本
            article['content_html'] = str(content_element)
            
            # 对文本进行清理，保留段落结构
            paragraphs = []
            for p in content_element.find_all(['p', 'div', 'h2', 'h3']):
                text = p.get_text().strip()
                if text and len(text) > 1:
                    paragraphs.append(text)
            
            article['content'] = '\n\n'.join(paragraphs)
            
        # 5. 提取分类，如果basic_info中没有
        if 'category' not in article or not article['category']:
            article['category'] = self._get_category_from_url(url)
            
        # 6. 提取关键词
        if 'keywords' not in article:
            # 尝试从meta标签获取
            keywords_element = soup.select_one('meta[name="keywords"]')
            if keywords_element and 'content' in keywords_element.attrs:
                article['keywords'] = keywords_element['content']
            else:
                # 尝试从页面内容获取关键词标签
                keywords_elements = soup.select('div.keywords a, div.article-keywords a, p.keywords a, div.tag a')
                if keywords_elements:
                    keywords = [el.text.strip() for el in keywords_elements]
                    article['keywords'] = ','.join(keywords)
            
        # 7. 提取图片
        if 'content_html' in article:
            img_soup = BeautifulSoup(article['content_html'], 'html.parser')
            images = []
            
            # 查找所有图片，包括懒加载图片
            for img in img_soup.select('img'):
                # 获取图片URL，优先获取data-src（懒加载的原始URL）
                img_url = img.get('data-src') or img.get('src') or img.get('data-original', '')
                if not img_url:
                    continue
                    
                # 过滤广告图片、图标和装饰图片
                ignore_patterns = ['advert', 'icon', 'logo', 'sprite', 'blank', 'spacer', 'button', 
                                   'sinaads', 'ad_', 'ad.', '.ad', 'banner']
                if any(pattern in img_url.lower() for pattern in ignore_patterns):
                    continue
                    
                # 过滤小图片（通常是图标或按钮）
                if img.get('width') and int(img.get('width')) < 100:
                    continue
                if img.get('height') and int(img.get('height')) < 100:
                    continue
                    
                # 确保URL为绝对路径
                if not img_url.startswith(('http://', 'https://')):
                    img_url = urljoin(url, img_url)
                    
                # 防止重复图片
                if img_url not in images:
                    images.append(img_url)
                
            if images:
                article['images'] = json.dumps(images)
                
        # 8. 添加爬取时间
        article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return article
    
    def should_crawl_url(self, url: str) -> bool:
        """
        检查URL是否应该被爬取
        
        Args:
            url: 要检查的URL
            
        Returns:
            bool: 是否应该爬取该URL
        """
        if not url:
            return False
            
        # 确保URL是以http或https开头
        if not url.startswith(('http://', 'https://')):
            return False
        
        # 确保URL属于新浪财经域名
        if not any(domain in url for domain in ['finance.sina.com.cn', 'sina.com.cn/finance', 'money.sina.com.cn', 'sina.com.cn/money']):
            return False
        
        # 过滤视频页面(通常内容较少)
        if '/video/' in url or 'video.sina.com.cn' in url:
            return False
            
        # 过滤专题页、列表页
        if '/zt_' in url or '/zt/' in url or '/list/' in url or 'list.sina.com.cn' in url:
            return False
            
        # 过滤直播页面
        if '/live/' in url or 'live.sina.com.cn' in url:
            return False
            
        # 过滤幻灯片
        if '/slide' in url or 'slide.sina.com.cn' in url:
            return False
            
        # 过滤广告页面
        ad_patterns = [
            'sinaads', 'adbox', 'advertisement', 'promotion', 'sponsor', 
            'click.sina', 'sina.cn', 'game.weibo', 'games.sina', 'iask',
            'beacon.sina', 'sax.sina', 'int.dpool', 'interest.mix', 'api.sina',
            'zhongce.sina', 'zhuanlan.sina'
        ]
        if any(pattern in url for pattern in ad_patterns):
            return False
            
        # 过滤账户相关
        if any(pattern in url for pattern in ['login', 'register', 'account', 'passport']):
            return False
            
        # 过滤WAP版、移动版首页和特定频道页
        if url.endswith('/') or url.endswith('.d.html') or url.endswith('index.shtml'):
            return False
            
        # 过滤PDF、ZIP等非网页文件
        if any(ext in url for ext in ['.pdf', '.zip', '.rar', '.doc', '.xls', '.ppt', '.jpg', '.png', '.gif']):
            return False
            
        # 过滤博客和微博
        if 'blog.sina' in url or 'weibo.com' in url:
            return False
            
        # 过滤网页浏览量过高的页面(通常是广告页或热点内容聚合页)
        if '/pv/' in url:
            return False
            
        # 过滤评论页面
        if '/comments/' in url or 'comment.sina' in url:
            return False
            
        # 如果链接包含年份和日期，说明可能是有效的新闻文章
        date_patterns = [
            r'/\d{4}-\d{2}-\d{2}/', 
            r'/\d{4}/\d{4}/', 
            r'/\d{8}/'
        ]
        has_date_pattern = any(re.search(pattern, url) for pattern in date_patterns)
        
        # 一般有效新闻URL包含"doc"字段
        has_doc = 'doc' in url
        
        # 检查链接是否指向新浪财经的文章页
        article_patterns = ['/finance/', '/dy/', '/zj/', '/stock/', '/forex/', '/money/', '/chanjing/', '/bond/', '/fund/']
        has_article_pattern = any(pattern in url for pattern in article_patterns)
        
        # 对于不明确的URL，如果包含日期模式或doc标识，或者是可能的文章页面，则认为是有效的
        if has_date_pattern or has_doc or has_article_pattern:
            return True
            
        # 默认情况下不爬取，安全起见
        return False
    
    def _get_category_from_url(self, url: str) -> str:
        """
        从URL中提取分类
        
        Args:
            url: 文章URL
            
        Returns:
            str: 分类名称
        """
        # 新浪财经的URL规律
        if '/stock/' in url:
            return '股票'
        elif '/fund/' in url:
            return '基金'
        elif '/forex/' in url:
            return '外汇'
        elif '/futures/' in url:
            return '期货'
        elif '/usstock/' in url:
            return '美股'
        elif '/hk/' in url:
            return '港股'
        elif '/tech.' in url:
            return '科技'
        elif '/china/' in url:
            return '宏观'
            
        # 默认分类
        return '财经' 