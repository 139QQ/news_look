#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 解析器组件
负责解析HTML和提取内容
"""

import re
import json
import logging
import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

from backend.app.utils.logger import get_crawler_logger
from backend.app.utils.text_cleaner import (
    clean_html_content, 
    extract_keywords, 
    decode_html_entities, 
    decode_unicode_escape, 
    decode_url_encoded
)

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('parsers')

class BaseParser(ABC):
    """解析器基类，定义解析器的接口"""
    
    @abstractmethod
    def parse_list(self, content: str, url: str = None) -> List[Dict]:
        """解析列表页面，提取新闻列表"""
        pass
    
    @abstractmethod
    def parse_detail(self, content: str, url: str = None) -> Dict:
        """解析详情页面，提取新闻详情"""
        pass
    
    @abstractmethod
    def clean_content(self, content: str) -> str:
        """清理内容，去除广告、无用标签等"""
        pass


class HTMLParser(BaseParser):
    """HTML解析器，使用BeautifulSoup解析HTML内容"""
    
    def __init__(self, list_selector: Optional[Dict] = None, 
                 detail_selector: Optional[Dict] = None,
                 date_format: str = '%Y-%m-%d %H:%M:%S'):
        """
        初始化HTML解析器
        
        Args:
            list_selector: 列表页面选择器
            detail_selector: 详情页面选择器
            date_format: 日期格式
        """
        # 默认列表选择器
        self.list_selector = {
            'container': 'div.news-list, ul.news-list, div.article-list',
            'item': 'div.news-item, li.news-item, div.article-item',
            'title': 'h2, h3, a.title',
            'link': 'a',
            'date': 'span.date, time.date, span.time',
            'summary': 'div.summary, p.summary, div.desc'
        }
        
        # 默认详情选择器
        self.detail_selector = {
            'title': 'h1.title, h1.article-title, div.article-title h1',
            'content': 'div.article-content, div.content, article.content, div.article',
            'date': 'span.date, time.date, span.time, div.article-info time',
            'author': 'span.author, div.author, span.editor, div.editor',
            'source': 'span.source, div.source',
            'category': 'span.category, div.category, span.channel, div.channel'
        }
        
        # 更新选择器
        if list_selector:
            self.list_selector.update(list_selector)
        if detail_selector:
            self.detail_selector.update(detail_selector)
            
        self.date_format = date_format
        
    def parse_list(self, content: str, url: str = None) -> List[Dict]:
        """
        解析列表页面，提取新闻列表
        
        Args:
            content: HTML内容
            url: 页面URL
            
        Returns:
            List[Dict]: 新闻列表
        """
        if not content:
            logger.warning("解析列表页面失败：内容为空")
            return []
            
        # 尝试修复编码问题
        content = self._fix_encoding(content)
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # 尝试查找容器
            containers = soup.select(self.list_selector['container'])
            if not containers:
                # 如果找不到容器，尝试直接查找条目
                items = soup.select(self.list_selector['item'])
            else:
                # 如果找到容器，在容器中查找条目
                container = containers[0]
                items = container.select(self.list_selector['item'])
            
            news_list = []
            
            for item in items:
                try:
                    # 提取标题
                    title_elem = item.select_one(self.list_selector['title'])
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    # 提取链接
                    link_elem = item.select_one(self.list_selector['link'])
                    link = ""
                    if link_elem and link_elem.has_attr('href'):
                        link = link_elem['href']
                        # 处理相对URL
                        if link.startswith('/') and url:
                            from urllib.parse import urljoin
                            link = urljoin(url, link)
                    
                    # 提取日期
                    date_elem = item.select_one(self.list_selector['date'])
                    date_str = date_elem.get_text(strip=True) if date_elem else ""
                    date = self._parse_date(date_str)
                    
                    # 提取摘要
                    summary_elem = item.select_one(self.list_selector['summary'])
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    # 创建新闻字典
                    news = {
                        'title': title,
                        'url': link,
                        'publish_time': date,
                        'summary': summary
                    }
                    
                    # 只添加有效的新闻（至少有标题和链接）
                    if title and link:
                        news_list.append(news)
                        
                except Exception as e:
                    logger.error(f"解析新闻列表项时出错: {str(e)}")
                    continue
            
            return news_list
            
        except Exception as e:
            logger.error(f"解析列表页面失败: {str(e)}")
            return []
    
    def parse_detail(self, content: str, url: str = None) -> Dict:
        """
        解析详情页面，提取新闻详情
        
        Args:
            content: HTML内容
            url: 页面URL
            
        Returns:
            Dict: 新闻详情
        """
        if not content:
            logger.warning("解析详情页面失败：内容为空")
            return {}
            
        # 尝试修复编码问题
        content = self._fix_encoding(content)
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # 提取标题
            title_elem = soup.select_one(self.detail_selector['title'])
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # 提取内容
            content_elem = soup.select_one(self.detail_selector['content'])
            if content_elem:
                # 清理内容
                content_html = str(content_elem)
                content_text = self.clean_content(content_html)
            else:
                content_html = ""
                content_text = ""
            
            # 提取日期
            date_elem = soup.select_one(self.detail_selector['date'])
            date_str = date_elem.get_text(strip=True) if date_elem else ""
            date = self._parse_date(date_str)
            
            # 提取作者
            author_elem = soup.select_one(self.detail_selector['author'])
            author = author_elem.get_text(strip=True) if author_elem else ""
            
            # 提取来源
            source_elem = soup.select_one(self.detail_selector['source'])
            source = source_elem.get_text(strip=True) if source_elem else ""
            
            # 提取分类
            category_elem = soup.select_one(self.detail_selector['category'])
            category = category_elem.get_text(strip=True) if category_elem else ""
            
            # 提取关键词
            keywords = extract_keywords(content_text)
            
            # 提取图片
            images = self._extract_images(soup, self.detail_selector['content'])
            
            # 创建新闻详情字典
            news_detail = {
                'title': title,
                'content': content_text,
                'content_html': content_html,
                'publish_time': date,
                'author': author,
                'source': source,
                'category': category,
                'url': url,
                'keywords': keywords,
                'images': images,
                'crawl_time': datetime.datetime.now().strftime(self.date_format)
            }
            
            return news_detail
            
        except Exception as e:
            logger.error(f"解析详情页面失败: {str(e)}")
            return {}
    
    def clean_content(self, content: str) -> str:
        """
        清理内容，去除广告、无用标签等
        
        Args:
            content: HTML内容
            
        Returns:
            str: 清理后的文本内容
        """
        if not content:
            return ""
            
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # 移除不需要的标签
            for tag in soup(['script', 'style', 'iframe', 'form', 'ins', 'div.advertisement', 'div.ad']):
                tag.decompose()
            
            # 移除空节点
            for tag in soup.find_all(lambda t: t.name and not t.contents and not t.string):
                tag.decompose()
            
            # 去除评论区
            for tag in soup.select('div.comment, div.comments, div#comments, div.comment-area'):
                tag.decompose()
            
            # 清理属性
            for tag in soup.find_all(True):
                # 保留部分有用属性
                allowed_attrs = ['href', 'src', 'alt', 'title']
                for attr in list(tag.attrs):
                    if attr not in allowed_attrs:
                        del tag.attrs[attr]
            
            # 获取清理后的HTML
            cleaned_html = str(soup)
            
            # 使用内置的HTML清理功能
            cleaned_text = clean_html_content(cleaned_html)
            
            return cleaned_text.strip()
            
        except Exception as e:
            logger.error(f"清理内容时出错: {str(e)}")
            return ""
    
    def _parse_date(self, date_str: str) -> str:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
            
        Returns:
            str: 标准格式的日期字符串
        """
        if not date_str:
            return datetime.datetime.now().strftime(self.date_format)
            
        # 清理日期字符串
        date_str = date_str.strip()
        date_str = re.sub(r'[\[\]()]', '', date_str)
        date_str = re.sub(r'发布时间：|日期：|时间：|来源：|作者：', '', date_str)
        date_str = date_str.strip()
        
        # 常见的日期格式
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y年%m月%d日 %H:%M:%S',
            '%Y年%m月%d日 %H:%M',
            '%Y年%m月%d日 %H时%M分',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y.%m.%d %H:%M:%S',
            '%Y.%m.%d %H:%M',
            '%m-%d %H:%M',
            '%m月%d日 %H:%M',
        ]
        
        # 尝试不同的格式解析日期
        for fmt in formats:
            try:
                # 尝试解析日期
                dt = datetime.datetime.strptime(date_str, fmt)
                
                # 如果年份缺失（如月日时间格式），添加当前年份
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.datetime.now().year)
                
                # 返回标准格式的日期字符串
                return dt.strftime(self.date_format)
            except ValueError:
                continue
        
        # 尝试识别相对日期表达
        try:
            # 处理"X分钟前"、"X小时前"等表达
            if '分钟前' in date_str:
                minutes = int(re.search(r'(\d+)分钟前', date_str).group(1))
                dt = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
                return dt.strftime(self.date_format)
            elif '小时前' in date_str:
                hours = int(re.search(r'(\d+)小时前', date_str).group(1))
                dt = datetime.datetime.now() - datetime.timedelta(hours=hours)
                return dt.strftime(self.date_format)
            elif '天前' in date_str:
                days = int(re.search(r'(\d+)天前', date_str).group(1))
                dt = datetime.datetime.now() - datetime.timedelta(days=days)
                return dt.strftime(self.date_format)
        except Exception:
            pass
        
        # 如果无法解析，使用当前时间
        logger.warning(f"无法解析日期: {date_str}，使用当前时间")
        return datetime.datetime.now().strftime(self.date_format)
    
    def _extract_images(self, soup: BeautifulSoup, content_selector: str) -> List[str]:
        """
        提取图片URL
        
        Args:
            soup: BeautifulSoup对象
            content_selector: 内容选择器
            
        Returns:
            List[str]: 图片URL列表
        """
        images = []
        
        try:
            # 尝试查找内容区域
            content_elem = soup.select_one(content_selector)
            if content_elem:
                # 在内容区域中查找图片
                for img in content_elem.find_all('img'):
                    if img.has_attr('src'):
                        img_url = img['src']
                        # 处理图片URL
                        img_url = decode_url_encoded(img_url)
                        images.append(img_url)
            
            # 去重
            images = list(set(images))
            
            return images
            
        except Exception as e:
            logger.error(f"提取图片时出错: {str(e)}")
            return []
    
    def _fix_encoding(self, content: str) -> str:
        """
        修复编码问题
        
        Args:
            content: HTML内容
            
        Returns:
            str: 修复编码后的内容
        """
        # 应用各种解码方法
        content = decode_html_entities(content)
        content = decode_unicode_escape(content)
        content = decode_url_encoded(content)
        
        return content


