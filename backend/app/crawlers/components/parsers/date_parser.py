#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 日期解析器
提供从不同网站解析发布日期的功能
"""

import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List, Pattern, Tuple

class DateParser:
    """日期解析器，负责从不同网站的页面中提取发布日期"""

    # 常用日期选择器
    DEFAULT_SELECTORS = [
        'span.date', 'span.time', 'span.publish-time', 
        'div.article-info span.time', 'div.article-info span.date', 
        'p.article-time', 'div.date', 'time', 'span.article-time',
        'div.time-source span.time', 'span.publish'
    ]
    
    # 网站特定的日期选择器
    SITE_SELECTORS = {
        '新浪财经': ['div.date-source span.date', 'div.time-source span.time', 'span.date'],
        '东方财富': ['div.time', 'div.articleInfo .time', 'div.Info span.time', 'span.p-time'],
        '网易财经': ['div.post_time_source', 'div.post_info time', 'span.time'],
        '凤凰财经': ['div.item-time', 'span.ss01', 'div.clearfix span.date', 'div.time-cont']
    }
    
    # 日期格式模式
    DATE_PATTERNS = [
        # 完整日期时间模式
        (r'(\d{4}[-/\.年]\d{1,2}[-/\.月]\d{1,2}日?\s*\d{1,2}:\d{1,2}(:\d{1,2})?)', 
         ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", 
          "%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y年%m月%d日 %H:%M:%S", "%Y年%m月%d日 %H:%M"]),
          
        # 今天、昨天模式
        (r'今天\s*(\d{1,2}:\d{1,2}(:\d{1,2})?)', ["%H:%M:%S", "%H:%M"]),
        (r'昨天\s*(\d{1,2}:\d{1,2}(:\d{1,2})?)', ["%H:%M:%S", "%H:%M"]),
        
        # 月日模式（当年）
        (r'(\d{1,2}[-/\.月]\d{1,2}日?\s*\d{1,2}:\d{1,2}(:\d{1,2})?)',
         ["%m-%d %H:%M:%S", "%m-%d %H:%M", "%m/%d %H:%M:%S", "%m/%d %H:%M",
          "%m.%d %H:%M:%S", "%m.%d %H:%M", "%m月%d日 %H:%M:%S", "%m月%d日 %H:%M"]),
          
        # 仅有时间模式（今天）
        (r'(\d{1,2}:\d{1,2}(:\d{1,2})?)', ["%H:%M:%S", "%H:%M"])
    ]
    
    def __init__(self, site: str = None, custom_selectors: List[str] = None):
        """
        初始化日期解析器
        
        Args:
            site: 网站名称，用于选择特定选择器
            custom_selectors: 自定义选择器列表
        """
        self.site = site
        self.custom_selectors = custom_selectors or []
        
    def parse(self, html: str, url: str = None) -> Optional[datetime]:
        """
        从HTML中解析发布日期
        
        Args:
            html: HTML内容
            url: 文章URL，某些情况下可从URL中提取日期
            
        Returns:
            datetime: 解析到的日期时间，如果未解析到则返回None
        """
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 尝试从选择器中获取日期
        date_text = self._extract_date_from_selectors(soup)
        if date_text:
            date_obj = self._parse_date_string(date_text)
            if date_obj:
                return date_obj
                
        # 2. 尝试从meta标签中获取日期
        date_text = self._extract_date_from_meta(soup)
        if date_text:
            date_obj = self._parse_date_string(date_text)
            if date_obj:
                return date_obj
                
        # 3. 尝试从URL中获取日期
        if url:
            date_obj = self._extract_date_from_url(url)
            if date_obj:
                return date_obj
                
        # 4. 尝试从文本中找到日期模式
        date_text = self._find_date_in_text(soup)
        if date_text:
            date_obj = self._parse_date_string(date_text)
            if date_obj:
                return date_obj
                
        return None
        
    def _extract_date_from_selectors(self, soup: BeautifulSoup) -> Optional[str]:
        """从选择器中提取日期文本"""
        # 构建选择器列表
        selectors = self.custom_selectors.copy()
        
        if self.site and self.site in self.SITE_SELECTORS:
            selectors.extend(self.SITE_SELECTORS[self.site])
            
        selectors.extend(self.DEFAULT_SELECTORS)
        
        # 使用选择器尝试获取日期
        for selector in selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_text = date_elem.get_text().strip()
                if date_text and self._is_likely_date(date_text):
                    return date_text
                    
        return None
        
    def _extract_date_from_meta(self, soup: BeautifulSoup) -> Optional[str]:
        """从meta标签中提取日期"""
        # 常见的日期meta标签
        meta_names = [
            'pubdate', 'publishdate', 'date', 'article:published_time',
            'og:published_time', 'publication_date', 'release_date'
        ]
        
        for name in meta_names:
            meta = soup.find('meta', attrs={'name': name}) or soup.find('meta', attrs={'property': name})
            if meta and meta.get('content'):
                return meta['content']
                
        return None
        
    def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        """从URL中提取日期"""
        # 尝试匹配URL中的日期模式，如/2023/04/01/、/20230401/等
        patterns = [
            r'/(\d{4})/(\d{1,2})/(\d{1,2})/', # /2023/04/01/
            r'/(\d{4})(\d{2})(\d{2})/',       # /20230401/
            r'_(\d{4})(\d{2})(\d{2})_',       # _20230401_
            r'-(\d{4})(\d{2})(\d{2})-',       # -20230401-
            r'/(\d{4})(\d{2})(\d{2})\.',      # /20230401.html
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    
                    # 验证日期有效性
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        return datetime(year, month, day)
                except (ValueError, IndexError):
                    continue
                    
        return None
        
    def _find_date_in_text(self, soup: BeautifulSoup) -> Optional[str]:
        """在文本中查找可能的日期模式"""
        # 搜索整个文本
        text = soup.get_text()
        
        # 查找常见日期模式
        for pattern, _ in self.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
                
        return None
        
    def _parse_date_string(self, date_string: str) -> Optional[datetime]:
        """解析日期字符串为datetime对象"""
        date_string = date_string.strip()
        
        # 清理常见干扰文本
        date_string = re.sub(r'发布时间[:：]', '', date_string)
        date_string = re.sub(r'发布[:：]', '', date_string)
        date_string = re.sub(r'时间[:：]', '', date_string)
        date_string = re.sub(r'更新[:：]', '', date_string)
        date_string = date_string.strip()
        
        # 1. 尝试直接解析ISO格式日期
        try:
            return datetime.fromisoformat(date_string)
        except (ValueError, TypeError):
            pass
            
        # 2. 尝试根据预定义模式解析
        for pattern, formats in self.DATE_PATTERNS:
            match = re.search(pattern, date_string)
            if match:
                date_part = match.group(1)
                
                # 处理"今天"、"昨天"情况
                if "今天" in date_string:
                    today = datetime.now()
                    for fmt in formats:
                        try:
                            time_obj = datetime.strptime(date_part, fmt)
                            return datetime(
                                today.year, today.month, today.day,
                                time_obj.hour, time_obj.minute, time_obj.second if ":" in fmt else 0
                            )
                        except ValueError:
                            continue
                elif "昨天" in date_string:
                    yesterday = datetime.now() - timedelta(days=1)
                    for fmt in formats:
                        try:
                            time_obj = datetime.strptime(date_part, fmt)
                            return datetime(
                                yesterday.year, yesterday.month, yesterday.day,
                                time_obj.hour, time_obj.minute, time_obj.second if ":" in fmt else 0
                            )
                        except ValueError:
                            continue
                else:
                    # 常规日期格式
                    for fmt in formats:
                        try:
                            date_obj = datetime.strptime(date_part, fmt)
                            
                            # 处理没有年份的情况（使用当前年份）
                            if "%Y" not in fmt:
                                current_year = datetime.now().year
                                return date_obj.replace(year=current_year)
                            
                            return date_obj
                        except ValueError:
                            continue
                            
        return None
        
    def _is_likely_date(self, text: str) -> bool:
        """判断文本是否可能是日期"""
        # 包含数字和时间分隔符的简单验证
        return bool(re.search(r'\d+[-/\.年:月日时分秒]', text)) and len(text) < 50 