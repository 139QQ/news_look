#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试新闻详情获取
"""

import os
import sys
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_news_detail")

# 添加项目根目录到 sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入必要的类
try:
    from database import Database
    logger.info("成功导入自定义 Database 类")
except ImportError:
    logger.warning("无法导入自定义 Database 类")

try:
    from newslook.utils.database import NewsDatabase
    logger.info("成功导入 NewsDatabase 类")
except ImportError:
    logger.warning("无法导入 NewsDatabase 类")

# 测试函数
def test_get_news_by_id():
    """测试从数据库中获取指定ID的新闻"""
    # 测试 Database 类
    if 'Database' in locals() or 'Database' in globals():
        try:
            logger.info("测试自定义 Database 类...")
            db = Database()
            # 打印数据库路径
            if hasattr(db, 'all_db_paths'):
                logger.info(f"Database 类数据库路径: {db.all_db_paths}")
            else:
                logger.warning("Database 类没有 all_db_paths 属性")
            
            # 测试几个ID
            for news_id in ['腾讯财经_1', '腾讯财经_2', '腾讯财经_3']:
                logger.info(f"测试获取新闻 ID: {news_id}")
                news = db.get_news_by_id(news_id)
                if news:
                    logger.info(f"找到新闻: {news.get('title', '无标题')}")
                else:
                    logger.warning(f"未找到新闻 ID: {news_id}")
        except Exception as e:
            logger.error(f"测试 Database 类出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 测试 NewsDatabase 类
    if 'NewsDatabase' in locals() or 'NewsDatabase' in globals():
        try:
            logger.info("测试 NewsDatabase 类...")
            db = NewsDatabase(use_all_dbs=True)
            # 打印数据库路径
            if hasattr(db, 'all_db_paths'):
                logger.info(f"NewsDatabase 类数据库路径: {db.all_db_paths}")
            else:
                logger.warning("NewsDatabase 类没有 all_db_paths 属性")
            
            # 测试几个ID
            for news_id in ['腾讯财经_1', '腾讯财经_2', '腾讯财经_3']:
                logger.info(f"测试获取新闻 ID: {news_id}")
                news = db.get_news_by_id(news_id)
                if news:
                    logger.info(f"找到新闻: {news.get('title', '无标题')}")
                    # 打印关键字段
                    for field in ['id', 'title', 'source', 'pub_time', 'content']:
                        logger.info(f"{field}: {news.get(field, 'None')}")
                else:
                    logger.warning(f"未找到新闻 ID: {news_id}")
        except Exception as e:
            logger.error(f"测试 NewsDatabase 类出错: {str(e)}")
            import traceback
            traceback.print_exc()

def test_database_paths():
    """测试数据库路径是否正确"""
    # 检查数据目录
    data_dir = os.path.join(os.getcwd(), 'data', 'db')
    logger.info(f"数据目录: {data_dir}")
    
    if os.path.exists(data_dir):
        # 列出所有数据库文件
        db_files = [f for f in os.listdir(data_dir) if f.endswith('.db')]
        logger.info(f"找到 {len(db_files)} 个数据库文件: {', '.join(db_files)}")
        
        # 检查腾讯财经数据库
        tencent_db = os.path.join(data_dir, '腾讯财经.db')
        if os.path.exists(tencent_db):
            logger.info(f"腾讯财经数据库存在: {tencent_db}")
            # 检查文件大小
            size = os.path.getsize(tencent_db) / 1024
            logger.info(f"腾讯财经数据库大小: {size:.2f} KB")
        else:
            logger.warning(f"腾讯财经数据库不存在: {tencent_db}")
    else:
        logger.error(f"数据目录不存在: {data_dir}")

# 主函数
if __name__ == "__main__":
    logger.info("开始测试新闻详情获取...")
    test_database_paths()
    test_get_news_by_id()
    logger.info("测试完成") 