#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 作者解析器
提供从不同网站解析新闻作者的功能
"""

import re
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List, Pattern

class AuthorParser:
    """作者解析器，负责从不同网站的页面中提取作者信息"""

    # 常用作者选择器
    DEFAULT_SELECTORS = [
        'span.author', 'div.author', 'div.article-author', 
        'p.article-author', 'div.writer', 'span.writer',
        'a.author', 'span.article-author', 'div.articleInfo .author',
        'div.author-info', 'div.byline'
    ]
    
    # 网站特定的作者选择器
    SITE_SELECTORS = {
        '新浪财经': ['div.date-source a', 'div.author-info', 'div.show_author'],
        '东方财富': ['div.author', 'div.source', 'div.articleInfo .author'],
        '网易财经': ['div.post_info .author', 'div.ep-source'],
        '凤凰财经': ['div.ss_con a', 'div.author-name']
    }
    
    # 作者文本模式
    AUTHOR_PATTERNS = [
        # 编辑模式
        (r'编辑[：:]?\s*([^<>]{2,10})', 1),
        (r'责任编辑[：:]?\s*([^<>\n]{2,10})', 1),
        (r'([^<>\n]{2,10})\s*[/／]\s*编辑', 1),
        # 作者模式
        (r'作者[：:]?\s*([^<>\n]{2,15})', 1),
        (r'记者[：:]?\s*([^<>\n]{2,15})', 1),
        (r'文[/／]\s*([^<>\n]{2,10})', 1),
    ]
    
    # 不可能是作者的字符串
    NON_AUTHOR_STRINGS = [
        '原创', '独家', '来源', '未知', '佚名', '本报', '财经', '综合',
        '新浪', '东方财富', '第一财经', '网易', '凤凰', '中国经济网', 
        '记者', '实习', '稿源', '投稿', '网站', 'http', 'www'
    ]
    
    def __init__(self, site: str = None, custom_selectors: List[str] = None):
        """
        初始化作者解析器
        
        Args:
            site: 网站名称，用于选择特定选择器
            custom_selectors: 自定义选择器列表
        """
        self.site = site
        self.custom_selectors = custom_selectors or []
        
    def parse(self, html: str, content: str = None) -> Optional[str]:
        """
        从HTML中解析作者
        
        Args:
            html: HTML内容
            content: 正文内容，用于从正文中提取作者信息
            
        Returns:
            str: 解析到的作者，如果未解析到则返回None
        """
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 尝试从选择器中获取作者
        author = self._extract_author_from_selectors(soup)
        if author:
            return self.clean_author(author)
            
        # 2. 尝试从meta标签中获取作者
        author = self._extract_author_from_meta(soup)
        if author:
            return self.clean_author(author)
            
        # 3. 如果提供了正文内容，尝试从正文中获取作者
        if content:
            author = self._extract_author_from_content(content)
            if author:
                return self.clean_author(author)
                
        # 4. 尝试从HTML中查找作者模式
        author = self._find_author_pattern(soup.get_text())
        if author:
            return self.clean_author(author)
            
        return None
        
    def _extract_author_from_selectors(self, soup: BeautifulSoup) -> Optional[str]:
        """从选择器中提取作者"""
        # 构建选择器列表
        selectors = self.custom_selectors.copy()
        
        if self.site and self.site in self.SITE_SELECTORS:
            selectors.extend(self.SITE_SELECTORS[self.site])
            
        selectors.extend(self.DEFAULT_SELECTORS)
        
        # 使用选择器尝试获取作者
        for selector in selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = author_elem.get_text().strip()
                if author and self._is_valid_author(author):
                    return author
                    
        return None
        
    def _extract_author_from_meta(self, soup: BeautifulSoup) -> Optional[str]:
        """从meta标签中提取作者"""
        # 常见的作者meta标签
        meta_names = [
            'author', 'article:author', 'og:author', 'DC.creator',
            'byl', 'twitter:creator', 'weibo:article:create_user'
        ]
        
        for name in meta_names:
            meta = soup.find('meta', attrs={'name': name}) or soup.find('meta', attrs={'property': name})
            if meta and meta.get('content'):
                author = meta['content'].strip()
                if self._is_valid_author(author):
                    return author
                    
        return None
        
    def _extract_author_from_content(self, content: str) -> Optional[str]:
        """从正文内容中提取作者信息"""
        if not content:
            return None
            
        # 查找常见的作者署名模式
        for pattern, group_idx in self.AUTHOR_PATTERNS:
            match = re.search(pattern, content)
            if match:
                author = match.group(group_idx).strip()
                if self._is_valid_author(author):
                    return author
                    
        return None
        
    def _find_author_pattern(self, text: str) -> Optional[str]:
        """在文本中查找可能的作者模式"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # 跳过过长的行
            if len(line) > 100:
                continue
                
            # 查找常见的作者签名模式
            for pattern, group_idx in self.AUTHOR_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    author = match.group(group_idx).strip()
                    if self._is_valid_author(author):
                        return author
                        
        return None
        
    def _is_valid_author(self, author: str) -> bool:
        """判断文本是否可能是有效的作者名"""
        if not author:
            return False
            
        # 过滤过长或过短的文本
        if len(author) < 2 or len(author) > 20:
            return False
            
        # 检查是否包含不可能是作者的字符串
        for non_author in self.NON_AUTHOR_STRINGS:
            if non_author in author:
                return False
                
        # 检查是否包含数字或特殊字符（简单验证）
        if re.search(r'[0-9@#$%^&*/\\]', author):
            return False
            
        return True
        
    def clean_author(self, author: str) -> str:
        """清理作者名"""
        if not author:
            return ""
            
        # 移除常见前缀
        prefixes = ['编辑:', '编辑：', '责任编辑:', '责任编辑：', 
                   '作者:', '作者：', '记者:', '记者：', '文/', '文/']
        for prefix in prefixes:
            if author.startswith(prefix):
                author = author[len(prefix):].strip()
                
        # 移除括号内容，如"张三（实习）"
        author = re.sub(r'\([^)]*\)', '', author)
        author = re.sub(r'（[^）]*）', '', author)
                
        # 移除常见后缀
        suffixes = ['/编辑', '/记者', '/综合']
        for suffix in suffixes:
            if author.endswith(suffix):
                author = author[:-len(suffix)].strip()
                
        return author.strip() 