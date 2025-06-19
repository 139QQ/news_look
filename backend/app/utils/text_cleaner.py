#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 文本清理工具
"""

import re
import jieba
import jieba.analyse
from backend.app.utils.logger import get_logger
from bs4 import BeautifulSoup
import html
import urllib.parse
from datetime import datetime, timedelta
import unicodedata

# 设置日志记录器
logger = get_logger('text_cleaner')

# 扩展替换字典，处理常见的特殊字符
REPLACE_DICT = {
    '&nbsp;': ' ', 
    '&quot;': '"', 
    '&amp;': '&', 
    '&lt;': '<', 
    '&gt;': '>', 
    '&ldquo;': '"', 
    '&rdquo;': '"', 
    '&#39;': "'", 
    '&#160;': ' ',
    '&#8220;': '"',
    '&#8221;': '"',
    '&#8230;': '...',
    '&#8216;': ''',
    '&#8217;': ''',
    '&#8226;': '•',
    '&mdash;': '—',
    '&ndash;': '–',
    '&hellip;': '...',
    '\xa0': ' ',
    '\u3000': ' ',  # 全角空格
    '\r': '',
    '\t': ' ',
}

class TextCleaner:
    """文本清理与格式化工具类"""
    
    @staticmethod
    def clean_html(html_content):
        """清理HTML内容，移除多余标签但保留基本结构"""
        if not html_content:
            return ""
            
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除无用标签
        for tag in soup.find_all(['script', 'style', 'iframe', 'nav', 'header', 'footer']):
            tag.decompose()
            
        return str(soup)
    
    @staticmethod
    def html_to_text(html_content):
        """将HTML转换为纯文本，保留基本格式"""
        if not html_content:
            return ""
            
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        return text
    
    @staticmethod
    def normalize_whitespace(text):
        """标准化空白字符"""
        if not text:
            return ""
            
        # 替换多个空白字符为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 替换多个换行为两个换行（形成段落）
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    @staticmethod
    def decode_html_entities(text):
        """解码HTML实体"""
        if not text:
            return ""
            
        return html.unescape(text)
    
    @staticmethod
    def normalize_unicode(text):
        """Unicode标准化，处理特殊字符"""
        if not text:
            return ""
            
        return unicodedata.normalize('NFKC', text)
    
    @staticmethod
    def remove_ads_text(text, ad_patterns=None):
        """移除广告文本"""
        if not text:
            return ""
            
        default_patterns = [
            r'版权声明：.*?$',
            r'原标题：.*?$',
            r'来源：.*?$',
            r'编辑：.*?$',
            r'关注我们：.*?$',
            r'扫码关注.*?$',
            r'更多精彩内容.*?$',
            r'点击查看.*?$',
            r'责任编辑：.*?$',
            r'本文来源.*?$'
        ]
        
        patterns = ad_patterns or default_patterns
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)
        
        return text
    
    @staticmethod
    def format_paragraphs(text, min_length=20):
        """
        智能格式化段落，提升阅读体验
        
        参数:
            text (str): 要处理的文本
            min_length (int): 最小段落长度
            
        返回:
            str: 格式化后的HTML段落
        """
        if not text:
            return ""
        
        # 预处理：修复可能的段落边界
        text = re.sub(r'([。！？!?])\s*', r'\1\n', text)  # 在句号、感叹号、问号后添加换行
        
        # 分割成段落
        raw_paragraphs = text.split('\n')
        formatted_paragraphs = []
        
        current_p = ""
        for line in raw_paragraphs:
            line = line.strip()
            if not line:
                if current_p:
                    formatted_paragraphs.append(current_p)
                    current_p = ""
                continue
                
            # 判断是否是新段落的开始
            if len(line) < min_length and line.endswith(('。', '！', '？', '.', '!', '?')):
                # 短句结尾作为独立段落
                if current_p:
                    formatted_paragraphs.append(current_p)
                formatted_paragraphs.append(line)
                current_p = ""
            elif current_p and (current_p.endswith(('。', '！', '？', '.', '!', '?')) or 
                               len(current_p) > 200):
                # 当前段已结束或过长，开始新段落
                formatted_paragraphs.append(current_p)
                current_p = line
            else:
                # 继续当前段落
                if current_p:
                    current_p += " " + line
                else:
                    current_p = line
        
        # 添加最后一个段落
        if current_p:
            formatted_paragraphs.append(current_p)
        
        # 生成HTML段落
        html_content = ""
        for p in formatted_paragraphs:
            p = p.strip()
            if p:
                html_content += f"<p>{p}</p>\n"
        
        return html_content
    
    @staticmethod
    def enhance_text_with_formatting(text):
        """增强文本格式化，添加段落、强调和引用样式"""
        if not text:
            return ""
            
        # 处理加粗文本
        text = re.sub(r'"([^"]+)"', r'<strong>"\1"</strong>', text)
        
        # 处理引用
        text = re.sub(r'^>(.+)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)
        
        # 识别并格式化列表
        list_pattern = re.compile(r'^\s*[•·-]\s+(.+)$', re.MULTILINE)
        if list_pattern.search(text):
            list_items = []
            for match in list_pattern.finditer(text):
                list_items.append(f"<li>{match.group(1)}</li>")
            if list_items:
                list_html = "<ul>\n" + "\n".join(list_items) + "\n</ul>"
                text = list_pattern.sub('', text)  # 移除原列表项
                text += "\n" + list_html
        
        return text
    
    @staticmethod
    def process_content_for_display(content):
        """
        处理内容用于显示，集成所有格式化功能
        
        参数:
            content (str): 原始内容文本或HTML
            
        返回:
            str: 格式化后的HTML内容
        """
        if not content:
            return ""
        
        # 判断内容类型（HTML或纯文本）
        is_html = bool(re.search(r'<[a-z]+[^>]*>', content))
        
        if is_html:
            # 清理HTML
            content = TextCleaner.clean_html(content)
        else:
            # 纯文本处理
            content = TextCleaner.decode_html_entities(content)
            content = TextCleaner.normalize_unicode(content)
            content = TextCleaner.normalize_whitespace(content)
            content = TextCleaner.remove_ads_text(content)
            
            # 格式化段落
            content = TextCleaner.format_paragraphs(content)
            
            # 增强格式
            content = TextCleaner.enhance_text_with_formatting(content)
        
        # 为图片添加响应式类
        if is_html:
            soup = BeautifulSoup(content, 'html.parser')
            for img in soup.find_all('img'):
                img_classes = img.get('class', [])
                if isinstance(img_classes, str):
                    img_classes = [img_classes]
                if 'img-fluid' not in img_classes:
                    img_classes.append('img-fluid')
                if 'rounded' not in img_classes:
                    img_classes.append('rounded')
                img['class'] = img_classes
                
                # 添加懒加载
                if not img.get('loading'):
                    img['loading'] = 'lazy'
                    
            content = str(soup)
        
        return content

    @staticmethod
    def clean_text(text):
        """基础文本清理"""
        if not text:
            return text
        
        # 基本清理
        text = text.strip()
        
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text)
        
        return text

    @staticmethod
    def remove_browser_tips(text):
        """去除浏览器升级提示消息"""
        if not text:
            return text
            
        # 凤凰网浏览器提示
        text = re.sub(r'亲爱的凤凰网用户[\s\S]*?浏览器.*?下载', '', text)
        
        # 新浪财经浏览器提示
        text = re.sub(r'您的浏览器不支持.*?请升级浏览器', '', text)
        
        # 其他网站的通用浏览器提示
        text = re.sub(r'您当前使用的浏览器版本过低.*?下载', '', text)
        text = re.sub(r'建议使用.*?浏览器访问本.*?下载', '', text)
        
        return text
    
    @staticmethod
    def extract_keywords(text, top_k=5):
        """从文本中提取关键词"""
        if not text:
            return []
        
        # 使用jieba提取关键词
        keywords = jieba.analyse.extract_tags(text, topK=top_k)
        return keywords

def decode_html_entities(text):
    """
    解码HTML实体，如 &lt; -> <, &quot; -> ", &amp; -> &
    
    Args:
        text: 包含HTML实体的文本
        
    Returns:
        str: 解码后的文本
    """
    if not text:
        return ""
    
    # 使用Python标准库html模块解码HTML实体
    return html.unescape(text)

def decode_unicode_escape(text):
    """
    解码Unicode转义序列，如 \u4e2d\u56fd -> 中国
    
    Args:
        text: 包含Unicode转义序列的文本
        
    Returns:
        str: 解码后的文本
    """
    if not text:
        return ""
    
    # 查找所有的Unicode转义序列并解码
    try:
        if '\\u' in text:
            text = text.encode('utf-8').decode('unicode_escape')
    except Exception:
        # 如果解码失败，使用正则表达式逐个处理
        pattern = r'\\u([0-9a-fA-F]{4})'
        
        def replace(match):
            try:
                return chr(int(match.group(1), 16))
            except:
                return match.group(0)
        
        text = re.sub(pattern, replace, text)
    
    return text

def decode_url_encoded(text):
    """
    解码URL编码的字符，如 %E4%B8%AD%E5%9B%BD -> 中国
    
    Args:
        text: 包含URL编码字符的文本
        
    Returns:
        str: 解码后的文本
    """
    if not text:
        return ""
    
    # 检测是否含有URL编码的特征
    if '%' in text and any(c in text for c in ['%20', '%E', '%C', '%D']):
        try:
            # 使用urllib.parse模块解码URL编码
            text = urllib.parse.unquote(text)
        except Exception:
            pass  # 解码失败，保持原样
    
    return text

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
    
    # 解码文本中可能存在的各种编码
    text = html_text
    text = decode_html_entities(text)
    text = decode_unicode_escape(text)
    text = decode_url_encoded(text)
    
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
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
    
    # 解码各种编码
    text = decode_html_entities(text)
    text = decode_unicode_escape(text)
    text = decode_url_encoded(text)
    
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
    
    # 解码各种编码
    text = decode_html_entities(text)
    text = decode_unicode_escape(text)
    text = decode_url_encoded(text)
    
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
    
    # 解码各种编码
    content = decode_html_entities(content)
    content = decode_unicode_escape(content)
    content = decode_url_encoded(content)
    
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

def clean_text(text):
    """简便函数：清理和标准化文本"""
    return TextCleaner.normalize_whitespace(
        TextCleaner.decode_html_entities(
            TextCleaner.normalize_unicode(text)
        )
    )


def html_to_clean_text(html_content):
    """简便函数：将HTML转换为清理后的纯文本"""
    return TextCleaner.normalize_whitespace(
        TextCleaner.html_to_text(html_content)
    )


def format_for_display(content):
    """格式化文本以便在网页中显示"""
    if not content:
        return ""
    
    # 首先清理文本
    content = TextCleaner.clean_text(content)
    
    # 移除浏览器提示
    content = TextCleaner.remove_browser_tips(content)
    
    # 处理HTML内容
    if not content.strip().startswith('<'):
        # 如果不是HTML格式，进行基本格式化
        content = content.replace('\n', '<br/>')
    else:
        # 如果是HTML内容，进行HTML格式增强
        try:
            soup = BeautifulSoup(content, 'html.parser')
            # 处理图片
            for img in soup.find_all('img'):
                # 添加响应式类
                img_classes = img.get('class', [])
                if isinstance(img_classes, str):
                    img_classes = [img_classes]
                if 'img-fluid' not in img_classes:
                    img_classes.append('img-fluid')
                if 'rounded' not in img_classes:
                    img_classes.append('rounded')
                img['class'] = img_classes
                # 添加懒加载
                img['loading'] = 'lazy'
                
            content = str(soup)
        except Exception:
            # 如果解析失败，返回原内容
            pass
    
    return content 