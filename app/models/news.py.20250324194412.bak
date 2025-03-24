#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 新闻数据模型
"""

import json
from datetime import datetime

class News:
    """新闻数据模型"""
    
    def __init__(self, id=None, title=None, content=None, pub_time=None, author=None, 
                 source=None, url=None, keywords=None, sentiment=None, crawl_time=None,
                 category=None, images=None, related_stocks=None):
        """
        初始化新闻对象
        
        Args:
            id: 新闻ID
            title: 标题
            content: 内容
            pub_time: 发布时间
            author: 作者
            source: 来源
            url: 原文链接
            keywords: 关键词
            sentiment: 情感值
            crawl_time: 爬取时间
            category: 分类
            images: 图片链接
            related_stocks: 相关股票
        """
        self.id = id
        self.title = title
        self.content = content
        self.pub_time = pub_time
        self.author = author
        self.source = source
        self.url = url
        self.keywords = keywords
        self.sentiment = sentiment
        self.crawl_time = crawl_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.category = category
        self.images = images or []
        self.related_stocks = related_stocks or []
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            dict: 新闻字典
        """
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'pub_time': self.pub_time,
            'author': self.author,
            'source': self.source,
            'url': self.url,
            'keywords': self.keywords,
            'sentiment': self.sentiment,
            'crawl_time': self.crawl_time,
            'category': self.category,
            'images': self.images,
            'related_stocks': self.related_stocks
        }
    
    def to_json(self):
        """
        转换为JSON字符串
        
        Returns:
            str: JSON字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data):
        """
        从字典创建新闻对象
        
        Args:
            data: 新闻字典
            
        Returns:
            News: 新闻对象
        """
        return cls(
            id=data.get('id'),
            title=data.get('title'),
            content=data.get('content'),
            pub_time=data.get('pub_time'),
            author=data.get('author'),
            source=data.get('source'),
            url=data.get('url'),
            keywords=data.get('keywords'),
            sentiment=data.get('sentiment'),
            crawl_time=data.get('crawl_time'),
            category=data.get('category'),
            images=data.get('images'),
            related_stocks=data.get('related_stocks')
        )
    
    @classmethod
    def from_json(cls, json_str):
        """
        从JSON字符串创建新闻对象
        
        Args:
            json_str: JSON字符串
            
        Returns:
            News: 新闻对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self):
        """字符串表示"""
        return f"News(id={self.id}, title={self.title}, source={self.source})"
    
    def __repr__(self):
        """表示形式"""
        return self.__str__()


class Feedback:
    """反馈数据模型"""
    
    def __init__(self, id=None, feedback_type=None, title=None, content=None, email=None,
                 urgent=False, status='pending', submit_time=None, update_time=None, response=None):
        """
        初始化反馈对象
        
        Args:
            id: 反馈ID
            feedback_type: 反馈类型
            title: 标题
            content: 内容
            email: 联系邮箱
            urgent: 是否紧急
            status: 状态
            submit_time: 提交时间
            update_time: 更新时间
            response: 回复内容
        """
        self.id = id
        self.feedback_type = feedback_type
        self.title = title
        self.content = content
        self.email = email
        self.urgent = urgent
        self.status = status
        self.submit_time = submit_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.update_time = update_time or self.submit_time
        self.response = response
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            dict: 反馈字典
        """
        return {
            'id': self.id,
            'feedback_type': self.feedback_type,
            'title': self.title,
            'content': self.content,
            'email': self.email,
            'urgent': self.urgent,
            'status': self.status,
            'submit_time': self.submit_time,
            'update_time': self.update_time,
            'response': self.response
        }
    
    def to_json(self):
        """
        转换为JSON字符串
        
        Returns:
            str: JSON字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data):
        """
        从字典创建反馈对象
        
        Args:
            data: 反馈字典
            
        Returns:
            Feedback: 反馈对象
        """
        return cls(
            id=data.get('id'),
            feedback_type=data.get('feedback_type'),
            title=data.get('title'),
            content=data.get('content'),
            email=data.get('email'),
            urgent=data.get('urgent'),
            status=data.get('status'),
            submit_time=data.get('submit_time'),
            update_time=data.get('update_time'),
            response=data.get('response')
        )
    
    @classmethod
    def from_json(cls, json_str):
        """
        从JSON字符串创建反馈对象
        
        Args:
            json_str: JSON字符串
            
        Returns:
            Feedback: 反馈对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self):
        """字符串表示"""
        return f"Feedback(id={self.id}, title={self.title}, status={self.status})"
    
    def __repr__(self):
        """表示形式"""
        return self.__str__() 