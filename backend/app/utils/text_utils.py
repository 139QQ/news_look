#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文本处理工具模块
"""

import re
import jieba
import jieba.analyse
import logging

# 设置日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_text(text):
    """
    清理文本，去除多余空白字符和特殊字符
    
    Args:
        text (str): 需要清理的文本
        
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 去除多余空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 去除特殊字符
    text = re.sub(r'[\r\n\t]', ' ', text)
    
    return text.strip()

def extract_keywords(text, top_k=10):
    """
    从文本中提取关键词
    
    Args:
        text (str): 输入文本
        top_k (int): 返回的关键词数量
        
    Returns:
        list: 关键词列表
    """
    if not text or len(text) < 10:
        return []
    
    # 使用jieba提取关键词
    try:
        keywords = jieba.analyse.extract_tags(text, topK=top_k)
        return keywords
    except (ValueError, TypeError) as e:
        logger.error("提取关键词失败: %s", str(e))
        return []

def text_similarity(text1, text2):
    """
    计算两段文本的相似度
    
    Args:
        text1 (str): 第一段文本
        text2 (str): 第二段文本
        
    Returns:
        float: 相似度得分 (0-1)
    """
    if not text1 or not text2:
        return 0.0
    
    # 提取关键词
    keywords1 = set(extract_keywords(text1, 20))
    keywords2 = set(extract_keywords(text2, 20))
    
    # 计算Jaccard相似度
    if not keywords1 or not keywords2:
        return 0.0
    
    intersection = keywords1.intersection(keywords2)
    union = keywords1.union(keywords2)
    
    return len(intersection) / len(union) if union else 0.0

def summarize_text(text, max_length=200):
    """
    生成文本摘要
    
    Args:
        text (str): 原文本
        max_length (int): 摘要最大长度
        
    Returns:
        str: 文本摘要
    """
    if not text:
        return ""
    
    # 简单摘要：取前max_length个字符
    if len(text) <= max_length:
        return text
    
    # 尝试在句子结束处截断
    summary = text[:max_length]
    last_period = summary.rfind('。')
    last_question = summary.rfind('？')
    last_exclamation = summary.rfind('！')
    
    # 找到最后一个句子结束符
    last_sentence_end = max(last_period, last_question, last_exclamation)
    
    if last_sentence_end > 0:
        return text[:last_sentence_end + 1]
    
    return summary + "..."
