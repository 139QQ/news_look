#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 图片解析器
提供从不同网站解析新闻图片的功能
"""

import re
import os
import hashlib
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List, Pattern, Tuple, Set

class ImageParser:
    """图片解析器，负责从不同网站的页面中提取图片"""

    # 常用图片容器选择器
    DEFAULT_CONTAINERS = [
        'div.article-content', 'div.main-content', 'div.news-body',
        'div.article-body', 'div.content', 'article', 'div.article',
        'div.post_text', 'div#artibody'
    ]
    
    # 网站特定的图片容器选择器
    SITE_CONTAINERS = {
        '新浪财经': ['div#artibody', 'div.article-content', 'div.blk_container'],
        '东方财富': ['div.newsContent', 'div.Post-RichText', 'div#ContentBody'],
        '网易财经': ['div.post_text', 'div.post_body', 'div#endText'],
        '凤凰财经': ['div.article_content', 'div.main_content', 'div.detailpage']
    }
    
    # 常用缩略图选择器
    THUMBNAIL_SELECTORS = [
        'div.article-thumb img', 'div.news-thumb img', 'div.thumb img',
        'div.article-header img', 'div.header-img img', 'div.topic-img img',
        'div.article-lead img', 'div.lead-img img'
    ]
    
    # 需要忽略的图片URL模式
    IGNORE_PATTERNS = [
        r'\.gif$', r'spacer\.gif', r'blank\.gif', r'dot\.gif', r'pixel\.gif',
        r'icon', r'logo', r'button', r'separator', r'ad', r'banner',
        r'avatar', r'clear\.gif', r'tracker', r'analytics'
    ]
    
    # 最小有效图片尺寸（宽x高），小于这个尺寸的图片会被过滤
    MIN_IMAGE_SIZE = (100, 100)
    
    def __init__(self, site: str = None, base_url: str = None, 
                 save_dir: str = None, min_size: Tuple[int, int] = None):
        """
        初始化图片解析器
        
        Args:
            site: 网站名称，用于选择特定选择器
            base_url: 基础URL，用于转换相对路径
            save_dir: 图片保存目录，如果提供则会保存图片
            min_size: 最小有效图片尺寸(宽,高)，小于此尺寸的图片会被过滤
        """
        self.site = site
        self.base_url = base_url
        self.save_dir = save_dir
        self.min_size = min_size or self.MIN_IMAGE_SIZE
        
        # 如果提供了保存目录，确保目录存在
        if self.save_dir and not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir, exist_ok=True)
        
    def parse(self, html: str, url: str = None) -> List[Dict[str, Any]]:
        """
        从HTML中解析图片
        
        Args:
            html: HTML内容
            url: 页面URL，用于转换相对路径
            
        Returns:
            List[Dict[str, Any]]: 图片信息列表，每个字典包含url, alt, title等字段
        """
        if not html:
            return []
            
        # 如果提供了url但没有提供base_url，则使用url作为base_url
        if url and not self.base_url:
            parsed_url = urlparse(url)
            self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找所有图片，包括缩略图和正文图片
        all_images = self._extract_all_images(soup, url)
        
        # 过滤和处理图片
        valid_images = self._filter_images(all_images)
        
        return valid_images
        
    def _extract_all_images(self, soup: BeautifulSoup, url: str = None) -> List[Dict[str, Any]]:
        """提取页面中的所有图片"""
        images = []
        
        # 1. 先提取缩略图/主图
        thumbnails = self._extract_thumbnails(soup)
        images.extend(thumbnails)
        
        # 2. 再提取文章内容中的图片
        article_content = self._find_article_content(soup)
        if article_content:
            content_images = self._extract_content_images(article_content)
            images.extend(content_images)
        else:
            # 如果找不到文章内容，则从整个页面提取
            all_page_images = self._extract_content_images(soup)
            images.extend(all_page_images)
            
        # 3. 处理图片URL（转换相对路径为绝对路径）
        for img in images:
            if url and not img['url'].startswith(('http://', 'https://', '//')):
                img['url'] = urljoin(url, img['url'])
            elif not img['url'].startswith(('http://', 'https://')) and img['url'].startswith('//'):
                img['url'] = 'https:' + img['url']
            elif self.base_url and not img['url'].startswith(('http://', 'https://', '//')):
                img['url'] = urljoin(self.base_url, img['url'])
                
        return images
        
    def _extract_thumbnails(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """提取页面中的缩略图/主图"""
        thumbnails = []
        
        # 使用缩略图选择器
        for selector in self.THUMBNAIL_SELECTORS:
            thumbnail_imgs = soup.select(selector)
            for img in thumbnail_imgs:
                img_data = self._extract_image_data(img)
                if img_data:
                    img_data['is_thumbnail'] = True
                    thumbnails.append(img_data)
                    
        return thumbnails
        
    def _find_article_content(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """查找文章内容区域"""
        # 构建容器选择器列表
        containers = []
        
        if self.site and self.site in self.SITE_CONTAINERS:
            containers.extend(self.SITE_CONTAINERS[self.site])
            
        containers.extend(self.DEFAULT_CONTAINERS)
        
        # 使用选择器尝试获取内容
        for selector in containers:
            content_elem = soup.select_one(selector)
            if content_elem:
                return content_elem
                
        return None
        
    def _extract_content_images(self, content: BeautifulSoup) -> List[Dict[str, Any]]:
        """从内容区域提取图片"""
        images = []
        
        # 1. 提取常规img标签
        for img in content.find_all('img'):
            img_data = self._extract_image_data(img)
            if img_data:
                img_data['is_thumbnail'] = False
                images.append(img_data)
                
        # 2. 提取带有背景图片的元素
        for elem in content.find_all(style=True):
            style = elem.get('style', '')
            background_match = re.search(r'background(?:-image)?:\s*url\([\'"]?([^\'"]+)[\'"]?\)', style)
            if background_match:
                bg_url = background_match.group(1)
                if bg_url and not self._is_filtered_image(bg_url):
                    images.append({
                        'url': bg_url,
                        'alt': elem.get_text()[:50].strip(),
                        'title': '',
                        'width': '',
                        'height': '',
                        'is_thumbnail': False,
                        'is_background': True
                    })
                    
        return images
        
    def _extract_image_data(self, img_tag) -> Optional[Dict[str, Any]]:
        """从img标签中提取图片数据"""
        # 获取URL
        src = img_tag.get('src', '')
        data_src = img_tag.get('data-src', '')
        data_original = img_tag.get('data-original', '')
        
        # 优先使用data-original和data-src
        url = data_original or data_src or src
        
        if not url or self._is_filtered_image(url):
            return None
            
        # 获取其他属性
        alt = img_tag.get('alt', '').strip()
        title = img_tag.get('title', '').strip()
        width = img_tag.get('width', '')
        height = img_tag.get('height', '')
        
        # 打包图片数据
        return {
            'url': url,
            'alt': alt,
            'title': title,
            'width': width,
            'height': height,
            'is_thumbnail': False,
            'is_background': False
        }
        
    def _is_filtered_image(self, url: str) -> bool:
        """检查图片URL是否应该被过滤"""
        if not url:
            return True
            
        # 检查是否是数据URL
        if url.startswith('data:'):
            return True
            
        # 应用过滤模式
        for pattern in self.IGNORE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
                
        return False
        
    def _filter_images(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤图片，移除重复和无效图片"""
        if not images:
            return []
            
        # 去重
        unique_images = []
        seen_urls = set()
        
        for img in images:
            url = img['url']
            # 标准化URL以便比较
            norm_url = self._normalize_url(url)
            
            if norm_url not in seen_urls:
                seen_urls.add(norm_url)
                unique_images.append(img)
                
        # 尝试按尺寸过滤（如果有尺寸信息）
        filtered_images = []
        for img in unique_images:
            width = img.get('width', '')
            height = img.get('height', '')
            
            try:
                if width and height:
                    w = int(str(width).replace('px', ''))
                    h = int(str(height).replace('px', ''))
                    if w >= self.min_size[0] and h >= self.min_size[1]:
                        filtered_images.append(img)
                    else:
                        # 如果是缩略图，即使尺寸不够也保留
                        if img.get('is_thumbnail', False):
                            filtered_images.append(img)
                else:
                    # 没有尺寸信息，保留图片
                    filtered_images.append(img)
            except (ValueError, TypeError):
                # 尺寸解析错误，保留图片
                filtered_images.append(img)
                
        return filtered_images
        
    def _normalize_url(self, url: str) -> str:
        """标准化URL，移除查询参数和锚点"""
        parsed = urlparse(url)
        # 只保留scheme, netloc和path部分
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
    def save_images(self, images: List[Dict[str, Any]], news_id: str) -> List[Dict[str, Any]]:
        """
        保存图片到本地，并返回更新后的图片信息
        
        Args:
            images: 图片信息列表
            news_id: 新闻ID，用于生成图片文件名
            
        Returns:
            List[Dict[str, Any]]: 更新后的图片信息列表，增加了本地路径信息
        """
        if not self.save_dir or not images:
            return images
            
        # 为新闻创建专门的目录
        news_dir = os.path.join(self.save_dir, news_id)
        os.makedirs(news_dir, exist_ok=True)
        
        # 导入所需库
        import requests
        from PIL import Image
        from io import BytesIO
        import time
        
        # 保存图片
        updated_images = []
        for i, img_data in enumerate(images):
            url = img_data['url']
            
            try:
                # 生成图片文件名
                ext = self._get_image_extension(url)
                filename = f"{i+1}_{self._url_to_filename(url)}{ext}"
                filepath = os.path.join(news_dir, filename)
                
                # 检查文件是否已存在
                if os.path.exists(filepath):
                    # 已存在，直接使用
                    img_data['local_path'] = filepath
                    updated_images.append(img_data)
                    continue
                    
                # 下载图片
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                # 尝试使用PIL打开图片，验证是否是有效的图片
                image = Image.open(BytesIO(response.content))
                
                # 获取实际尺寸
                width, height = image.size
                img_data['width'] = width
                img_data['height'] = height
                
                # 保存图片
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                    
                # 更新图片信息
                img_data['local_path'] = filepath
                updated_images.append(img_data)
                
                # 随机延迟，避免频繁请求
                time.sleep(0.2)  # 200ms延迟
                
            except Exception as e:
                # 记录错误但继续处理其他图片
                print(f"下载图片失败 {url}: {str(e)}")
                continue
                
        return updated_images
        
    def _url_to_filename(self, url: str) -> str:
        """将URL转换为合法的文件名"""
        # 使用URL的哈希作为文件名
        return hashlib.md5(url.encode()).hexdigest()[:12]
        
    def _get_image_extension(self, url: str) -> str:
        """从URL中获取图片扩展名"""
        path = urlparse(url).path
        ext = os.path.splitext(path)[1].lower()
        
        # 如果没有扩展名或扩展名不是常见图片格式，使用默认扩展名
        valid_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return ext if ext in valid_exts else '.jpg' 