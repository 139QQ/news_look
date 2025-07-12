#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文本清洗工具模块 - 用于处理乱码问题和格式化文本
"""

import re
import html
from bs4 import BeautifulSoup, Comment
from typing import Optional

def clean_text(text: str) -> str:
    """
    清理文本中的乱码和特殊字符
    
    Args:
        text (str): 需要清理的文本
        
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    
    # 尝试解决Unicode编码问题
    try:
        # 检查是否是Unicode转义字符
        if '\\u' in text:
            text = text.encode('utf-8').decode('unicode_escape')
        
        # 检查是否是URL编码
        if '%' in text and any(c in text for c in ['%20', '%E', '%C', '%D']):
            import urllib.parse
            text = urllib.parse.unquote(text)
    except Exception:
        pass  # 如果转换失败，继续使用原始文本
    
    # 替换常见乱码字符
    replacements = {
        'æ': '-',
        'ç': ':',
        '¥': ' ',
        'â': '',
        'ä': 'a',
        'ë': 'e',
        'ï': 'i',
        'ö': 'o',
        'ü': 'u',
        '€': '元',
        '£': '英镑',
        '¢': '分',
        '°': '度',
        '©': '',
        '®': '',
        '™': '',
        '·': '·',
        '…': '...',
        '—': '-',
        '–': '-',
        ''': "'",
        ''': "'",
        '"': '"',
        '"': '"',
        '„': '"',
        '«': '"',
        '»': '"',
        '‹': "'",
        '›': "'",
        '≈': '约等于',
        '≠': '不等于',
        '≤': '小于等于',
        '≥': '大于等于',
        '×': 'x',
        '÷': '/',
        '←': '<-',
        '→': '->',
        '↑': '上',
        '↓': '下',
        '↔': '<->',
        '♠': '黑桃',
        '♣': '梅花',
        '♥': '红心',
        '♦': '方块',
        '★': '*',
        '☆': '*',
        '■': '■',
        '□': '□',
        '▲': '▲',
        '△': '△',
        '●': '●',
        '○': '○',
        '◆': '◆',
        '◇': '◇',
        '◎': '◎',
        '§': '§',
        '¶': '¶',
        '†': '+',
        '‡': '++',
        '‰': '千分之',
        '‱': '万分之',
        'Æ': 'AE',
        'Œ': 'OE',
        'æ': 'ae',
        'œ': 'oe',
        'ß': 'ss',
        'Ø': 'O',
        'ø': 'o',
        'Å': 'A',
        'å': 'a',
        '\u003c': '<',
        '\u003e': '>',
        '\u0026': '&',
        '\u2019': "'",
        '\u2018': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u00a0': ' ',
        '\t': ' ',
        # 特殊处理HTML字符实体
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&apos;': "'",
        '&nbsp;': ' '
    }
    
    # 处理Unicode字符
    if '\\u' in text:
        try:
            text = text.encode().decode('unicode_escape')
        except:
            pass
            
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # 移除不可见字符（保留换行符）
    text = ''.join(c for c in text if ord(c) >= 32 or c == '\n')
    
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 解码HTML实体
    text = html.unescape(text)
    
    return text

def clean_html_content(html_content):
    """
    清理HTML内容，返回格式化的纯文本
    
    Args:
        html_content: HTML内容或BeautifulSoup对象
        
    Returns:
        str: 清理后的文本
    """
    if not html_content:
        return ""
    
    # 如果输入不是BeautifulSoup对象，创建一个
    if not isinstance(html_content, BeautifulSoup):
        soup = BeautifulSoup(str(html_content), 'html.parser')
    else:
        soup = html_content
    
    # 移除可能导致问题的标签
    for tag in soup(["script", "style", "iframe", "noscript", "head", "meta", "link"]):
        tag.decompose()
    
    # 移除所有注释
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    # 获取文本
    text = soup.get_text(separator="\n", strip=True)
    
    # 使用clean_text进一步处理
    return clean_text(text)

