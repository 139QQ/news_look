#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 文本清理工具
"""

import re
import jieba
import jieba.analyse
from app.utils.logger import get_logger
from bs4 import BeautifulSoup
import html
from datetime import datetime, timedelta
import unicodedata

# 设置日志记录器
logger = get_logger('text_cleaner')

def clean_html(html_text):
    """
    清理HTML文本，去除HTML标签和多余的空白字符
    
    Args:
        html_text: HTML文本
    
    Returns:
        str: 清理后的文本
    """
    if not html_text:
        return ""
    
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', html_text)
    
    # 去除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 去除特殊字符
    text = re.sub(r'[\r\n\t]', '', text)
    
    return text.strip()

def extract_keywords(text, topK=10):
    """
    提取文本中的关键词
    
    Args:
        text: 文本
        topK: 提取的关键词数量
    
    Returns:
        list: 关键词列表
    """
    if not text:
        return []
    
    # 使用jieba提取关键词
    keywords = jieba.analyse.extract_tags(text, topK=topK)
    
    return keywords

def normalize_text(text):
    """
    规范化文本，去除特殊字符，转换为小写
    
    Args:
        text: 文本
    
    Returns:
        str: 规范化后的文本
    """
    if not text:
        return ""
    
    # 去除特殊字符
    text = re.sub(r'[^\w\s]', '', text)
    
    # 转换为小写
    text = text.lower()
    
    return text.strip()

def remove_stopwords(text, stopwords=None):
    """
    去除停用词
    
    Args:
        text: 文本
        stopwords: 停用词列表
    
    Returns:
        str: 去除停用词后的文本
    """
    if not text:
        return ""
    
    if not stopwords:
        # 默认停用词
        stopwords = ['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这']
    
    # 分词
    words = jieba.cut(text)
    
    # 去除停用词
    filtered_words = [word for word in words if word not in stopwords and len(word.strip()) > 0]
    
    return ' '.join(filtered_words)

def clean_text(text):
    """
    清理文本，去除多余空白字符和HTML实体
    
    Args:
        text: 原始文本
    
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    
    # 解码HTML实体
    text = html.unescape(text)
    
    # 去除多余空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 去除首尾空白
    text = text.strip()
    
    # 规范化Unicode字符
    text = unicodedata.normalize('NFKC', text)
    
    return text

def clean_html_content(content_elem):
    """
    清理HTML内容，去除广告、无关内容等
    
    Args:
        content_elem: BeautifulSoup元素
    
    Returns:
        str: 清理后的内容
    """
    if not content_elem:
        return ""
    
    # 复制元素，避免修改原始元素
    content = BeautifulSoup(str(content_elem), 'html.parser')
    
    # 移除脚本和样式
    for script in content.find_all(['script', 'style']):
        script.decompose()
    
    # 移除广告相关元素
    ad_classes = ['ad', 'advertisement', 'banner', 'recommend', 'related', 'footer', 'copyright']
    for ad_class in ad_classes:
        for elem in content.find_all(class_=lambda c: c and ad_class in c.lower()):
            elem.decompose()
    
    # 移除分享按钮
    share_classes = ['share', 'social', 'bshare']
    for share_class in share_classes:
        for elem in content.find_all(class_=lambda c: c and share_class in c.lower()):
            elem.decompose()
    
    # 获取文本
    text = content.get_text(separator='\n')
    
    # 清理文本
    text = clean_text(text)
    
    return text

def format_news_content(content):
    """
    格式化新闻内容，分段落、去除广告等
    
    Args:
        content: 原始内容
    
    Returns:
        str: 格式化后的内容
    """
    if not content:
        return ""
    
    # 分段落
    paragraphs = re.split(r'\n+', content)
    
    # 清理每个段落
    cleaned_paragraphs = []
    for p in paragraphs:
        # 清理段落
        p = clean_text(p)
        
        # 跳过空段落
        if not p:
            continue
        
        # 跳过广告段落
        ad_patterns = [
            r'广告',
            r'推广',
            r'更多精彩',
            r'点击查看',
            r'关注我们',
            r'扫描二维码',
            r'责任编辑',
            r'声明[：:]',
            r'免责声明',
            r'版权声明',
            r'原标题[：:]',
            r'来源[：:]',
            r'作者[：:]',
            r'编辑[：:]'
        ]
        if any(re.search(pattern, p) for pattern in ad_patterns):
            continue
        
        # 添加到清理后的段落
        cleaned_paragraphs.append(p)
    
    # 合并段落
    return '\n\n'.join(cleaned_paragraphs)

def format_datetime(date_str):
    """
    格式化日期时间字符串为标准格式
    
    Args:
        date_str: 日期时间字符串
    
    Returns:
        str: 标准格式的日期时间字符串，格式为'YYYY-MM-DD HH:MM:SS'
    """
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 清理日期字符串
    date_str = clean_text(date_str)
    
    # 常见的日期格式
    patterns = [
        # 标准格式
        (r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})', 
         lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} {int(m.group(4)):02d}:{int(m.group(5)):02d}:{int(m.group(6)):02d}"),
        
        # 标准格式，无秒
        (r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{1,2})', 
         lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} {int(m.group(4)):02d}:{int(m.group(5)):02d}:00"),
        
        # 中文格式，带年月日时分秒
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})[:：](\d{1,2})[:：](\d{1,2})', 
         lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} {int(m.group(4)):02d}:{int(m.group(5)):02d}:{int(m.group(6)):02d}"),
        
        # 中文格式，带年月日时分
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})[:：](\d{1,2})', 
         lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} {int(m.group(4)):02d}:{int(m.group(5)):02d}:00"),
        
        # 中文格式，带年月日
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日', 
         lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} 00:00:00"),
        
        # 简化格式，月日时分
        (r'(\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{1,2})', 
         lambda m: f"{datetime.now().year}-{int(m.group(1)):02d}-{int(m.group(2)):02d} {int(m.group(3)):02d}:{int(m.group(4)):02d}:00"),
        
        # 相对时间，几小时前
        (r'(\d+)小时前', 
         lambda m: (datetime.now() - timedelta(hours=int(m.group(1)))).strftime('%Y-%m-%d %H:%M:%S')),
        
        # 相对时间，几分钟前
        (r'(\d+)分钟前', 
         lambda m: (datetime.now() - timedelta(minutes=int(m.group(1)))).strftime('%Y-%m-%d %H:%M:%S')),
        
        # 今天、昨天
        (r'今天\s*(\d{1,2}):(\d{1,2})', 
         lambda m: f"{datetime.now().strftime('%Y-%m-%d')} {int(m.group(1)):02d}:{int(m.group(2)):02d}:00"),
        
        (r'昨天\s*(\d{1,2}):(\d{1,2})', 
         lambda m: f"{(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')} {int(m.group(1)):02d}:{int(m.group(2)):02d}:00")
    ]
    
    # 尝试匹配各种格式
    for pattern, formatter in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                return formatter(match)
            except Exception:
                continue
    
    # 如果无法解析，返回当前时间
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S') 