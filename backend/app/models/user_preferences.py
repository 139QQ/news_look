#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 用户偏好数据模型
"""

import json
from datetime import datetime

class UserPreferences:
    """用户偏好数据模型"""
    
    def __init__(self, user_id=None, saved_news=None, read_news=None, last_updated=None):
        """
        初始化用户偏好对象
        
        Args:
            user_id: 用户ID
            saved_news: 收藏的新闻ID列表
            read_news: 已读新闻ID列表
            last_updated: 最后更新时间
        """
        self.user_id = user_id or "default_user"  # 默认用户ID
        self.saved_news = saved_news or []
        self.read_news = read_news or []
        self.last_updated = last_updated or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def save_news(self, news_id):
        """
        收藏新闻
        
        Args:
            news_id: 新闻ID
            
        Returns:
            bool: 是否成功
        """
        if news_id not in self.saved_news:
            self.saved_news.append(news_id)
            self.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True
        return False
    
    def unsave_news(self, news_id):
        """
        取消收藏新闻
        
        Args:
            news_id: 新闻ID
            
        Returns:
            bool: 是否成功
        """
        if news_id in self.saved_news:
            self.saved_news.remove(news_id)
            self.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True
        return False
    
    def mark_as_read(self, news_id):
        """
        标记新闻为已读
        
        Args:
            news_id: 新闻ID
            
        Returns:
            bool: 是否成功
        """
        if news_id not in self.read_news:
            self.read_news.append(news_id)
            self.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True
        return False
    
    def mark_as_unread(self, news_id):
        """
        标记新闻为未读
        
        Args:
            news_id: 新闻ID
            
        Returns:
            bool: 是否成功
        """
        if news_id in self.read_news:
            self.read_news.remove(news_id)
            self.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True
        return False
    
    def is_saved(self, news_id):
        """
        检查新闻是否已收藏
        
        Args:
            news_id: 新闻ID
            
        Returns:
            bool: 是否已收藏
        """
        return news_id in self.saved_news
    
    def is_read(self, news_id):
        """
        检查新闻是否已读
        
        Args:
            news_id: 新闻ID
            
        Returns:
            bool: 是否已读
        """
        return news_id in self.read_news
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            dict: 用户偏好字典
        """
        return {
            'user_id': self.user_id,
            'saved_news': self.saved_news,
            'read_news': self.read_news,
            'last_updated': self.last_updated
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
        从字典创建用户偏好对象
        
        Args:
            data: 用户偏好字典
            
        Returns:
            UserPreferences: 用户偏好对象
        """
        return cls(
            user_id=data.get('user_id'),
            saved_news=data.get('saved_news', []),
            read_news=data.get('read_news', []),
            last_updated=data.get('last_updated')
        )
    
    @classmethod
    def from_json(cls, json_str):
        """
        从JSON字符串创建用户偏好对象
        
        Args:
            json_str: JSON字符串
            
        Returns:
            UserPreferences: 用户偏好对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self):
        """字符串表示"""
        return f"UserPreferences(user_id={self.user_id}, saved_news={len(self.saved_news)}, read_news={len(self.read_news)})"
    
    def __repr__(self):
        """表示形式"""
        return self.__str__() 