#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 标题解析器
提供从不同网站解析新闻标题的功能
"""

import re
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List, Pattern

class TitleParser:
    """标题解析器，负责从不同网站的页面中提取标题"""

    # 常用标题选择器
    DEFAULT_SELECTORS = [
        'h1.title', 'h1.article-title', 'h1.main-title', 
        'h1.content-title', 'h1#article-title', 'h1.news-title',
        'div.article-title h1', 'div.news-title h1'
    ]
    
    # 网站特定的标题选择器
    SITE_SELECTORS = {
        '新浪财经': ['h1.main-title', 'h1#artibodyTitle', 'div.article h1'],
        '东方财富': ['div.newsContent h1', 'h1.title', 'div.detail-title h1'],
        '网易财经': ['h1.post_title', 'h1.title', 'div.post_content_main h1'],
        '凤凰财经': ['h1.article-title', 'div.article-title h1', 'div.titleArea h1']
    }
    
    # 标题清理正则表达式列表
    CLEAN_PATTERNS = [
        (r'原标题[:：]', ''),  # 删除"原标题："前缀
        (r'独家[:：]', ''),    # 删除"独家："前缀
        (r'专访[:：]', ''),    # 删除"专访："前缀
        (r'快讯[:：]', ''),    # 删除"快讯："前缀
        (r'最新[:：]', ''),    # 删除"最新："前缀
        (r'突发[:：]', ''),    # 删除"突发："前缀
        (r'【.*?】', ''),      # 删除【】中的内容
        (r'\s+', ' ')         # 压缩多个空格为一个
    ]
    
    def __init__(self, site: str = None, custom_selectors: List[str] = None):
        """
        初始化标题解析器
        
        Args:
            site: 网站名称，用于选择特定选择器
            custom_selectors: 自定义选择器列表
        """
        self.site = site
        self.custom_selectors = custom_selectors or []
        
    def parse(self, html: str) -> Optional[str]:
        """
        从HTML中解析标题
        
        Args:
            html: HTML内容
            
        Returns:
            str: 解析到的标题，如果未解析到则返回None
        """
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 构建选择器列表，优先使用自定义选择器，然后是网站特定选择器，最后是默认选择器
        selectors = self.custom_selectors.copy()
        
        if self.site and self.site in self.SITE_SELECTORS:
            selectors.extend(self.SITE_SELECTORS[self.site])
            
        selectors.extend(self.DEFAULT_SELECTORS)
        
        # 使用选择器尝试获取标题
        for selector in selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                if title:
                    return self.clean_title(title)
                    
        # 如果选择器方法未能获取标题，尝试其他方法
        # 1. 尝试获取title标签内容
        title_tag = soup.title
        if title_tag:
            site_names = [
                '新浪财经', '东方财富', '网易财经', '凤凰财经',
                '新浪', '东方', '网易', '凤凰', '财经', '股票'
            ]
            title = title_tag.get_text().strip()
            
            # 清理网站名称
            for name in site_names:
                title = title.replace(f' - {name}', '')
                title = title.replace(f'_{name}', '')
                title = title.replace(f'-{name}', '')
                
            if title:
                return self.clean_title(title)
                
        # 2. 查找大字体标题（通常h1或字体较大的div）
        for h1 in soup.find_all('h1'):
            title = h1.get_text().strip()
            if title and len(title) > 5 and len(title) < 100:  # 合理的标题长度
                return self.clean_title(title)
                
        return None
        
    def clean_title(self, title: str) -> str:
        """
        清理标题，删除无用前缀和格式化
        
        Args:
            title: 原始标题
            
        Returns:
            str: 清理后的标题
        """
        if not title:
            return ""
            
        # 应用清理模式
        cleaned_title = title.strip()
        for pattern, replacement in self.CLEAN_PATTERNS:
            cleaned_title = re.sub(pattern, replacement, cleaned_title)
            
        return cleaned_title.strip() 