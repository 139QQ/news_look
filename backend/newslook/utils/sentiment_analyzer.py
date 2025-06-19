#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 情感分析工具
"""

import re
import os
import json
import jieba
import numpy as np
from collections import defaultdict
from backend.app.utils.logger import get_logger

# 设置日志记录器
logger = get_logger('sentiment_analyzer')

class SentimentAnalyzer:
    """情感分析器，用于分析新闻情感"""
    
    def __init__(self, dict_path=None):
        """
        初始化情感分析器
        
        Args:
            dict_path: 情感词典路径，如果为None则使用默认路径
        """
        # 设置情感词典路径
        if dict_path is None:
            # 使用默认路径
            self.dict_path = os.path.join('data', 'sentiment_dict')
        else:
            self.dict_path = dict_path
        
        # 加载情感词典
        self.sentiment_dict = self.load_sentiment_dict()
        
        # 加载否定词典
        self.negation_words = self.load_negation_words()
        
        # 加载程度副词词典
        self.degree_words = self.load_degree_words()
        
        # 加载停用词词典
        self.stopwords = self.load_stopwords()
        
        logger.debug("情感分析器初始化完成")
    
    def load_sentiment_dict(self):
        """
        加载情感词典
        
        Returns:
            dict: 情感词典，格式为{词: 情感值}
        """
        sentiment_dict = {}
        
        # 如果情感词典目录不存在，则创建
        os.makedirs(self.dict_path, exist_ok=True)
        
        # 情感词典文件路径
        dict_file = os.path.join(self.dict_path, 'sentiment_dict.json')
        
        # 如果情感词典文件存在，则加载
        if os.path.exists(dict_file):
            try:
                with open(dict_file, 'r', encoding='utf-8') as f:
                    sentiment_dict = json.load(f)
                return sentiment_dict
            except Exception as e:
                print(f"加载情感词典失败: {str(e)}")
        
        # 如果情感词典文件不存在，则创建一个简单的情感词典
        # 这里只是一个简单的示例，实际项目中应该使用更完整的情感词典
        positive_words = [
            '上涨', '增长', '利好', '看好', '突破', '强势', '反弹', '回升', '利润', '盈利',
            '增加', '提高', '扩大', '改善', '优化', '创新', '机遇', '发展', '繁荣', '稳定',
            '成功', '领先', '优势', '突出', '卓越', '杰出', '出色', '优秀', '良好', '满意'
        ]
        
        negative_words = [
            '下跌', '下滑', '利空', '看空', '跌破', '弱势', '回落', '下降', '亏损', '亏本',
            '减少', '降低', '缩小', '恶化', '劣化', '停滞', '风险', '衰退', '萧条', '动荡',
            '失败', '落后', '劣势', '平庸', '糟糕', '不佳', '差劲', '低劣', '不良', '不满'
        ]
        
        # 设置情感值
        for word in positive_words:
            sentiment_dict[word] = 1.0
        
        for word in negative_words:
            sentiment_dict[word] = -1.0
        
        # 保存情感词典
        try:
            with open(dict_file, 'w', encoding='utf-8') as f:
                json.dump(sentiment_dict, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存情感词典失败: {str(e)}")
        
        return sentiment_dict
    
    def load_negation_words(self):
        """
        加载否定词词典
        
        Returns:
            set: 否定词集合
        """
        negation_words = set([
            '不', '没', '无', '非', '莫', '弗', '勿', '毋', '未', '否', '别', '无', '不曾',
            '没有', '不要', '不会', '不能', '不可', '不可能', '不可以', '不够', '不是'
        ])
        
        return negation_words
    
    def load_degree_words(self):
        """
        加载程度副词词典
        
        Returns:
            dict: 程度副词词典，格式为{词: 程度值}
        """
        degree_words = {
            '极其': 2.0, '最': 2.0, '极': 2.0, '极度': 2.0, '极端': 2.0, '根本': 2.0, '万分': 2.0,
            '很': 1.5, '太': 1.5, '非常': 1.5, '十分': 1.5, '特别': 1.5, '尤其': 1.5, '格外': 1.5,
            '分外': 1.5, '更加': 1.5, '更为': 1.5, '较为': 1.5, '较': 1.5, '比较': 1.5, '相当': 1.5,
            '稍': 0.5, '稍微': 0.5, '稍稍': 0.5, '稍许': 0.5, '略': 0.5, '略微': 0.5, '一点': 0.5,
            '一点点': 0.5, '有点': 0.5, '有点儿': 0.5, '有些': 0.5, '多少': 0.5
        }
        
        return degree_words
    
    def load_stopwords(self):
        """
        加载停用词词典
        
        Returns:
            set: 停用词集合
        """
        stopwords = set([
            '的', '了', '和', '与', '或', '是', '在', '有', '这', '那', '就', '都', '而', '及',
            '等', '被', '比', '把', '为', '向', '于', '但', '由', '从', '对', '之', '让', '给',
            '到', '且', '则', '使', '因', '所', '以', '如', '若', '某', '每', '各', '该', '此',
            '其', '何', '又', '也', '个', '们', '我', '你', '他', '她', '它', '将', '已', '能',
            '要', '会', '可', '得', '着', '过', '地', '上', '下', '前', '后', '左', '右', '中',
            '内', '外', '来', '去', '出', '入', '里', '时', '年', '月', '日', '分', '秒', '很',
            '再', '只', '又', '也', '还', '并', '却', '乃', '呀', '吗', '啊', '哪', '那', '怎',
            '么', '什', '谁', '多', '少', '几', '更', '最', '好', '些', '吧', '呢', '啦', '嘛'
        ])
        
        return stopwords
    
    def analyze(self, title, content):
        """
        分析文本情感
        
        Args:
            title: 标题
            content: 内容
        
        Returns:
            float: 情感值，0-1之间，越大越积极
        """
        # 合并标题和内容，标题权重更高
        text = title * 3 + ' ' + content
        
        # 分词
        words = jieba.lcut(text)
        
        # 情感分析
        sentiment_score = self.calculate_sentiment_score(words)
        
        # 将情感分数转换为0-1之间的值
        normalized_score = self.normalize_score(sentiment_score)
        
        return normalized_score
    
    def calculate_sentiment_score(self, words):
        """
        计算情感分数
        
        Args:
            words: 分词后的词列表
        
        Returns:
            float: 情感分数
        """
        # 情感分数
        score = 0.0
        
        # 否定词计数
        negation_count = 0
        
        # 程度副词
        degree = 1.0
        
        # 遍历词语
        for i, word in enumerate(words):
            # 跳过停用词
            if word in self.stopwords:
                continue
            
            # 处理否定词
            if word in self.negation_words:
                negation_count += 1
                continue
            
            # 处理程度副词
            if word in self.degree_words:
                degree = self.degree_words[word]
                continue
            
            # 处理情感词
            if word in self.sentiment_dict:
                # 计算情感值
                word_score = self.sentiment_dict[word]
                
                # 处理否定词的影响
                if negation_count % 2 == 1:
                    word_score = -word_score
                
                # 处理程度副词的影响
                word_score *= degree
                
                # 累加情感分数
                score += word_score
                
                # 重置否定词计数和程度副词
                negation_count = 0
                degree = 1.0
        
        return score
    
    def normalize_score(self, score):
        """
        将情感分数归一化到0-1之间
        
        Args:
            score: 原始情感分数
        
        Returns:
            float: 归一化后的情感分数，0-1之间
        """
        # 使用Sigmoid函数归一化
        normalized = 1.0 / (1.0 + np.exp(-score))
        
        return normalized 