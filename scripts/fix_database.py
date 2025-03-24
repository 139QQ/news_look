#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库修复脚本

该脚本用于修复NewsLook项目的数据库结构问题，包括：
1. 添加缺失的字段（如pub_time）
2. 确保所有数据库表结构一致
3. 备份和修复数据库
"""

import os
import sqlite3
import logging
import shutil
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_database(db_path):
    """
    备份数据库
    
    Args:
        db_path: 数据库路径
    
    Returns:
        备份数据库路径
    """
    if not os.path.exists(db_path):
        logger.error(f"数据库不存在: {db_path}")
        return None
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_path = f"{db_path}.{timestamp}.bak"
    
    # 复制数据库文件
    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"已备份数据库: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"备份数据库失败: {str(e)}")
        return None

def check_table_structure(conn, table_name="news"):
    """
    检查表结构
    
    Args:
        conn: 数据库连接
        table_name: 表名
        
    Returns:
        表结构信息
    """
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # 检查表是否存在
        if not columns:
            logger.warning(f"表 {table_name} 不存在")
            return None
        
        # 获取列名列表
        column_names = [col[1] for col in columns]
        logger.info(f"表 {table_name} 的列: {', '.join(column_names)}")
        
        return column_names
    except Exception as e:
        logger.error(f"检查表结构失败: {str(e)}")
        return None

def fix_database(db_path):
    """
    修复数据库
    
    Args:
        db_path: 数据库路径
    
    Returns:
        是否成功修复
    """
    if not os.path.exists(db_path):
        logger.error(f"数据库不存在: {db_path}")
        return False
    
    # 备份数据库
    backup_database(db_path)
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        
        # 检查表结构
        columns = check_table_structure(conn)
        
        if columns is None:
            # 如果表不存在，创建表
            logger.info(f"在 {db_path} 中创建 news 表")
            conn.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                url TEXT,
                source TEXT,
                pub_time TEXT,
                author TEXT,
                category TEXT,
                tags TEXT,
                summary TEXT,
                image_urls TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            logger.info(f"已在 {db_path} 中创建 news 表")
        else:
            # 检查是否缺少 pub_time 字段
            if 'pub_time' not in columns and 'publish_time' not in columns:
                logger.info(f"在 {db_path} 的 news 表中添加 pub_time 列")
                conn.execute("ALTER TABLE news ADD COLUMN pub_time TEXT")
                logger.info(f"已在 {db_path} 的 news 表中添加 pub_time 列")
            elif 'publish_time' in columns and 'pub_time' not in columns:
                # 重命名 publish_time 为 pub_time
                logger.info(f"在 {db_path} 的 news 表中将 publish_time 重命名为 pub_time")
                
                # SQLite不直接支持重命名列，需要创建新表并复制数据
                # 1. 创建临时表
                conn.execute('''
                CREATE TABLE news_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    content TEXT,
                    url TEXT,
                    source TEXT,
                    pub_time TEXT,
                    author TEXT,
                    category TEXT,
                    tags TEXT,
                    summary TEXT,
                    image_urls TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # 2. 复制数据
                conn.execute('''
                INSERT INTO news_temp (id, title, content, url, source, pub_time, author, category, tags, summary, image_urls, created_at, updated_at)
                SELECT id, title, content, url, source, publish_time, author, category, tags, summary, image_urls, created_at, updated_at
                FROM news
                ''')
                
                # 3. 删除旧表
                conn.execute("DROP TABLE news")
                
                # 4. 重命名新表
                conn.execute("ALTER TABLE news_temp RENAME TO news")
                
                logger.info(f"已在 {db_path} 的 news 表中将 publish_time 重命名为 pub_time")
            
            # 检查其他必要字段
            required_columns = [
                'id', 'title', 'content', 'url', 'source', 'author', 
                'category', 'tags', 'summary', 'image_urls', 
                'created_at', 'updated_at'
            ]
            
            for col in required_columns:
                if col not in columns:
                    logger.info(f"在 {db_path} 的 news 表中添加 {col} 列")
                    data_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if col == 'id' else "TIMESTAMP DEFAULT CURRENT_TIMESTAMP" if col in ['created_at', 'updated_at'] else "TEXT"
                    
                    # 如果是主键列，需要特殊处理
                    if col == 'id':
                        # 检查是否有记录
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM news")
                        count = cursor.fetchone()[0]
                        
                        if count > 0:
                            logger.warning(f"表 news 已有 {count} 条记录，无法添加 id 主键列")
                            continue
                    
                    try:
                        conn.execute(f"ALTER TABLE news ADD COLUMN {col} {data_type}")
                        logger.info(f"已在 {db_path} 的 news 表中添加 {col} 列")
                    except sqlite3.OperationalError as e:
                        logger.warning(f"添加 {col} 列失败: {str(e)}")
        
        # 提交更改
        conn.commit()
        
        # 关闭连接
        conn.close()
        
        logger.info(f"已成功修复数据库: {db_path}")
        return True
    except Exception as e:
        logger.error(f"修复数据库失败: {str(e)}")
        return False

def main():
    """主函数"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    logger.info("开始修复数据库")
    
    # 寻找所有数据库文件
    db_dirs = [
        os.path.join(project_root, "data"),
        os.path.join(project_root, "app", "db"),
        os.path.join(project_root, "app", "web")
    ]
    
    source_dirs = ["东方财富", "凤凰财经", "新浪财经", "网易财经", "腾讯财经"]
    
    for db_dir in db_dirs:
        if os.path.exists(db_dir):
            # 修复目录下的所有 .db 文件
            for root, _, files in os.walk(db_dir):
                for file in files:
                    if file.endswith(".db"):
                        db_path = os.path.join(root, file)
                        logger.info(f"修复数据库: {db_path}")
                        fix_database(db_path)
    
    # 修复特定数据源的数据库
    for source in source_dirs:
        db_path = os.path.join(project_root, "data", f"{source}.db")
        if os.path.exists(db_path):
            logger.info(f"修复数据源数据库: {db_path}")
            fix_database(db_path)
    
    logger.info("数据库修复完成")

if __name__ == "__main__":
    main() 