class JSONParser(BaseParser):
    """JSON解析器，解析JSON格式数据"""
    
    def __init__(self, list_mapping: Optional[Dict] = None, 
                 detail_mapping: Optional[Dict] = None,
                 date_format: str = '%Y-%m-%d %H:%M:%S'):
        """
        初始化JSON解析器
        
        Args:
            list_mapping: 列表字段映射
            detail_mapping: 详情字段映射
            date_format: 日期格式
        """
        # 默认列表映射
        self.list_mapping = {
            'container': 'data.list',
            'title': 'title',
            'link': 'url',
            'date': 'publishTime',
            'summary': 'summary'
        }
        
        # 默认详情映射
        self.detail_mapping = {
            'title': 'data.title',
            'content': 'data.content',
            'date': 'data.publishTime',
            'author': 'data.author',
            'source': 'data.source',
            'category': 'data.category'
        }
        
        # 更新映射
        if list_mapping:
            self.list_mapping.update(list_mapping)
        if detail_mapping:
            self.detail_mapping.update(detail_mapping)
            
        self.date_format = date_format
        
    def parse_list(self, content: str, url: str = None) -> List[Dict]:
        """
        解析列表页面，提取新闻列表
        
        Args:
            content: JSON内容
            url: 页面URL
            
        Returns:
            List[Dict]: 新闻列表
        """
        if not content:
            logger.warning("解析列表页面失败：内容为空")
            return []
            
        try:
            # 尝试解析JSON
            data = json.loads(content)
            
            # 获取数据容器
            container_path = self.list_mapping['container'].split('.')
            container = data
            for key in container_path:
                if key in container:
                    container = container[key]
                else:
                    logger.warning(f"找不到容器路径: {self.list_mapping['container']}")
                    return []
            
            # 确保容器是列表
            if not isinstance(container, list):
                logger.warning("数据容器不是列表")
                return []
            
            news_list = []
            
            for item in container:
                try:
                    # 提取标题
                    title = self._get_value_by_path(item, self.list_mapping['title'])
                    
                    # 提取链接
                    link = self._get_value_by_path(item, self.list_mapping['link'])
                    
                    # 提取日期
                    date_str = self._get_value_by_path(item, self.list_mapping['date'])
                    date = self._parse_date(date_str)
                    
                    # 提取摘要
                    summary = self._get_value_by_path(item, self.list_mapping['summary'])
                    
                    # 创建新闻字典
                    news = {
                        'title': title,
                        'url': link,
                        'publish_time': date,
                        'summary': summary
                    }
                    
                    # 只添加有效的新闻（至少有标题和链接）
                    if title and link:
                        news_list.append(news)
                        
                except Exception as e:
                    logger.error(f"解析新闻列表项时出错: {str(e)}")
                    continue
            
            return news_list
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"解析列表页面失败: {str(e)}")
            return []
    
    def parse_detail(self, content: str, url: str = None) -> Dict:
        """
        解析详情页面，提取新闻详情
        
        Args:
            content: JSON内容
            url: 页面URL
            
        Returns:
            Dict: 新闻详情
        """
        if not content:
            logger.warning("解析详情页面失败：内容为空")
            return {}
            
        try:
            # 尝试解析JSON
            data = json.loads(content)
            
            # 提取各字段
            title = self._get_value_by_path(data, self.detail_mapping['title'])
            content_html = self._get_value_by_path(data, self.detail_mapping['content'])
            content_text = self.clean_content(content_html)
            date_str = self._get_value_by_path(data, self.detail_mapping['date'])
            date = self._parse_date(date_str)
            author = self._get_value_by_path(data, self.detail_mapping['author'])
            source = self._get_value_by_path(data, self.detail_mapping['source'])
            category = self._get_value_by_path(data, self.detail_mapping['category'])
            
            # 提取关键词
            keywords = extract_keywords(content_text)
            
            # 提取图片
            images = self._extract_images_from_html(content_html)
            
            # 创建新闻详情字典
            news_detail = {
                'title': title,
                'content': content_text,
                'content_html': content_html,
                'publish_time': date,
                'author': author,
                'source': source,
                'category': category,
                'url': url,
                'keywords': keywords,
                'images': images,
                'crawl_time': datetime.datetime.now().strftime(self.date_format)
            }
            
            return news_detail
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"解析详情页面失败: {str(e)}")
            return {}
    
    def clean_content(self, content: str) -> str:
        """
        清理内容，去除HTML标签等
        
        Args:
            content: HTML内容
            
        Returns:
            str: 清理后的文本内容
        """
        if not content:
            return ""
            
        # 去除HTML标签
        return clean_html_content(content)
    
    def _get_value_by_path(self, data: Any, path: str) -> Any:
        """
        根据路径获取数据
        
        Args:
            data: 数据对象
            path: 路径（如'data.list.0.title'）
            
        Returns:
            Any: 路径对应的数据
        """
        if not path:
            return None
            
        # 处理数组索引
        parts = []
        for part in path.split('.'):
            # 检查是否是数组索引
            if part.isdigit():
                parts.append(int(part))
            else:
                parts.append(part)
        
        # 获取值
        value = data
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            elif isinstance(value, list) and isinstance(part, int) and 0 <= part < len(value):
                value = value[part]
            else:
                return None
        
        return value
    
    def _parse_date(self, date_str: str) -> str:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
            
        Returns:
            str: 标准格式的日期字符串
        """
        # 如果是时间戳
        if isinstance(date_str, (int, float)):
            # 假设是毫秒级时间戳
            if date_str > 1000000000000:
                date_str = date_str / 1000
            return datetime.datetime.fromtimestamp(date_str).strftime(self.date_format)
            
        # 如果是字符串
        if isinstance(date_str, str):
            # 尝试解析，使用与HTMLParser相同的方法
            html_parser = HTMLParser(date_format=self.date_format)
            return html_parser._parse_date(date_str)
        
        # 默认返回当前时间
        return datetime.datetime.now().strftime(self.date_format)
    
    def _extract_images_from_html(self, html: str) -> List[str]:
        """
        从HTML内容中提取图片URL
        
        Args:
            html: HTML内容
            
        Returns:
            List[str]: 图片URL列表
        """
        if not html:
            return []
            
        images = []
        
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取所有图片
            for img in soup.find_all('img'):
                if img.has_attr('src'):
                    img_url = img['src']
                    # 处理图片URL
                    img_url = decode_url_encoded(img_url)
                    images.append(img_url)
            
            # 去重
            images = list(set(images))
            
            return images
            
        except Exception as e:
            logger.error(f"从HTML中提取图片时出错: {str(e)}")
            return []


def create_parser(parser_type: str = 'html', **kwargs) -> BaseParser:
    """
    创建解析器工厂函数
    
    Args:
        parser_type: 解析器类型（'html'或'json'）
        **kwargs: 其他参数
        
    Returns:
        BaseParser: 解析器实例
    """
    if parser_type.lower() == 'json':
        return JSONParser(**kwargs)
    else:
        return HTMLParser(**kwargs) 