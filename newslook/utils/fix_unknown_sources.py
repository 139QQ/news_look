#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复未知来源新闻并整理数据库
"""

import os
import sqlite3
import shutil
from datetime import datetime
import logging
from app.utils.database import NewsDatabase
from app.utils.logger import get_logger
from app.config import get_settings

# 获取日志记录器
logger = get_logger(__name__)

def update_unknown_sources():
    """
    更新所有未知来源的新闻
    """
    try:
        db = NewsDatabase(use_all_dbs=True)
        unknown_count_before = db.get_news_count(source='未知来源') + db.get_news_count(source='')
        logger.info(f"更新前未知来源新闻数量: {unknown_count_before}")
        
        # 更新未知来源
        updated_count = db.update_unknown_sources()
        logger.info(f"已更新未知来源新闻数量: {updated_count}")
        
        unknown_count_after = db.get_news_count(source='未知来源') + db.get_news_count(source='')
        logger.info(f"更新后剩余未知来源新闻数量: {unknown_count_after}")
        
        return unknown_count_before, updated_count, unknown_count_after
    except Exception as e:
        logger.error(f"更新未知来源失败: {str(e)}")
        return 0, 0, 0

def force_update_unknown_sources():
    """
    强制更新所有未知来源的新闻，将其重新分配到正确的来源
    这个函数会处理那些无法通过URL识别的新闻，直接设置为一个默认来源
    
    Returns:
        int: 更新的记录数量
    """
    try:
        # 获取数据库目录
        settings = get_settings()
        db_dir = settings.get('DB_DIR')
        if not db_dir:
            db_dir = os.path.join(os.getcwd(), 'data', 'db')
        
        unknown_db_path = os.path.join(db_dir, '未知来源.db')
        
        # 检查未知来源数据库是否存在
        if not os.path.exists(unknown_db_path):
            logger.info("未知来源数据库不存在，无需强制更新")
            return 0
            
        # 连接到未知来源数据库
        conn = sqlite3.connect(unknown_db_path)
        cursor = conn.cursor()
        
        # 设置默认来源
        default_source = "东方财富"  # 可以根据需要更改默认来源
        
        # 更新所有未知来源的新闻
        cursor.execute("""
            UPDATE news 
            SET source = ? 
            WHERE source = '未知来源' OR source IS NULL OR source = ''
        """, (default_source,))
        
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"已强制更新 {updated_count} 条未知来源的新闻为 {default_source}")
        return updated_count
    except Exception as e:
        logger.error(f"强制更新未知来源失败: {str(e)}")
        return 0

def merge_unknown_source_db():
    """
    将未知来源数据库中的数据合并到主数据库或对应来源数据库中
    """
    try:
        # 获取数据库目录
        settings = get_settings()
        db_dir = settings.get('DB_DIR')
        if not db_dir:
            db_dir = os.path.join(os.getcwd(), 'data', 'db')
        
        unknown_db_path = os.path.join(db_dir, '未知来源.db')
        main_db_path = os.path.join(db_dir, 'finance_news.db')
        
        # 检查未知来源数据库是否存在
        if not os.path.exists(unknown_db_path):
            logger.info("未知来源数据库不存在，无需合并")
            return 0
            
        # 连接到未知来源数据库
        unknown_conn = sqlite3.connect(unknown_db_path)
        unknown_conn.row_factory = sqlite3.Row
        unknown_cursor = unknown_conn.cursor()
        
        # 连接到主数据库
        main_conn = sqlite3.connect(main_db_path)
        main_cursor = main_conn.cursor()
        
        # 获取未知来源数据库中的所有新闻
        unknown_cursor.execute("SELECT * FROM news")
        news_items = unknown_cursor.fetchall()
        
        merged_count = 0
        source_db_paths = {}
        
        for news in news_items:
            news_dict = dict(news)
            source = news_dict.get('source')
            
            # 如果source为空或未知来源，把它放到主数据库
            if not source or source == '未知来源':
                try:
                    # 检查新闻是否已存在于主数据库中
                    main_cursor.execute("SELECT id FROM news WHERE url = ?", (news_dict.get('url'),))
                    if not main_cursor.fetchone():
                        # 插入到主数据库
                        main_cursor.execute('''
                            INSERT INTO news (title, content, url, publish_time, crawl_time, 
                            source, category, image_url, sentiment, summary)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            news_dict.get('title', ''),
                            news_dict.get('content', ''),
                            news_dict.get('url', ''),
                            news_dict.get('publish_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            news_dict.get('crawl_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            news_dict.get('source', '未知来源'),
                            news_dict.get('category', '财经'),
                            news_dict.get('image_url', ''),
                            news_dict.get('sentiment', 0),
                            news_dict.get('summary', '')
                        ))
                        merged_count += 1
                except Exception as e:
                    logger.error(f"合并新闻到主数据库失败: {str(e)}")
            else:
                # 根据来源将新闻放到对应的数据库
                if source not in source_db_paths:
                    source_db_path = os.path.join(db_dir, f"{source}.db")
                    # 检查来源数据库是否存在
                    if os.path.exists(source_db_path):
                        source_db_paths[source] = sqlite3.connect(source_db_path)
                        source_db_paths[source].cursor().execute('''
                            CREATE TABLE IF NOT EXISTS news (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                title TEXT,
                                content TEXT,
                                url TEXT UNIQUE,
                                publish_time TEXT,
                                crawl_time TEXT,
                                source TEXT,
                                category TEXT,
                                image_url TEXT,
                                sentiment REAL,
                                summary TEXT
                            )
                        ''')
                    else:
                        # 如果来源数据库不存在，使用主数据库
                        source_db_paths[source] = main_conn
                
                try:
                    source_conn = source_db_paths[source]
                    source_cursor = source_conn.cursor()
                    
                    # 检查新闻是否已存在于来源数据库中
                    source_cursor.execute("SELECT id FROM news WHERE url = ?", (news_dict.get('url'),))
                    if not source_cursor.fetchone():
                        # 插入到来源数据库
                        source_cursor.execute('''
                            INSERT INTO news (title, content, url, publish_time, crawl_time, 
                            source, category, image_url, sentiment, summary)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            news_dict.get('title', ''),
                            news_dict.get('content', ''),
                            news_dict.get('url', ''),
                            news_dict.get('publish_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            news_dict.get('crawl_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            source,
                            news_dict.get('category', '财经'),
                            news_dict.get('image_url', ''),
                            news_dict.get('sentiment', 0),
                            news_dict.get('summary', '')
                        ))
                        merged_count += 1
                except Exception as e:
                    logger.error(f"合并新闻到来源数据库失败: {str(e)}")
        
        # 提交所有更改
        main_conn.commit()
        for conn in source_db_paths.values():
            if conn != main_conn:  # 避免重复提交主数据库
                conn.commit()
        
        # 关闭所有连接
        unknown_conn.close()
        main_conn.close()
        for conn in source_db_paths.values():
            if conn != main_conn:  # 避免重复关闭主数据库
                conn.close()
        
        logger.info(f"已合并 {merged_count} 条新闻从未知来源数据库到其他数据库")
        return merged_count
    except Exception as e:
        logger.error(f"合并未知来源数据库失败: {str(e)}")
        return 0

def remove_unknown_source_db():
    """
    删除未知来源数据库文件
    
    Returns:
        bool: 是否成功删除
    """
    try:
        # 获取数据库目录
        settings = get_settings()
        db_dir = settings.get('DB_DIR')
        if not db_dir:
            db_dir = os.path.join(os.getcwd(), 'data', 'db')
        
        unknown_db_path = os.path.join(db_dir, '未知来源.db')
        
        # 检查未知来源数据库是否存在
        if not os.path.exists(unknown_db_path):
            logger.info("未知来源数据库不存在，无需删除")
            return True
        
        # 创建备份
        backup_dir = os.path.join(db_dir, 'backup')
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_path = os.path.join(backup_dir, f"未知来源_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.db")
        shutil.copy2(unknown_db_path, backup_path)
        logger.info(f"已创建未知来源数据库备份: {backup_path}")
        
        # 删除未知来源数据库
        os.remove(unknown_db_path)
        logger.info("已删除未知来源数据库")
        
        return True
    except Exception as e:
        logger.error(f"删除未知来源数据库失败: {str(e)}")
        return False

def scan_all_databases_for_unknown_sources():
    """
    扫描所有数据库中的未知来源记录，并打印统计信息
    
    Returns:
        dict: 各数据库中未知来源记录的数量
    """
    try:
        # 获取数据库目录
        settings = get_settings()
        db_dir = settings.get('DB_DIR')
        if not db_dir:
            db_dir = os.path.join(os.getcwd(), 'data', 'db')
        
        # 扫描数据库目录中的所有数据库
        db_files = [f for f in os.listdir(db_dir) if f.endswith('.db') and os.path.isfile(os.path.join(db_dir, f))]
        
        results = {}
        total_unknown = 0
        
        logger.info(f"扫描 {len(db_files)} 个数据库文件中的未知来源记录...")
        
        for db_file in db_files:
            db_path = os.path.join(db_dir, db_file)
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 检查news表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                if not cursor.fetchone():
                    logger.warning(f"数据库 {db_file} 中没有news表，跳过")
                    conn.close()
                    continue
                
                # 查询未知来源或空来源的记录数
                cursor.execute("SELECT COUNT(*) FROM news WHERE source = '未知来源' OR source IS NULL OR source = ''")
                count = cursor.fetchone()[0]
                
                # 如果存在未知来源，则记录下来
                if count > 0:
                    results[db_file] = count
                    total_unknown += count
                    logger.info(f"数据库 {db_file} 中有 {count} 条未知来源记录")
                
                conn.close()
            except Exception as e:
                logger.error(f"扫描数据库 {db_file} 失败: {str(e)}")
        
        logger.info(f"扫描完成，共找到 {total_unknown} 条未知来源记录")
        return results
    except Exception as e:
        logger.error(f"扫描所有数据库失败: {str(e)}")
        return {}

def fix_all_databases(force_update=True):
    """
    修复所有数据库中的未知来源记录
    
    Args:
        force_update: 是否强制更新未知来源
    
    Returns:
        dict: 各数据库的修复结果统计
    """
    try:
        # 获取数据库目录
        settings = get_settings()
        db_dir = settings.get('DB_DIR')
        if not db_dir:
            db_dir = os.path.join(os.getcwd(), 'data', 'db')
        
        # 扫描所有数据库获取未知来源统计
        unknown_sources = scan_all_databases_for_unknown_sources()
        
        # 如果没有未知来源记录，直接返回
        if not unknown_sources:
            logger.info("所有数据库中都没有未知来源记录，无需修复")
            return {}
        
        results = {}
        
        # 遍历处理每个有未知来源记录的数据库
        for db_file, count in unknown_sources.items():
            logger.info(f"开始修复数据库 {db_file} 中的 {count} 条未知来源记录...")
            
            db_path = os.path.join(db_dir, db_file)
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 首先尝试根据URL推断来源
                updated_by_url = 0
                cursor.execute("""
                    SELECT id, url FROM news 
                    WHERE source = '未知来源' OR source IS NULL OR source = ''
                """)
                news_items = cursor.fetchall()
                
                for news_id, url in news_items:
                    if not url:
                        continue
                        
                    url = url.lower()
                    new_source = None
                    
                    # 根据URL推断来源
                    if 'eastmoney.com' in url:
                        new_source = '东方财富'
                    elif 'sina.com' in url or 'sina.cn' in url:
                        new_source = '新浪财经'
                    elif 'qq.com' in url or 'finance.qq.com' in url or 'news.qq.com' in url:
                        new_source = '腾讯财经'
                    elif '163.com' in url or 'money.163.com' in url:
                        new_source = '网易财经'
                    elif 'ifeng.com' in url:
                        new_source = '凤凰财经'
                    elif 'jrj.com' in url:
                        new_source = '金融界'
                    # 添加其他可能的来源判断...
                    
                    if new_source:
                        cursor.execute("UPDATE news SET source = ? WHERE id = ?", (new_source, news_id))
                        updated_by_url += 1
                
                if updated_by_url > 0:
                    conn.commit()
                    logger.info(f"根据URL更新了 {updated_by_url} 条记录")
                
                # 如果启用了强制更新，则将剩余的未知来源记录设置为默认来源
                if force_update:
                    # 根据数据库文件名设置默认来源
                    default_source = os.path.splitext(db_file)[0]
                    if default_source == 'finance_news':
                        default_source = '东方财富'  # 为主数据库设置一个默认来源
                    
                    cursor.execute("""
                        UPDATE news SET source = ? 
                        WHERE source = '未知来源' OR source IS NULL OR source = ''
                    """, (default_source,))
                    
                    force_updated = cursor.rowcount
                    conn.commit()
                    logger.info(f"强制更新了 {force_updated} 条记录为 {default_source}")
                    
                    # 记录结果
                    results[db_file] = {
                        'initial_count': count,
                        'updated_by_url': updated_by_url,
                        'force_updated': force_updated,
                        'remaining': 0
                    }
                else:
                    # 再次查询剩余的未知来源记录数
                    cursor.execute("SELECT COUNT(*) FROM news WHERE source = '未知来源' OR source IS NULL OR source = ''")
                    remaining = cursor.fetchone()[0]
                    
                    # 记录结果
                    results[db_file] = {
                        'initial_count': count,
                        'updated_by_url': updated_by_url,
                        'force_updated': 0,
                        'remaining': remaining
                    }
                
                conn.close()
            except Exception as e:
                logger.error(f"修复数据库 {db_file} 失败: {str(e)}")
                results[db_file] = {
                    'initial_count': count,
                    'updated_by_url': 0,
                    'force_updated': 0,
                    'remaining': count,
                    'error': str(e)
                }
        
        # 汇总结果
        total_initial = sum(r['initial_count'] for r in results.values())
        total_updated_by_url = sum(r['updated_by_url'] for r in results.values())
        total_force_updated = sum(r['force_updated'] for r in results.values())
        total_remaining = sum(r['remaining'] for r in results.values())
        
        logger.info(f"全部数据库修复完成: 初始未知来源记录 {total_initial} 条")
        logger.info(f"根据URL更新: {total_updated_by_url} 条")
        logger.info(f"强制更新: {total_force_updated} 条")
        logger.info(f"剩余未知来源: {total_remaining} 条")
        
        return results
    except Exception as e:
        logger.error(f"修复所有数据库失败: {str(e)}")
        return {}

def update_unknown_sources_direct():
    """
    直接使用SQLite接口更新所有数据库中未知来源的新闻，根据URL推断正确的数据源
    避免ORM相关的错误
    
    Returns:
        int: 更新的记录数量
    """
    try:
        logger.info("开始直接更新所有数据库中未知来源的新闻数据...")
        
        # 获取数据库目录
        settings = get_settings()
        db_dir = settings.get('DB_DIR')
        if not db_dir:
            db_dir = os.path.join(os.getcwd(), 'data', 'db')
            
        # 获取所有数据库文件
        db_files = [f for f in os.listdir(db_dir) if f.endswith('.db') and os.path.isfile(os.path.join(db_dir, f))]
        
        total_updated = 0
        
        for db_file in db_files:
            db_path = os.path.join(db_dir, db_file)
            try:
                # 连接数据库
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 检查news表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                if not cursor.fetchone():
                    logger.warning(f"数据库 {db_file} 中没有news表，跳过")
                    conn.close()
                    continue
                
                # 查询所有未知来源的新闻
                cursor.execute("""
                    SELECT id, url FROM news 
                    WHERE source = '未知来源' OR source IS NULL OR source = ''
                """)
                news_items = cursor.fetchall()
                
                if not news_items:
                    logger.info(f"数据库 {db_file} 中没有未知来源的新闻")
                    conn.close()
                    continue
                
                db_updated = 0
                
                for news_id, url in news_items:
                    if not url:
                        continue
                        
                    # 将URL转为小写以便匹配
                    url = url.lower()
                    new_source = None
                    
                    # 根据URL推断来源
                    if 'eastmoney.com' in url:
                        new_source = '东方财富'
                    elif 'sina.com' in url or 'sina.cn' in url:
                        new_source = '新浪财经'
                    elif 'qq.com' in url or 'finance.qq.com' in url or 'news.qq.com' in url:
                        new_source = '腾讯财经'
                    elif '163.com' in url or 'money.163.com' in url:
                        new_source = '网易财经'
                    elif 'ifeng.com' in url:
                        new_source = '凤凰财经'
                    elif 'jrj.com' in url:
                        new_source = '金融界'
                    elif 'cs.com.cn' in url:
                        new_source = '中国证券网'
                    elif 'hexun.com' in url:
                        new_source = '和讯网'
                    elif 'cnstock.com' in url:
                        new_source = '中证网'
                    elif 'xinhuanet.com' in url:
                        new_source = '新华网'
                    elif 'people.com.cn' in url:
                        new_source = '人民网'
                    elif 'cctv.com' in url:
                        new_source = 'CCTV'
                    elif 'stcn.com' in url:
                        new_source = '证券时报网'
                    elif '21jingji.com' in url:
                        new_source = '21世纪经济报道'
                    elif 'caixin.com' in url:
                        new_source = '财新网'
                    
                    if new_source:
                        cursor.execute("UPDATE news SET source = ? WHERE id = ?", (new_source, news_id))
                        db_updated += 1
                
                # 提交更改
                if db_updated > 0:
                    conn.commit()
                    logger.info(f"数据库 {db_file} 中更新了 {db_updated} 条未知来源的新闻")
                    total_updated += db_updated
                
                conn.close()
            except Exception as e:
                logger.error(f"更新数据库 {db_file} 中的未知来源失败: {str(e)}")
        
        logger.info(f"直接更新完成，共更新 {total_updated} 条未知来源的新闻")
        return total_updated
    except Exception as e:
        logger.error(f"直接更新未知来源失败: {str(e)}")
        return 0

def fix_all(force_update=True):
    """
    执行所有修复步骤
    
    Args:
        force_update: 是否强制更新未知来源
    """
    logger.info("=" * 50)
    logger.info("开始修复未知来源数据")
    logger.info("=" * 50)
    
    # 扫描所有数据库中的未知来源记录
    unknown_sources_by_db = scan_all_databases_for_unknown_sources()
    
    # 尝试修复所有数据库中的未知来源记录
    logger.info("开始修复所有数据库中的未知来源记录...")
    fix_results = fix_all_databases(force_update)
    
    # 第一步：直接更新未知来源（避免ORM错误）
    updated_count = update_unknown_sources_direct()
    logger.info(f"直接更新未知来源完成: 已更新 {updated_count} 条")
    
    # 如果还有未知来源且启用了强制更新
    if updated_count == 0 and force_update:
        # 第二步：强制更新未知来源
        force_updated = force_update_unknown_sources()
        logger.info(f"强制更新未知来源完成: 已更新 {force_updated} 条")
    
    # 第三步：合并未知来源数据库
    merged_count = merge_unknown_source_db()
    logger.info(f"合并未知来源数据库完成: 已合并 {merged_count} 条新闻")
    
    # 第四步：删除未知来源数据库
    removed = remove_unknown_source_db()
    if removed:
        logger.info("删除未知来源数据库成功")
    else:
        logger.error("删除未知来源数据库失败")
    
    logger.info("=" * 50)
    logger.info("修复未知来源数据完成")
    logger.info("=" * 50)

if __name__ == "__main__":
    print("\n")
    print("=" * 80)
    print("      财经新闻爬虫系统 - 未知来源修复工具")
    print("=" * 80)
    print("\n")
    print("开始扫描并修复所有数据库中的未知来源数据...\n")
    
    # 执行修复
    fix_all(force_update=True)
    
    print("\n处理完成，修复结果摘要:")
    
    # 获取数据库状态
    settings = get_settings()
    db_dir = settings.get('DB_DIR')
    if not db_dir:
        db_dir = os.path.join(os.getcwd(), 'data', 'db')
    
    print(f"\n数据库目录: {db_dir}")
    print(f"数据库文件: {', '.join([f for f in os.listdir(db_dir) if f.endswith('.db')])}")
    
    # 检查是否还有未知来源的数据
    try:
        db = NewsDatabase(use_all_dbs=True)
        remaining = db.get_news_count(source='未知来源') + db.get_news_count(source='')
        if remaining > 0:
            print(f"\n警告: 仍有 {remaining} 条未知来源的新闻需要手动处理")
        else:
            print("\n所有未知来源的新闻已修复完成")
    except Exception as e:
        print(f"\n检查剩余未知来源时出错: {str(e)}")
    
    print("\n" + "=" * 80) 