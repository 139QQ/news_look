#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 内容解析器
提供从不同网站解析新闻正文内容的功能
"""

import re
from bs4 import BeautifulSoup, Tag, Comment
from typing import Optional, Dict, Any, List, Set, Tuple

class ContentParser:
    """内容解析器，负责从不同网站的页面中提取正文内容"""

    # 常用内容选择器
    DEFAULT_SELECTORS = [
        'div.article-content', 'div.article-body', 'div.main-content',
        'div.news-content', 'div.content', 'article', 'div.article',
        'div.post_text', 'div.main-text', 'div#artibody'
    ]
    
    # 网站特定的内容选择器
    SITE_SELECTORS = {
        '新浪财经': ['div#artibody', 'div.article-content', 'div.article'],
        '东方财富': ['div.newsContent', 'div.article-content', 'div.Post-RichText'],
        '网易财经': ['div.post_text', 'div.post_body', 'div.content'],
        '凤凰财经': ['div.article_content', 'div.main_content', 'div.article-body']
    }
    
    # 需要移除的元素选择器
    REMOVE_SELECTORS = [
        'div.article-bottom', 'div.article-footer', 'div.related-news',
        'div.recommend', 'div.advertisement', 'div.adv', 'div.statement',
        'div.disclaimer', 'div.copyright', 'div.share-box', 'div.author-info',
        'div.comments', 'script', 'style', 'ins', 'iframe',
        'div.pagination', 'ul.pagination', 'div.page-box', 'div.pages',
        'div.footer', 'div.article-actions', 'div.toolbar', 'div#articleEdit',
        'div.keytags', 'div.tag-list', 'div.subject-list'
    ]
    
    # 广告或无用内容的正则表达式模式
    AD_PATTERNS = [
        r'相关推荐[：:]?', r'推荐阅读[：:]?', r'相关阅读[：:]?', r'更多精彩内容[：:]?',
        r'更多[：:]?', r'责任编辑[：:].*?[\n]', r'【免责声明】.*$', r'来源[：:].*?[\n]', 
        r'原标题[：:].*?[\n]', r'编辑[：:].*?[\n]', r'作者[：:].*?[\n]',
        r'本文来源[：:].*?[\n]', r'【.*?声明.*?】.*$', r'版权声明.*$',
        r'点击查看更多', r'扫描下方二维码', r'关注我们的微信', r'加入我们的.*?群',
        r'[\s\n]*原文链接：http.*$'
    ]
    
    # 章节分隔符的正则表达式
    SECTION_PATTERNS = [
        r'一、', r'二、', r'三、', r'四、', r'五、', r'六、', r'七、', r'八、', r'九、', r'十、',
        r'1\.', r'2\.', r'3\.', r'4\.', r'5\.', r'6\.', r'7\.', r'8\.', r'9\.', r'10\.',
        r'（一）', r'（二）', r'（三）', r'（四）', r'（五）', r'（六）', r'（七）', r'（八）'
    ]
    
    def __init__(self, site: str = None, custom_selectors: List[str] = None, 
                 custom_removers: List[str] = None, min_text_length: int = 50,
                 max_noise_density: float = 0.4):
        """
        初始化内容解析器
        
        Args:
            site: 网站名称，用于选择特定选择器
            custom_selectors: 自定义选择器列表
            custom_removers: 自定义需要移除的元素选择器
            min_text_length: 最小文本长度，小于此长度的段落将被忽略
            max_noise_density: 最大噪音密度，超过此密度的段落将被忽略
        """
        self.site = site
        self.custom_selectors = custom_selectors or []
        self.custom_removers = custom_removers or []
        self.min_text_length = min_text_length
        self.max_noise_density = max_noise_density
        
    def parse(self, html: str) -> Optional[str]:
        """
        从HTML中解析正文内容
        
        Args:
            html: HTML内容
            
        Returns:
            str: 解析到的正文内容，如果未解析到则返回None
        """
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 尝试使用特定选择器提取内容
        content_html = self._extract_content_by_selectors(soup)
        if content_html:
            return self._clean_content(content_html)
            
        # 2. 尝试使用正文提取算法提取内容
        content_html = self._extract_content_by_density(soup)
        if content_html:
            return self._clean_content(content_html)
            
        # 3. 如果前两种方法都失败，尝试从正文中提取最长的p段落作为内容
        paragraphs = []
        for p in soup.find_all('p'):
            # 忽略script和style中的p标签
            if p.parent and p.parent.name in ['script', 'style']:
                continue
                
            text = p.get_text().strip()
            if text and len(text) > self.min_text_length:
                paragraphs.append(text)
                
        if paragraphs:
            return '\n\n'.join(paragraphs)
            
        return None
        
    def _extract_content_by_selectors(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """使用预定义的选择器提取内容"""
        # 构建选择器列表
        selectors = self.custom_selectors.copy()
        
        if self.site and self.site in self.SITE_SELECTORS:
            selectors.extend(self.SITE_SELECTORS[self.site])
            
        selectors.extend(self.DEFAULT_SELECTORS)
        
        # 使用选择器尝试获取内容
        for selector in selectors:
            content_elem = soup.select_one(selector)
            if content_elem and self._is_valid_content(content_elem):
                # 深度复制，避免修改原始soup
                content_copy = BeautifulSoup(str(content_elem), 'html.parser')
                # 清理无用元素
                self._remove_noise_elements(content_copy)
                return content_copy
                
        return None
        
    def _extract_content_by_density(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """使用文本密度算法提取内容"""
        # 移除垃圾元素
        self._remove_noise_elements(soup)
        
        # 计算各个标签的文本密度
        density_map = {}
        for tag in soup.find_all(['div', 'article', 'section']):
            # 忽略隐藏元素
            if self._is_hidden_element(tag):
                continue
                
            # 计算密度：文本长度/标签长度
            text_length = len(tag.get_text())
            html_length = len(str(tag))
            
            if html_length > 0:
                density = text_length / html_length
                child_count = len(tag.find_all())
                
                # 通过密度、文本长度和子元素数量计算得分
                score = density * (1 + min(child_count / 10, 1)) * min(text_length / 500, 3)
                density_map[tag] = score
        
        # 如果没有找到任何元素，返回None
        if not density_map:
            return None
            
        # 找到得分最高的元素
        main_content = max(density_map.items(), key=lambda x: x[1])[0]
        
        # 复制元素，避免修改原始soup
        content_copy = BeautifulSoup(str(main_content), 'html.parser')
        
        # 进一步清理
        self._remove_noise_elements(content_copy)
        
        return content_copy
        
    def _is_valid_content(self, element: Tag) -> bool:
        """检查元素是否为有效的内容元素"""
        # 内容必须包含足够的文本
        text = element.get_text().strip()
        if len(text) < self.min_text_length * 3:  # 至少三个段落的长度
            return False
            
        # 内容必须包含段落标签
        if not element.find_all(['p', 'div', 'section', 'article']):
            return False
            
        # 计算可能的噪音比例
        noise_count = self._count_noise_elements(element)
        total_elements = len(element.find_all())
        
        if total_elements > 0:
            noise_ratio = noise_count / total_elements
            if noise_ratio > self.max_noise_density:
                return False
                
        return True
        
    def _count_noise_elements(self, element: Tag) -> int:
        """计算元素中的噪音元素数量"""
        count = 0
        # 合并系统和自定义的移除选择器
        all_removers = self.REMOVE_SELECTORS + self.custom_removers
        
        for selector in all_removers:
            count += len(element.select(selector))
            
        # 计算注释、script和style标签
        count += len(element.find_all(['script', 'style']))
        count += len(element.find_all(string=lambda text: isinstance(text, Comment)))
        
        return count
        
    def _remove_noise_elements(self, soup: BeautifulSoup) -> None:
        """移除噪音元素"""
        # 合并系统和自定义的移除选择器
        all_removers = self.REMOVE_SELECTORS + self.custom_removers
        
        # 移除选择器匹配的元素
        for selector in all_removers:
            for element in soup.select(selector):
                element.decompose()
                
        # 移除注释
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            
        # 移除空元素
        for tag in soup.find_all():
            if not tag.get_text().strip() and tag.name not in ['img', 'br', 'hr']:
                tag.decompose()
                
        # 移除隐藏元素
        for tag in soup.find_all():
            if self._is_hidden_element(tag):
                tag.decompose()
                
    def _is_hidden_element(self, tag: Tag) -> bool:
        """检查元素是否被隐藏"""
        style = tag.get('style', '').lower()
        classes = ' '.join(tag.get('class', [])).lower()
        
        # 通过样式检查
        if 'display: none' in style or 'visibility: hidden' in style:
            return True
            
        # 通过类名检查
        hidden_classes = ['hidden', 'hide', 'invisible', 'display-none']
        for cls in hidden_classes:
            if cls in classes:
                return True
                
        return False
        
    def _clean_content(self, content_soup: BeautifulSoup) -> str:
        """清理和格式化提取的内容"""
        # 获取文本内容
        text = content_soup.get_text('\n', strip=True)
        
        # 清理无用文本
        for pattern in self.AD_PATTERNS:
            text = re.sub(pattern, '', text)
            
        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 分段处理
        paragraphs = []
        for para in text.split('\n'):
            para = para.strip()
            if para and len(para) >= self.min_text_length:
                paragraphs.append(para)
                
        # 合并段落
        result = '\n\n'.join(paragraphs)
        
        return result 