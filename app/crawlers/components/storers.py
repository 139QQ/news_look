#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 存储器组件
负责存储爬取的新闻数据
"""

import os
import json
import sqlite3
import logging
import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from abc import ABC, abstractmethod

from app.utils.logger import get_crawler_logger

# 使用专门的爬虫日志记录器
logger = get_crawler_logger('storers')

class BaseStorer(ABC):
    """存储器基类，定义存储器的接口"""
    
    @abstractmethod
    def save(self, data: Union[Dict, List[Dict]]) -> bool:
        """保存数据"""
        pass
    
    @abstractmethod
    def get(self, query: Dict) -> List[Dict]:
        """获取数据"""
        pass
    
    @abstractmethod
    def update(self, query: Dict, data: Dict) -> bool:
        """更新数据"""
        pass
    
    @abstractmethod
    def delete(self, query: Dict) -> bool:
        """删除数据"""
        pass


class SQLiteStorer(BaseStorer):
    """SQLite存储器，将数据存储到SQLite数据库"""
    
    def __init__(self, db_path: str, table_name: str = 'news'):
        """
        初始化SQLite存储器
        
        Args:
            db_path: 数据库路径
            table_name: 表名
        """
        self.db_path = db_path
        self.table_name = table_name
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 初始化数据库连接
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path)
            self._init_table()
            logger.info(f"SQLite存储器初始化成功: {self.db_path}, 表: {self.table_name}")
        except Exception as e:
            logger.error(f"SQLite存储器初始化失败: {str(e)}")
    
    def __del__(self):
        """析构函数，关闭数据库连接"""
        try:
            if self.conn:
                self.conn.close()
                logger.debug("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {str(e)}")
    
    def _init_table(self):
        """初始化数据库表结构"""
        try:
            cursor = self.conn.cursor()
            
            # 创建新闻表
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                content_html TEXT,
                url TEXT UNIQUE,
                publish_time TEXT,
                crawl_time TEXT,
                source TEXT,
                category TEXT,
                author TEXT,
                keywords TEXT,
                sentiment REAL,
                summary TEXT,
                images TEXT
            )
            ''')
            
            # 创建索引
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_url ON {self.table_name}(url)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_source ON {self.table_name}(source)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_category ON {self.table_name}(category)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_publish_time ON {self.table_name}(publish_time)')
            
            self.conn.commit()
            logger.info(f"数据库表 {self.table_name} 初始化成功")
        except Exception as e:
            logger.error(f"初始化数据库表失败: {str(e)}")
    
    def save(self, data: Union[Dict, List[Dict]]) -> bool:
        """
        保存数据到数据库
        
        Args:
            data: 单条新闻数据或新闻数据列表
            
        Returns:
            bool: 保存是否成功
        """
        # 确保连接可用
        if not self.conn:
            try:
                self.conn = sqlite3.connect(self.db_path)
            except Exception as e:
                logger.error(f"连接数据库失败: {str(e)}")
                return False
        
        # 转换单条数据为列表
        if isinstance(data, dict):
            data_list = [data]
        else:
            data_list = data
        
        # 开始事务
        self.conn.isolation_level = 'DEFERRED'
        
        try:
            cursor = self.conn.cursor()
            
            # 准备SQL语句
            sql = f'''
            INSERT OR REPLACE INTO {self.table_name} 
            (id, title, content, content_html, url, publish_time, crawl_time, 
             source, category, author, keywords, sentiment, summary, images)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            # 批量插入数据
            count = 0
            for item in data_list:
                try:
                    # 如果没有ID，生成一个
                    if 'id' not in item or not item['id']:
                        import hashlib
                        id_str = f"{item.get('url', '')}{item.get('title', '')}"
                        item['id'] = hashlib.md5(id_str.encode('utf-8')).hexdigest()
                    
                    # 处理列表类型的字段（关键词、图片）
                    keywords = item.get('keywords', [])
                    if isinstance(keywords, list):
                        keywords = ','.join(keywords)

                    images = item.get('images', [])
                    if isinstance(images, list):
                        images = json.dumps(images)

                    # 添加当前时间为爬取时间
                    if 'crawl_time' not in item or not item['crawl_time']:
                        item['crawl_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    # 执行插入
                    cursor.execute(sql, (
                        item.get('id', ''),
                        item.get('title', ''),
                        item.get('content', ''),
                        item.get('content_html', ''),
                        item.get('url', ''),
                        item.get('publish_time', ''),
                        item.get('crawl_time', ''),
                        item.get('source', ''),
                        item.get('category', ''),
                        item.get('author', ''),
                        keywords,
                        item.get('sentiment', 0.0),
                        item.get('summary', ''),
                        images
                    ))
                    count += 1
                except Exception as e:
                    logger.error(f"插入数据时出错: {str(e)}, 数据: {item}")
                    continue
            
            # 提交事务
            self.conn.commit()
            logger.info(f"成功保存 {count}/{len(data_list)} 条数据到 {self.table_name}")
            return count > 0
            
        except Exception as e:
            # 回滚事务
            self.conn.rollback()
            logger.error(f"保存数据失败: {str(e)}")
            return False
    
    def get(self, query: Dict = None) -> List[Dict]:
        """
        获取数据
        
        Args:
            query: 查询条件
            
        Returns:
            List[Dict]: 查询结果
        """
        # 确保连接可用
        if not self.conn:
            try:
                self.conn = sqlite3.connect(self.db_path)
            except Exception as e:
                logger.error(f"连接数据库失败: {str(e)}")
                return []
        
        try:
            cursor = self.conn.cursor()
            
            # 构建SQL查询
            sql = f'SELECT * FROM {self.table_name}'
            params = []
            
            if query:
                conditions = []
                for key, value in query.items():
                    if key in ['publish_time_start', 'publish_time_end']:
                        continue
                    conditions.append(f'{key} = ?')
                    params.append(value)
                
                # 处理日期范围查询
                if 'publish_time_start' in query and query['publish_time_start']:
                    conditions.append('publish_time >= ?')
                    params.append(query['publish_time_start'])
                
                if 'publish_time_end' in query and query['publish_time_end']:
                    conditions.append('publish_time <= ?')
                    params.append(query['publish_time_end'])
                
                if conditions:
                    sql += ' WHERE ' + ' AND '.join(conditions)
            
            # 添加排序
            sql += ' ORDER BY publish_time DESC'
            
            # 执行查询
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # 获取列名
            columns = [col[0] for col in cursor.description]
            
            # 解析结果
            result = []
            for row in cursor.fetchall():
                item = dict(zip(columns, row))
                
                # 处理JSON字段
                if 'images' in item and item['images']:
                    try:
                        item['images'] = json.loads(item['images'])
                    except json.JSONDecodeError:
                        item['images'] = []
                
                if 'keywords' in item and item['keywords']:
                    item['keywords'] = item['keywords'].split(',')
                
                result.append(item)
            
            return result
            
        except Exception as e:
            logger.error(f"查询数据失败: {str(e)}")
            return []
    
    def update(self, query: Dict, data: Dict) -> bool:
        """
        更新数据
        
        Args:
            query: 查询条件
            data: 更新数据
            
        Returns:
            bool: 更新是否成功
        """
        # 确保连接可用
        if not self.conn:
            try:
                self.conn = sqlite3.connect(self.db_path)
            except Exception as e:
                logger.error(f"连接数据库失败: {str(e)}")
                return False
        
        if not query or not data:
            logger.warning("更新数据失败：查询条件或更新数据为空")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # 构建SQL更新
            set_clauses = []
            set_params = []
            
            for key, value in data.items():
                # 处理特殊字段
                if key in ['keywords', 'images'] and isinstance(value, list):
                    if key == 'keywords':
                        value = ','.join(value)
                    elif key == 'images':
                        value = json.dumps(value)
                
                set_clauses.append(f'{key} = ?')
                set_params.append(value)
            
            # 构建WHERE条件
            where_clauses = []
            where_params = []
            
            for key, value in query.items():
                where_clauses.append(f'{key} = ?')
                where_params.append(value)
            
            # 合并参数
            params = set_params + where_params
            
            # 构建完整SQL
            sql = f'''
            UPDATE {self.table_name} 
            SET {', '.join(set_clauses)} 
            WHERE {' AND '.join(where_clauses)}
            '''
            
            # 执行更新
            cursor.execute(sql, params)
            self.conn.commit()
            
            affected_rows = cursor.rowcount
            logger.info(f"成功更新 {affected_rows} 条数据")
            return affected_rows > 0
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"更新数据失败: {str(e)}")
            return False
    
    def delete(self, query: Dict) -> bool:
        """
        删除数据
        
        Args:
            query: 查询条件
            
        Returns:
            bool: 删除是否成功
        """
        # 确保连接可用
        if not self.conn:
            try:
                self.conn = sqlite3.connect(self.db_path)
            except Exception as e:
                logger.error(f"连接数据库失败: {str(e)}")
                return False
        
        if not query:
            logger.warning("删除数据失败：查询条件为空")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # 构建WHERE条件
            where_clauses = []
            params = []
            
            for key, value in query.items():
                where_clauses.append(f'{key} = ?')
                params.append(value)
            
            # 构建完整SQL
            sql = f'''
            DELETE FROM {self.table_name} 
            WHERE {' AND '.join(where_clauses)}
            '''
            
            # 执行删除
            cursor.execute(sql, params)
            self.conn.commit()
            
            affected_rows = cursor.rowcount
            logger.info(f"成功删除 {affected_rows} 条数据")
            return affected_rows > 0
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"删除数据失败: {str(e)}")
            return False
    
    def get_count(self, query: Dict = None) -> int:
        """
        获取数据数量
        
        Args:
            query: 查询条件
            
        Returns:
            int: 数据数量
        """
        # 确保连接可用
        if not self.conn:
            try:
                self.conn = sqlite3.connect(self.db_path)
            except Exception as e:
                logger.error(f"连接数据库失败: {str(e)}")
                return 0
        
        try:
            cursor = self.conn.cursor()
            
            # 构建SQL查询
            sql = f'SELECT COUNT(*) FROM {self.table_name}'
            params = []
            
            if query:
                conditions = []
                for key, value in query.items():
                    if key in ['publish_time_start', 'publish_time_end']:
                        continue
                    conditions.append(f'{key} = ?')
                    params.append(value)
                
                # 处理日期范围查询
                if 'publish_time_start' in query and query['publish_time_start']:
                    conditions.append('publish_time >= ?')
                    params.append(query['publish_time_start'])
                
                if 'publish_time_end' in query and query['publish_time_end']:
                    conditions.append('publish_time <= ?')
                    params.append(query['publish_time_end'])
                
                if conditions:
                    sql += ' WHERE ' + ' AND '.join(conditions)
            
            # 执行查询
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # 获取结果
            count = cursor.fetchone()[0]
            return count
            
        except Exception as e:
            logger.error(f"查询数据数量失败: {str(e)}")
            return 0


class JSONFileStorer(BaseStorer):
    """JSON文件存储器，将数据存储到JSON文件"""
    
    def __init__(self, file_path: str, encoding: str = 'utf-8'):
        """
        初始化JSON文件存储器
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
        """
        self.file_path = file_path
        self.encoding = encoding
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        # 初始化文件
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding=self.encoding) as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            logger.info(f"JSON文件已创建: {self.file_path}")
        
        logger.info(f"JSON文件存储器初始化成功: {self.file_path}")
    
    def save(self, data: Union[Dict, List[Dict]]) -> bool:
        """
        保存数据到JSON文件
        
        Args:
            data: 单条新闻数据或新闻数据列表
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 读取现有数据
            existing_data = []
            try:
                with open(self.file_path, 'r', encoding=self.encoding) as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []
            
            # 准备新数据
            if isinstance(data, dict):
                data_list = [data]
            else:
                data_list = data
            
            # 添加ID
            for item in data_list:
                if 'id' not in item or not item['id']:
                    import hashlib
                    id_str = f"{item.get('url', '')}{item.get('title', '')}"
                    item['id'] = hashlib.md5(id_str.encode('utf-8')).hexdigest()
                
                # 添加当前时间为爬取时间
                if 'crawl_time' not in item or not item['crawl_time']:
                    item['crawl_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 找出已存在的数据
            existing_ids = {item.get('id') for item in existing_data}
            
            # 合并数据
            for item in data_list:
                if item.get('id') not in existing_ids:
                    existing_data.append(item)
                else:
                    # 更新已存在的数据
                    for i, existing_item in enumerate(existing_data):
                        if existing_item.get('id') == item.get('id'):
                            existing_data[i] = item
                            break
            
            # 写入文件
            with open(self.file_path, 'w', encoding=self.encoding) as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(data_list)} 条数据到 {self.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存数据到JSON文件失败: {str(e)}")
            return False
    
    def get(self, query: Dict = None) -> List[Dict]:
        """
        获取数据
        
        Args:
            query: 查询条件
            
        Returns:
            List[Dict]: 查询结果
        """
        try:
            # 读取所有数据
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                data = json.load(f)
            
            # 如果没有查询条件，返回所有数据
            if not query:
                return data
            
            # 过滤数据
            result = []
            for item in data:
                match = True
                
                for key, value in query.items():
                    # 处理日期范围查询
                    if key == 'publish_time_start' and 'publish_time' in item:
                        if item['publish_time'] < value:
                            match = False
                            break
                    elif key == 'publish_time_end' and 'publish_time' in item:
                        if item['publish_time'] > value:
                            match = False
                            break
                    elif key in item and item[key] != value:
                        match = False
                        break
                
                if match:
                    result.append(item)
            
            # 按发布时间排序
            result.sort(key=lambda x: x.get('publish_time', ''), reverse=True)
            
            return result
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"读取JSON文件失败: {str(e)}")
            return []
    
    def update(self, query: Dict, data: Dict) -> bool:
        """
        更新数据
        
        Args:
            query: 查询条件
            data: 更新数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 读取所有数据
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                all_data = json.load(f)
            
            # 查找并更新数据
            updated = False
            for i, item in enumerate(all_data):
                match = True
                
                for key, value in query.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                
                if match:
                    # 更新数据
                    all_data[i].update(data)
                    updated = True
            
            # 如果有更新，写入文件
            if updated:
                with open(self.file_path, 'w', encoding=self.encoding) as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"成功更新数据")
                return True
            else:
                logger.warning(f"未找到匹配的数据进行更新")
                return False
                
        except Exception as e:
            logger.error(f"更新数据失败: {str(e)}")
            return False
    
    def delete(self, query: Dict) -> bool:
        """
        删除数据
        
        Args:
            query: 查询条件
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 读取所有数据
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                all_data = json.load(f)
            
            # 过滤数据
            original_length = len(all_data)
            filtered_data = []
            
            for item in all_data:
                match = True
                
                for key, value in query.items():
                    if key not in item or item[key] != value:
                        match = False
                        break
                
                if not match:
                    filtered_data.append(item)
            
            # 如果有数据被删除，写入文件
            if len(filtered_data) < original_length:
                with open(self.file_path, 'w', encoding=self.encoding) as f:
                    json.dump(filtered_data, f, ensure_ascii=False, indent=2)
                
                deleted_count = original_length - len(filtered_data)
                logger.info(f"成功删除 {deleted_count} 条数据")
                return True
            else:
                logger.warning("未找到匹配的数据进行删除")
                return False
                
        except Exception as e:
            logger.error(f"删除数据失败: {str(e)}")
            return False


def create_storer(storer_type: str = 'sqlite', **kwargs) -> BaseStorer:
    """
    创建存储器工厂函数
    
    Args:
        storer_type: 存储器类型（'sqlite'或'json'）
        **kwargs: 其他参数
        
    Returns:
        BaseStorer: 存储器实例
    """
    if storer_type.lower() == 'json':
        return JSONFileStorer(**kwargs)
    else:
        return SQLiteStorer(**kwargs) 