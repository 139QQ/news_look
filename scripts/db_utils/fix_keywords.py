#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
import logging

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_keywords_in_db(db_path):
    """修复数据库中的关键词格式问题"""
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    logger.info(f"开始修复数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查news表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
        if not cursor.fetchone():
            logger.warning(f"数据库 {db_path} 中没有news表")
            conn.close()
            return False
        
        # 检查keywords字段是否存在
        cursor.execute("PRAGMA table_info(news)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'keywords' not in columns:
            logger.warning(f"数据库 {db_path} 中的news表没有keywords字段")
            conn.close()
            return False
        
        # 获取所有记录的ID和keywords
        cursor.execute("SELECT id, keywords FROM news")
        rows = cursor.fetchall()
        logger.debug(f"数据库 {db_path} 中共有 {len(rows)} 条记录")
        
        fixed_count = 0
        for row in rows:
            news_id, keywords = row
            logger.debug(f"处理记录 ID: {news_id}, 关键词: {keywords}, 类型: {type(keywords)}")
            
            if not keywords:
                logger.debug(f"记录 ID: {news_id} 的关键词为空，跳过")
                continue
            
            try:
                # 尝试解析JSON
                if isinstance(keywords, str):
                    json.loads(keywords)
                    logger.debug(f"记录 ID: {news_id} 的关键词格式正确，跳过")
                    continue
            except json.JSONDecodeError as e:
                # JSON解析失败，需要修复
                logger.debug(f"记录 ID: {news_id} 的关键词JSON解析失败: {str(e)}")
                try:
                    # 如果是字符串列表，尝试将其转换为JSON字符串
                    if isinstance(keywords, str):
                        # 尝试分割字符串
                        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
                        if keyword_list:
                            # 将列表转换为JSON字符串
                            fixed_keywords = json.dumps(keyword_list)
                            logger.debug(f"修复记录 ID: {news_id} 的关键词: {keywords} -> {fixed_keywords}")
                            cursor.execute("UPDATE news SET keywords = ? WHERE id = ?", (fixed_keywords, news_id))
                            fixed_count += 1
                        else:
                            logger.debug(f"记录 ID: {news_id} 的关键词分割后为空")
                except Exception as e:
                    logger.error(f"修复关键词失败，ID: {news_id}, 错误: {str(e)}")
        
        conn.commit()
        logger.info(f"数据库 {db_path} 修复完成，共修复 {fixed_count} 条记录")
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"修复数据库 {db_path} 时出错: {str(e)}")
        return False

def fix_all_databases():
    """修复所有数据库的关键词格式"""
    # 数据库目录
    db_dir = 'data/db'
    
    if not os.path.exists(db_dir):
        logger.error(f"数据库目录不存在: {db_dir}")
        return
    
    # 获取所有数据库文件
    db_files = [f for f in os.listdir(db_dir) if f.endswith('.db') and not f.endswith('.bak')]
    
    if not db_files:
        logger.warning(f"在 {db_dir} 目录中没有找到数据库文件")
        return
    
    logger.info(f"找到 {len(db_files)} 个数据库文件: {db_files}")
    
    # 修复每个数据库
    for db_file in db_files:
        db_path = os.path.join(db_dir, db_file)
        fix_keywords_in_db(db_path)

if __name__ == "__main__":
    logger.info("开始修复数据库关键词格式问题")
    fix_all_databases()
    logger.info("数据库关键词格式修复完成") 