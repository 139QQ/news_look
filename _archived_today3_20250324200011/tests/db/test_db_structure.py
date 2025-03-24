#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试新的数据库结构
"""

import os
import sys
import time
from datetime import datetime
import hashlib
import json

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database import NewsDatabase
from utils.db_manager import DatabaseManager
from utils.logger import setup_logger

logger = setup_logger()

def test_source_db():
    """测试来源专用数据库"""
    logger.info("=== 测试来源专用数据库 ===")
    
    # 创建不同来源的数据库
    sources = ['东方财富', '新浪财经', '腾讯财经', '网易财经']
    
    for source in sources:
        # 创建来源专用数据库
        db = NewsDatabase(source=source)
        
        # 生成测试数据
        for i in range(5):
            title = f"{source}测试新闻{i+1}"
            content = f"这是{source}的测试新闻内容{i+1}，用于测试来源专用数据库。"
            
            # 生成新闻ID
            news_id = hashlib.md5(f"{title}_{content}".encode('utf-8')).hexdigest()
            
            # 构建新闻数据
            news_item = {
                'id': news_id,
                'title': title,
                'content': content,
                'pub_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'author': f"{source}作者",
                'source': source,
                'category': f"测试分类{i % 3 + 1}",
                'url': f"https://example.com/{source}/{i+1}.html",
                'keywords': f"测试,{source},新闻,{i+1}",
                'sentiment': 0.5,
                'images': [f"https://example.com/images/{i+1}.jpg"],
                'related_stocks': [{"code": "000001", "name": "平安银行"}],
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 保存新闻
            db.save_news(news_item)
            logger.info(f"保存测试新闻: {title}")
        
        logger.info(f"{source}数据库测试完成")
    
    logger.info("所有来源数据库测试完成")

def test_query_news():
    """测试查询新闻"""
    logger.info("=== 测试查询新闻 ===")
    
    # 创建数据库管理器
    db_manager = DatabaseManager()
    
    # 获取所有数据库
    db_files = db_manager.list_databases()
    logger.info(f"找到 {len(db_files)} 个数据库文件: {db_files}")
    
    # 获取所有数据库统计信息
    stats = db_manager.get_database_stats()
    logger.info(f"数据库统计信息: {json.dumps(stats, ensure_ascii=False)}")
    
    # 从主数据库查询新闻
    main_db = NewsDatabase()
    news_list = main_db.query_news(limit=10)
    logger.info(f"主数据库查询结果: {len(news_list)} 条新闻")
    
    # 从来源数据库查询新闻
    source_db = NewsDatabase(source='东方财富')
    news_list = source_db.query_news(limit=10)
    logger.info(f"东方财富数据库查询结果: {len(news_list)} 条新闻")
    
    # 按分类查询
    news_list = main_db.query_news(category='测试分类1', limit=10)
    logger.info(f"按分类查询结果: {len(news_list)} 条新闻")
    
    # 按关键词查询
    news_list = main_db.query_news(keyword='测试', limit=10)
    logger.info(f"按关键词查询结果: {len(news_list)} 条新闻")

def test_merge_databases():
    """测试合并数据库"""
    logger.info("=== 测试合并数据库 ===")
    
    # 创建数据库管理器
    db_manager = DatabaseManager()
    
    # 合并前统计
    stats_before = db_manager.get_database_stats('finance_news.db')
    logger.info(f"合并前主数据库统计: {json.dumps(stats_before, ensure_ascii=False)}")
    
    # 合并数据库
    success = db_manager.merge_all_databases()
    logger.info(f"合并数据库{'成功' if success else '失败'}")
    
    # 合并后统计
    stats_after = db_manager.get_database_stats('finance_news.db')
    logger.info(f"合并后主数据库统计: {json.dumps(stats_after, ensure_ascii=False)}")

def test_backup_restore():
    """测试备份和恢复"""
    logger.info("=== 测试备份和恢复 ===")
    
    # 创建数据库管理器
    db_manager = DatabaseManager()
    
    # 备份主数据库
    backup_file = db_manager.backup_database('finance_news.db')
    logger.info(f"备份主数据库: {backup_file}")
    
    # 获取备份文件名
    backup_filename = os.path.basename(backup_file)
    
    # 恢复到临时数据库
    temp_db = 'temp_restored.db'
    success = db_manager.restore_database(backup_filename, temp_db)
    logger.info(f"恢复到临时数据库{'成功' if success else '失败'}")
    
    # 检查恢复的数据库
    stats = db_manager.get_database_stats(temp_db)
    logger.info(f"恢复的数据库统计: {json.dumps(stats, ensure_ascii=False)}")
    
    # 删除临时数据库
    success = db_manager.delete_database(temp_db)
    logger.info(f"删除临时数据库{'成功' if success else '失败'}")

def test_export_import():
    """测试导出和导入"""
    logger.info("=== 测试导出和导入 ===")
    
    # 创建数据库管理器
    db_manager = DatabaseManager()
    
    # 导出主数据库
    export_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'export_test.json')
    success = db_manager.export_data('finance_news.db', export_file)
    logger.info(f"导出主数据库{'成功' if success else '失败'}: {export_file}")
    
    # 创建临时数据库
    temp_db = 'temp_import.db'
    temp_db_path = os.path.join(db_manager.db_dir, temp_db)
    
    # 确保临时数据库不存在
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)
    
    # 初始化临时数据库
    temp_db_obj = NewsDatabase(temp_db_path)
    
    # 导入数据到临时数据库
    success = db_manager.import_data(temp_db, export_file)
    logger.info(f"导入数据到临时数据库{'成功' if success else '失败'}")
    
    # 检查导入的数据库
    stats = db_manager.get_database_stats(temp_db)
    logger.info(f"导入的数据库统计: {json.dumps(stats, ensure_ascii=False)}")
    
    # 删除临时数据库
    success = db_manager.delete_database(temp_db)
    logger.info(f"删除临时数据库{'成功' if success else '失败'}")
    
    # 删除导出文件
    if os.path.exists(export_file):
        os.remove(export_file)
        logger.info(f"删除导出文件: {export_file}")

def main():
    """主函数"""
    logger.info("开始测试新的数据库结构")
    
    # 确保数据目录存在
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # 测试来源专用数据库
    test_source_db()
    
    # 测试查询新闻
    test_query_news()
    
    # 测试合并数据库
    test_merge_databases()
    
    # 测试备份和恢复
    test_backup_restore()
    
    # 测试导出和导入
    test_export_import()
    
    logger.info("数据库结构测试完成")

if __name__ == "__main__":
    main() 