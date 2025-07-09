#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库迁移脚本 - 统一新闻表结构
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def migrate(db_path):
    """
    执行数据库迁移
    
    Args:
        db_path: 数据库路径
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 备份原表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_backup AS 
            SELECT * FROM news
        ''')
        
        # 删除原表
        cursor.execute('DROP TABLE IF EXISTS news')
        
        # 创建新表结构 - 移除url的UNIQUE约束，稍后通过INSERT OR IGNORE处理重复
        cursor.execute('''
            CREATE TABLE news (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_html TEXT,
                pub_time DATETIME NOT NULL,
                author TEXT,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                keywords TEXT,
                images TEXT,
                related_stocks TEXT,
                sentiment REAL,
                classification TEXT,
                category TEXT DEFAULT '财经',
                crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX idx_news_source_time ON news(source, pub_time)')
        cursor.execute('CREATE INDEX idx_news_category ON news(category)')
        cursor.execute('CREATE INDEX idx_news_pub_time ON news(pub_time)')
        cursor.execute('CREATE INDEX idx_news_url ON news(url)')  # 添加URL索引但不是UNIQUE约束
        
        # 使用INSERT OR IGNORE从备份表恢复数据
        cursor.execute('''
            INSERT OR IGNORE INTO news (
                id, title, content, content_html, pub_time, author, source,
                url, keywords, images, related_stocks, sentiment,
                classification, category, crawl_time
            )
            SELECT 
                id,
                title,
                content,
                content_html,
                COALESCE(pub_time, datetime('now')) as pub_time,
                author,
                COALESCE(source, '未知') as source,
                url,
                keywords,
                images,
                related_stocks,
                CAST(CASE 
                    WHEN sentiment = '积极' THEN 1
                    WHEN sentiment = '消极' THEN -1
                    ELSE 0 
                END AS REAL) as sentiment,
                classification,
                COALESCE(category, '财经') as category,
                COALESCE(crawl_time, datetime('now')) as crawl_time
            FROM news_backup
        ''')
        
        # 删除备份表
        cursor.execute('DROP TABLE IF EXISTS news_backup')
        
        # 提交事务
        conn.commit()
        logger.info("数据库迁移完成")
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python 001_unified_schema.py <db_path>")
        sys.exit(1)
    migrate(sys.argv[1]) 