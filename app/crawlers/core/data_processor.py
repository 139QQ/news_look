#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 数据处理模块
负责数据清洗、转换和存储
"""

import os
import time
import sqlite3
import json
import hashlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from app.utils.logger import get_logger
from app.utils.text_cleaner import clean_html, clean_text
from app.utils.sentiment_analyzer import SentimentAnalyzer

# 初始化日志记录器
logger = get_logger('data_processor')

class DataProcessor:
    """数据处理器，负责清洗和存储爬取的数据"""
    
    def __init__(self, db_path: str, batch_size: int = 10):
        """
        初始化数据处理器
        
        Args:
            db_path: 数据库路径
            batch_size: 批处理大小
        """
        self.db_path = db_path
        self.batch_size = batch_size
        self.sentiment_analyzer = SentimentAnalyzer()
        self.batch_data = []
        self.stats = {
            'processed': 0,
            'saved': 0,
            'failed': 0,
            'duplicates': 0,
            'last_batch_time': 0
        }
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建新闻表（如果不存在）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                content_html TEXT,
                pub_time TEXT,
                author TEXT,
                source TEXT,
                url TEXT UNIQUE,
                keywords TEXT,
                images TEXT,
                related_stocks TEXT,
                sentiment TEXT,
                classification TEXT,
                category TEXT,
                crawl_time TEXT
            )
            ''')
            
            # 创建关键词表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE,
                count INTEGER DEFAULT 1,
                last_updated TEXT
            )
            ''')
            
            # 创建新闻-关键词关联表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_keywords (
                news_id TEXT,
                keyword_id INTEGER,
                PRIMARY KEY (news_id, keyword_id),
                FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
                FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
            )
            ''')
            
            # 创建股票表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                code TEXT PRIMARY KEY,
                name TEXT,
                count INTEGER DEFAULT 1,
                last_updated TEXT
            )
            ''')
            
            # 创建新闻-股票关联表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_stocks (
                news_id TEXT,
                stock_code TEXT,
                PRIMARY KEY (news_id, stock_code),
                FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
                FOREIGN KEY (stock_code) REFERENCES stocks(code) ON DELETE CASCADE
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"数据库初始化完成: {self.db_path}")
        except Exception as e:
            logger.error(f"初始化数据库失败: {str(e)}")
            raise
    
    def process(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个文章数据
        
        Args:
            article: 文章数据字典
            
        Returns:
            Dict[str, Any]: 处理后的文章数据
        """
        try:
            # 复制一份文章数据，避免修改原始数据
            processed = article.copy()
            
            # 生成ID
            if 'id' not in processed or not processed['id']:
                if 'url' in processed and processed['url']:
                    processed['id'] = hashlib.md5(processed['url'].encode('utf-8')).hexdigest()
                else:
                    processed['id'] = hashlib.md5((
                        processed.get('title', '') + 
                        processed.get('source', '') + 
                        str(datetime.now())
                    ).encode('utf-8')).hexdigest()
            
            # 清理标题
            if 'title' in processed and processed['title']:
                processed['title'] = clean_text(processed['title']).strip()
            
            # 清理并保存原始HTML内容
            if 'content_html' not in processed and 'content' in processed:
                processed['content_html'] = processed['content']
            
            # 清理正文内容
            if 'content' in processed and processed['content']:
                if isinstance(processed['content'], str):
                    processed['content'] = clean_html(processed['content'])
            
            # 设置爬取时间
            if 'crawl_time' not in processed:
                processed['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 提取关键词（如果没有）
            if ('keywords' not in processed or not processed['keywords']) and 'content' in processed and processed['content']:
                try:
                    from app.utils.keywords_extractor import extract_keywords
                    keywords = extract_keywords(processed['content'])
                    processed['keywords'] = ','.join(keywords)
                except ImportError:
                    logger.warning("关键词提取组件未找到，跳过关键词提取")
            
            # 进行情感分析（如果没有）
            if ('sentiment' not in processed or not processed['sentiment']) and 'content' in processed:
                try:
                    # 使用标题和内容进行情感分析
                    sentiment = self.sentiment_analyzer.analyze(
                        title=processed.get('title', ''),
                        content=processed.get('content', '')
                    )
                    processed['sentiment'] = sentiment
                except Exception as e:
                    logger.warning(f"情感分析失败: {str(e)}")
            
            # 确保标题字段不为空（数据库有NOT NULL约束）
            if 'title' not in processed or not processed['title']:
                processed['title'] = f"未知标题 {processed['id'][:8]}"
                logger.warning(f"文章标题为空，设置默认标题，ID: {processed['id']}")
            
            # 处理图片列表
            if 'images' in processed and processed['images']:
                if isinstance(processed['images'], list):
                    # 将图片列表转换为JSON字符串
                    processed['images'] = json.dumps(processed['images'], ensure_ascii=False)
            
            # 记录统计
            self.stats['processed'] += 1
            
            return processed
        except Exception as e:
            logger.error(f"处理文章失败: {str(e)}")
            self.stats['failed'] += 1
            raise
    
    def save(self, article: Dict[str, Any]) -> bool:
        """
        保存单个文章到数据库
        
        Args:
            article: 文章数据字典
            
        Returns:
            bool: 是否保存成功
        """
        # 先处理文章
        try:
            processed = self.process(article)
            
            # 添加到批处理队列
            self.batch_data.append(processed)
            
            # 如果达到批处理大小，执行批量保存
            if len(self.batch_data) >= self.batch_size:
                return self.save_batch()
            
            return True
        except Exception as e:
            logger.error(f"保存文章失败: {str(e)}")
            self.stats['failed'] += 1
            return False
    
    def save_batch(self) -> bool:
        """
        批量保存文章到数据库
        
        Returns:
            bool: 是否保存成功
        """
        if not self.batch_data:
            return True
            
        conn = None
        try:
            start_time = time.time()
            
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 开始事务
            conn.execute('BEGIN TRANSACTION')
            
            saved_count = 0
            duplicate_count = 0
            
            for article in self.batch_data:
                try:
                    # 检查文章是否已存在
                    cursor.execute('SELECT id FROM news WHERE id = ? OR url = ?', 
                                  (article.get('id'), article.get('url')))
                    if cursor.fetchone():
                        duplicate_count += 1
                        continue
                    
                    # 插入新闻
                    cursor.execute('''
                    INSERT INTO news (
                        id, title, content, content_html, pub_time, author, source,
                        url, keywords, images, related_stocks, sentiment, 
                        classification, category, crawl_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        article.get('id'),
                        article.get('title'),
                        article.get('content'),
                        article.get('content_html'),
                        article.get('pub_time'),
                        article.get('author'),
                        article.get('source'),
                        article.get('url'),
                        article.get('keywords'),
                        article.get('images'),
                        article.get('related_stocks'),
                        article.get('sentiment'),
                        article.get('classification'),
                        article.get('category'),
                        article.get('crawl_time')
                    ))
                    
                    # 处理关键词
                    if 'keywords' in article and article['keywords']:
                        keywords = [kw.strip() for kw in article['keywords'].split(',')]
                        for keyword in keywords:
                            if not keyword:
                                continue
                                
                            # 尝试插入关键词（如果不存在）
                            try:
                                cursor.execute('''
                                INSERT INTO keywords (keyword, last_updated) 
                                VALUES (?, ?)
                                ''', (keyword, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                            except sqlite3.IntegrityError:
                                # 关键词已存在，更新计数
                                cursor.execute('''
                                UPDATE keywords SET count = count + 1, 
                                last_updated = ? WHERE keyword = ?
                                ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), keyword))
                            
                            # 获取关键词ID
                            cursor.execute('SELECT id FROM keywords WHERE keyword = ?', (keyword,))
                            keyword_id = cursor.fetchone()[0]
                            
                            # 建立新闻-关键词关联
                            cursor.execute('''
                            INSERT OR IGNORE INTO news_keywords (news_id, keyword_id)
                            VALUES (?, ?)
                            ''', (article['id'], keyword_id))
                    
                    # 处理相关股票
                    if 'related_stocks' in article and article['related_stocks']:
                        stocks = json.loads(article['related_stocks']) if isinstance(article['related_stocks'], str) else article['related_stocks']
                        for stock in stocks:
                            if isinstance(stock, dict):
                                code = stock.get('code')
                                name = stock.get('name')
                            else:
                                # 假设是逗号分隔的代码
                                code = stock
                                name = None
                                
                            if not code:
                                continue
                                
                            # 尝试插入股票（如果不存在）
                            try:
                                cursor.execute('''
                                INSERT INTO stocks (code, name, last_updated) 
                                VALUES (?, ?, ?)
                                ''', (code, name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                            except sqlite3.IntegrityError:
                                # 股票已存在，更新计数
                                cursor.execute('''
                                UPDATE stocks SET count = count + 1, 
                                last_updated = ? WHERE code = ?
                                ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), code))
                            
                            # 建立新闻-股票关联
                            cursor.execute('''
                            INSERT OR IGNORE INTO news_stocks (news_id, stock_code)
                            VALUES (?, ?)
                            ''', (article['id'], code))
                    
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"保存文章 {article.get('id', 'unknown')} 失败: {str(e)}")
                    continue
            
            # 提交事务
            conn.commit()
            
            # 更新统计信息
            self.stats['saved'] += saved_count
            self.stats['duplicates'] += duplicate_count
            self.stats['last_batch_time'] = time.time() - start_time
            
            logger.info(f"批量保存完成: 保存 {saved_count} 条，跳过 {duplicate_count} 条重复，耗时 {self.stats['last_batch_time']:.2f} 秒")
            
            # 清空批处理队列
            self.batch_data = []
            
            return True
            
        except Exception as e:
            logger.error(f"批量保存失败: {str(e)}")
            # 回滚事务
            if conn:
                conn.rollback()
            return False
            
        finally:
            # 关闭连接
            if conn:
                conn.close()
    
    def flush(self) -> bool:
        """
        刷新缓存，保存所有剩余的批处理数据
        
        Returns:
            bool: 是否保存成功
        """
        return self.save_batch()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        return {
            'processed': self.stats['processed'],
            'saved': self.stats['saved'],
            'failed': self.stats['failed'],
            'duplicates': self.stats['duplicates'],
            'pending': len(self.batch_data),
            'last_batch_time': self.stats['last_batch_time'],
            'db_path': self.db_path
        }
    
    def close(self):
        """关闭资源"""
        # 保存剩余的数据
        self.flush() 