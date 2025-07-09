#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 用户偏好数据库管理
"""

import sqlite3
import json
import time
from pathlib import Path
from backend.app.utils.logger import get_logger
import os

logger = get_logger(__name__)

class UserPreferencesDB:
    """用户偏好数据库操作类"""
    
    def __init__(self, db_path=None):
        """初始化用户偏好数据库"""
        if db_path:
            self.db_path = db_path
        else:
            # 从配置中获取数据库目录
            from backend.app.config import get_settings
            settings = get_settings()
            db_dir = settings.get('DB_DIR', os.path.join(os.getcwd(), 'data', 'db'))
            # 确保数据库目录存在
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"创建用户偏好数据库目录: {db_dir}")
            self.db_path = os.path.join(db_dir, 'user_preferences.db')
            logger.info(f"使用用户偏好数据库: {self.db_path}")
        
        # 不在初始化时立即创建连接，改为按需创建
        self.conn = None
        self._init_db()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
        return False  # 不处理异常
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except Exception as e:
                logger.error(f"关闭用户偏好数据库连接失败: {str(e)}")
            finally:
                self.conn = None
    
    def _get_connection(self):
        """获取数据库连接"""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        try:
            # 使用临时连接创建表
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 用户偏好表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                preferences TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 用户收藏新闻表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_saved_news (
                user_id TEXT,
                news_id INTEGER,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, news_id)
            )
            ''')
            
            # 用户已读新闻表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_read_news (
                user_id TEXT,
                news_id INTEGER,
                read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, news_id)
            )
            ''')
            
            conn.commit()
            conn.close()  # 关闭临时连接
            logger.info("用户偏好数据库表初始化完成")
        except Exception as e:
            logger.error(f"用户偏好数据库初始化失败: {str(e)}")
            raise
    
    def get_preferences(self, user_id):
        """获取用户偏好设置"""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT preferences FROM user_preferences WHERE user_id = ?", 
                (user_id,)
            )
            result = cursor.fetchone()
            
            if result:
                return json.loads(result["preferences"])
            return {}
        except Exception as e:
            logger.error(f"获取用户偏好设置失败: {str(e)}")
            return {}
    
    def save_preferences(self, user_id, preferences):
        """保存用户偏好设置"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 检查用户是否已有偏好设置
            cursor.execute(
                "SELECT 1 FROM user_preferences WHERE user_id = ?", 
                (user_id,)
            )
            exists = cursor.fetchone()
            
            # 序列化偏好数据
            prefs_json = json.dumps(preferences, ensure_ascii=False)
            
            # 更新或插入偏好设置
            if exists:
                cursor.execute(
                    "UPDATE user_preferences SET preferences = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (prefs_json, user_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO user_preferences (user_id, preferences) VALUES (?, ?)",
                    (user_id, prefs_json)
                )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"保存用户偏好设置失败: {str(e)}")
            return False
    
    def save_news(self, user_id, news_id):
        """将新闻添加到用户收藏"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 检查是否已经收藏
            cursor.execute(
                "SELECT 1 FROM user_saved_news WHERE user_id = ? AND news_id = ?",
                (user_id, news_id)
            )
            if cursor.fetchone():
                return True  # 已经收藏过
            
            # 添加到收藏
            cursor.execute(
                "INSERT INTO user_saved_news (user_id, news_id) VALUES (?, ?)",
                (user_id, news_id)
            )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"收藏新闻失败: {str(e)}")
            return False
    
    def unsave_news(self, user_id, news_id):
        """从用户收藏中移除新闻"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM user_saved_news WHERE user_id = ? AND news_id = ?",
                (user_id, news_id)
            )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"取消收藏新闻失败: {str(e)}")
            return False
    
    def is_saved(self, user_id, news_id):
        """检查新闻是否已被用户收藏"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT 1 FROM user_saved_news WHERE user_id = ? AND news_id = ?",
                (user_id, news_id)
            )
            
            return bool(cursor.fetchone())
        except Exception as e:
            logger.error(f"检查新闻收藏状态失败: {str(e)}")
            return False
    
    def mark_as_read(self, user_id, news_id):
        """将新闻标记为已读"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 检查是否已标记为已读
            cursor.execute(
                "SELECT 1 FROM user_read_news WHERE user_id = ? AND news_id = ?",
                (user_id, news_id)
            )
            if cursor.fetchone():
                return True  # 已经标记为已读
            
            # 标记为已读
            cursor.execute(
                "INSERT INTO user_read_news (user_id, news_id) VALUES (?, ?)",
                (user_id, news_id)
            )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"标记新闻为已读失败: {str(e)}")
            return False
    
    def mark_as_unread(self, user_id, news_id):
        """将新闻标记为未读"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM user_read_news WHERE user_id = ? AND news_id = ?",
                (user_id, news_id)
            )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"标记新闻为未读失败: {str(e)}")
            return False
    
    def is_read(self, user_id, news_id):
        """检查新闻是否已被用户阅读"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT 1 FROM user_read_news WHERE user_id = ? AND news_id = ?",
                (user_id, news_id)
            )
            
            return bool(cursor.fetchone())
        except Exception as e:
            logger.error(f"检查新闻阅读状态失败: {str(e)}")
            return False
    
    def get_saved_news_ids(self, user_id):
        """获取用户收藏的所有新闻ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT news_id FROM user_saved_news WHERE user_id = ? ORDER BY saved_at DESC",
                (user_id,)
            )
            
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取用户收藏新闻ID列表失败: {str(e)}")
            return []
    
    def get_read_news_ids(self, user_id):
        """获取用户已读的所有新闻ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT news_id FROM user_read_news WHERE user_id = ? ORDER BY read_at DESC",
                (user_id,)
            )
            
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取用户已读新闻ID列表失败: {str(e)}")
            return [] 