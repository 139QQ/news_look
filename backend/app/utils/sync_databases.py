#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库同步工具 - 将源数据库的新闻数据同步到主数据库
"""

import os
import sys
import glob
import sqlite3
import logging
from datetime import datetime
from backend.app.db.SQLiteManager import SQLiteManager
from backend.app.config import get_settings
from backend.app.utils.logger import get_logger

# 设置日志记录器
logger = get_logger("db_sync")

def sync_all_databases():
    """
    将所有源数据库中的数据同步到主数据库
    
    Returns:
        tuple: (成功数, 跳过数, 总数)
    """
    # 获取数据库目录
    settings = get_settings()
    db_dir = settings.get('DB_DIR', os.path.join(os.getcwd(), 'data', 'db'))
    
    # 确保目录存在
    if not os.path.exists(db_dir):
        logger.error(f"数据库目录不存在: {db_dir}")
        return 0, 0, 0
    
    # 获取所有数据库文件路径
    db_files = glob.glob(os.path.join(db_dir, "*.db"))
    
    # 排除主数据库
    main_db_path = os.path.join(db_dir, "finance_news.db")
    source_db_files = [f for f in db_files if f != main_db_path and f != os.path.join(db_dir, "user_preferences.db")]
    
    if not source_db_files:
        logger.info("没有找到任何源数据库文件")
        return 0, 0, 0
    
    logger.info(f"找到 {len(source_db_files)} 个源数据库")
    
    # 初始化计数器
    total_count = 0
    success_count = 0
    skip_count = 0
    
    # 遍历所有源数据库
    for source_db_file in source_db_files:
        source_name = os.path.basename(source_db_file).replace(".db", "")
        logger.info(f"开始从 {source_name} 同步数据")
        
        try:
            # 从源数据库读取新闻
            source_conn = sqlite3.connect(source_db_file)
            source_conn.row_factory = sqlite3.Row
            
            # 查询源数据库中的所有新闻
            cursor = source_conn.cursor()
            cursor.execute("SELECT * FROM news")
            news_rows = cursor.fetchall()
            
            source_count = len(news_rows)
            total_count += source_count
            
            logger.info(f"从 {source_name} 读取到 {source_count} 条新闻")
            
            # 初始化主数据库连接
            with SQLiteManager(db_path=main_db_path) as main_db:
                # 将每条新闻插入到主数据库
                for row in news_rows:
                    try:
                        # 转换为字典
                        news = dict(row)
                        
                        # 确保有ID
                        if 'id' not in news or not news['id']:
                            import hashlib
                            if 'url' in news and news['url']:
                                news['id'] = hashlib.md5(news['url'].encode('utf-8')).hexdigest()
                            else:
                                title_source = f"{news.get('title', '')}_{news.get('source', '')}"
                                news['id'] = hashlib.md5(title_source.encode('utf-8')).hexdigest()
                        
                        # 确保来源字段正确
                        if 'source' not in news or not news['source']:
                            news['source'] = source_name
                        
                        # 确保爬取时间字段存在
                        if 'crawl_time' not in news or not news['crawl_time']:
                            news['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 保存到主数据库
                        if main_db.save_news(news):
                            success_count += 1
                        else:
                            skip_count += 1
                            
                    except Exception as e:
                        logger.error(f"同步新闻失败: {str(e)}")
                        skip_count += 1
            
            source_conn.close()
            logger.info(f"从 {source_name} 同步完成: 成功 {success_count}, 跳过 {skip_count}")
            
        except Exception as e:
            logger.error(f"处理数据库 {source_name} 时出错: {str(e)}")
    
    logger.info(f"同步全部完成: 总共 {total_count} 条新闻, 成功 {success_count}, 跳过 {skip_count}")
    return success_count, skip_count, total_count

if __name__ == "__main__":
    # 添加项目根目录到系统路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 运行同步
    success, skip, total = sync_all_databases()
    print(f"同步结果: 总共 {total} 条新闻, 成功 {success}, 跳过 {skip}") 