def format_news_content(content: str, max_length: Optional[int] = None) -> str:
    """
    格式化新闻内容，清理乱码并截断到指定长度
    
    Args:
        content (str): 新闻内容
        max_length (int, optional): 最大长度，如果为None则不截断
        
    Returns:
        str: 格式化后的内容
    """
    if not content:
        return "暂无内容摘要"
    
    # 清理文本
    cleaned_content = clean_text(content)
    
    # 如果内容仍然包含乱码，返回默认文本
    if any(c in cleaned_content for c in ['æ', 'ç', '¥', 'â', 'ä', 'ë']):
        return "内容解析中..."
    
    # 截断内容
    if max_length and len(cleaned_content) > max_length:
        # 尝试在句子结束处截断
        sentence_end = cleaned_content.rfind('。', 0, max_length)
        if sentence_end > max_length * 0.7:  # 如果找到的句子结束位置不太靠前
            return cleaned_content[:sentence_end+1] + "..."
        else:
            return cleaned_content[:max_length] + "..."
    
    return cleaned_content

def format_datetime(date_str: str) -> str:
    """
    格式化日期时间字符串
    
    Args:
        date_str (str): 日期时间字符串
        
    Returns:
        str: 格式化后的日期时间
    """
    if not date_str:
        return "未知时间"
    
    # 清理日期字符串中的乱码
    date_str = clean_text(date_str)
    
    # 尝试解析不同格式的日期
    try:
        # 尝试解析标准格式 (YYYY-MM-DD)
        if re.match(r'\d{4}-\d{1,2}-\d{1,2}', date_str):
            match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
            if match:
                year, month, day = match.groups()
                return f"{year}年{month}月{day}日"
        
        # 尝试解析标准格式 (YYYY/MM/DD)
        if re.match(r'\d{4}/\d{1,2}/\d{1,2}', date_str):
            match = re.match(r'(\d{4})/(\d{1,2})/(\d{1,2})', date_str)
            if match:
                year, month, day = match.groups()
                return f"{year}年{month}月{day}日"
        
        # 尝试解析月日格式 (MM-DD)
        if re.match(r'\d{1,2}-\d{1,2}', date_str):
            match = re.match(r'(\d{1,2})-(\d{1,2})', date_str)
            if match:
                month, day = match.groups()
                return f"{month}月{day}日"
        
        # 尝试解析月日格式 (MM/DD)
        if re.match(r'\d{1,2}/\d{1,2}', date_str):
            match = re.match(r'(\d{1,2})/(\d{1,2})', date_str)
            if match:
                month, day = match.groups()
                return f"{month}月{day}日"
        
        # 如果已经是中文格式，直接返回
        if '月' in date_str and '日' in date_str:
            return date_str
        
        # 尝试从乱码中提取数字
        numbers = re.findall(r'\d+', date_str)
        if len(numbers) >= 2:
            # 假设前两个数字是月和日
            return f"{numbers[0]}月{numbers[1]}日"
    
    except Exception as e:
        print(f"日期格式化错误: {e}")
    
    # 如果无法解析，返回默认值
    return "最近更新"

def extract_keywords(text: str, max_keywords: int = 5) -> str:
    """
    从文本中提取关键词
    
    Args:
        text (str): 文本内容
        max_keywords (int): 最大关键词数量
        
    Returns:
        str: 逗号分隔的关键词
    """
    try:
        import jieba.analyse
        
        # 清理文本
        cleaned_text = clean_text(text)
        
        # 提取关键词
        keywords = jieba.analyse.extract_tags(cleaned_text, topK=max_keywords)
        
        return ','.join(keywords)
    except Exception as e:
        print(f"关键词提取错误: {e}")
        return ""

def is_valid_content(content: str, min_length: int = 50) -> bool:
    """
    判断内容是否有效（不是广告、不是过短的内容等）
    
    Args:
        content (str): 内容
        min_length (int): 最小有效长度
        
    Returns:
        bool: 是否有效
    """
    if not content:
        return False
    
    # 清理内容
    cleaned_content = clean_text(content)
    
    # 检查长度
    if len(cleaned_content) < min_length:
        return False
    
    # 检查是否包含广告关键词
    ad_keywords = ['广告', '推广', '点击查看', '点击购买', '联系电话', '咨询热线', 
                  '优惠券', '折扣码', '限时优惠', '抢购', '秒杀']
    
    for keyword in ad_keywords:
        if keyword in cleaned_content:
            return False
    
    return True 