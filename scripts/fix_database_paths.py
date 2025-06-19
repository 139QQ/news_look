#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库路径修复脚本
统一修复数据库文件位置和路径配置问题
"""

import os
import sys
import shutil
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from backend.newslook.core.database_path_manager import get_database_path_manager
from backend.newslook.utils.logger import get_logger

logger = get_logger(__name__)


def check_database_files():
    """检查当前数据库文件分布情况"""
    logger.info("=== 检查数据库文件分布情况 ===")
    
    db_manager = get_database_path_manager()
    db_info = db_manager.get_database_info()
    
    standard_dbs = []
    old_location_dbs = []
    
    for db_path, info in db_info.items():
        if info['location'] == 'standard':
            standard_dbs.append((db_path, info))
        else:
            old_location_dbs.append((db_path, info))
    
    logger.info(f"标准位置数据库文件 ({len(standard_dbs)}个):")
    for db_path, info in standard_dbs:
        logger.info(f"  - {info['name']} ({info['size_mb']} MB)")
    
    logger.info(f"旧位置数据库文件 ({len(old_location_dbs)}个):")
    for db_path, info in old_location_dbs:
        logger.info(f"  - {info['name']} ({info['size_mb']} MB) -> 需要迁移")
    
    return standard_dbs, old_location_dbs


def test_database_connections():
    """测试数据库连接"""
    logger.info("=== 测试数据库连接 ===")
    
    db_manager = get_database_path_manager()
    all_dbs = db_manager.discover_all_db_files()
    
    connection_results = {}
    
    for db_path in all_dbs:
        try:
            conn = sqlite3.connect(db_path, timeout=5.0)
            cursor = conn.cursor()
            
            # 测试基本查询
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # 如果有news表，查询记录数
            news_count = 0
            if any('news' in str(table[0]).lower() for table in tables):
                cursor.execute("SELECT COUNT(*) FROM news")
                news_count = cursor.fetchone()[0]
            
            conn.close()
            
            connection_results[db_path] = {
                'status': 'success',
                'tables': len(tables),
                'news_count': news_count
            }
            
            logger.info(f"✓ {Path(db_path).name}: {len(tables)}个表, {news_count}条新闻")
            
        except Exception as e:
            connection_results[db_path] = {
                'status': 'error',
                'error': str(e)
            }
            logger.error(f"✗ {Path(db_path).name}: 连接失败 - {e}")
    
    return connection_results


def migrate_databases():
    """迁移数据库文件到标准位置"""
    logger.info("=== 迁移数据库文件 ===")
    
    db_manager = get_database_path_manager()
    
    # 执行迁移
    migrated_files = db_manager.migrate_old_databases()
    
    if migrated_files:
        logger.info(f"成功迁移 {len(migrated_files)} 个数据库文件:")
        for migration in migrated_files:
            logger.info(f"  {migration}")
    else:
        logger.info("没有需要迁移的数据库文件")
    
    return migrated_files


def cleanup_old_files(dry_run=True):
    """清理旧位置的数据库文件"""
    action = "预览清理" if dry_run else "执行清理"
    logger.info(f"=== {action}旧数据库文件 ===")
    
    db_manager = get_database_path_manager()
    cleanup_files = db_manager.cleanup_old_databases(dry_run=dry_run)
    
    if cleanup_files:
        action_text = "将清理" if dry_run else "已清理"
        logger.info(f"{action_text} {len(cleanup_files)} 个旧数据库文件:")
        for file_path in cleanup_files:
            logger.info(f"  - {file_path}")
    else:
        logger.info("没有需要清理的旧数据库文件")
    
    return cleanup_files


def verify_web_database_access():
    """验证Web应用的数据库访问"""
    logger.info("=== 验证Web应用数据库访问 ===")
    
    try:
        from backend.newslook.utils.enhanced_database import EnhancedNewsDatabase
        
        # 测试Enhanced数据库连接
        db = EnhancedNewsDatabase(timeout=10.0)
        
        if not db.pools:
            logger.error("✗ EnhancedNewsDatabase未找到任何数据库连接池")
            return False
        
        logger.info(f"✓ EnhancedNewsDatabase初始化成功，连接池数量: {len(db.pools)}")
        
        # 测试查询
        try:
            news_list = db.query_news(limit=1)
            total_count = db.get_news_count()
            
            logger.info(f"✓ 数据库查询成功，总新闻数: {total_count}")
            db.close()
            return True
            
        except Exception as e:
            logger.error(f"✗ 数据库查询失败: {e}")
            db.close()
            return False
            
    except Exception as e:
        logger.error(f"✗ Web数据库访问测试失败: {e}")
        return False


def create_backup():
    """创建数据库备份"""
    logger.info("=== 创建数据库备份 ===")
    
    db_manager = get_database_path_manager()
    backup_dir = db_manager.backup_dir
    
    # 创建时间戳备份目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_timestamp_dir = backup_dir / f"fix_backup_{timestamp}"
    backup_timestamp_dir.mkdir(exist_ok=True)
    
    backed_up_files = []
    
    # 备份所有数据库文件
    all_dbs = db_manager.discover_all_db_files()
    
    for db_path in all_dbs:
        db_file = Path(db_path)
        if db_file.exists():
            backup_path = backup_timestamp_dir / db_file.name
            try:
                shutil.copy2(str(db_file), str(backup_path))
                backed_up_files.append(str(backup_path))
                logger.info(f"✓ 备份: {db_file.name}")
            except Exception as e:
                logger.error(f"✗ 备份失败 {db_file.name}: {e}")
    
    logger.info(f"备份完成，备份目录: {backup_timestamp_dir}")
    logger.info(f"备份文件数量: {len(backed_up_files)}")
    
    return backup_timestamp_dir, backed_up_files


def main():
    """主函数"""
    logger.info("NewsLook 数据库路径修复工具")
    logger.info("=" * 50)
    
    try:
        # 1. 检查当前数据库文件分布
        standard_dbs, old_dbs = check_database_files()
        
        # 2. 测试数据库连接
        connection_results = test_database_connections()
        
        # 3. 创建备份
        if standard_dbs or old_dbs:
            backup_dir, backup_files = create_backup()
            logger.info(f"已创建备份，共 {len(backup_files)} 个文件")
        
        # 4. 迁移数据库文件
        migrated_files = migrate_databases()
        
        # 5. 验证Web数据库访问
        web_access_ok = verify_web_database_access()
        
        # 6. 预览清理旧文件
        cleanup_preview = cleanup_old_files(dry_run=True)
        
        # 7. 生成修复报告
        logger.info("=" * 50)
        logger.info("修复完成报告:")
        logger.info(f"  - 发现标准位置数据库: {len(standard_dbs)} 个")
        logger.info(f"  - 发现旧位置数据库: {len(old_dbs)} 个")
        logger.info(f"  - 迁移数据库文件: {len(migrated_files)} 个")
        logger.info(f"  - Web数据库访问: {'正常' if web_access_ok else '异常'}")
        logger.info(f"  - 可清理旧文件: {len(cleanup_preview)} 个")
        
        if cleanup_preview:
            response = input("\n是否要删除旧位置的数据库文件? (y/N): ")
            if response.lower() == 'y':
                cleaned_files = cleanup_old_files(dry_run=False)
                logger.info(f"已清理 {len(cleaned_files)} 个旧数据库文件")
        
        logger.info("数据库路径修复完成!")
        
        if not web_access_ok:
            logger.warning("Web数据库访问仍有问题，请检查配置或联系开发人员")
        
    except Exception as e:
        logger.error(f"修复过程中出现错误: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 