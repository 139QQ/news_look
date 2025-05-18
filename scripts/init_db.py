#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库初始化脚本
"""

import os
import sys
import logging

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.db.migration_manager import MigrationManager

logger = logging.getLogger(__name__)

def init_db(db_path: str, migrations_dir: str = 'app/db/migrations'):
    """
    初始化数据库
    
    Args:
        db_path: 数据库路径
        migrations_dir: 迁移脚本目录
    """
    try:
        # 确保数据库目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # 运行迁移
        manager = MigrationManager(db_path, migrations_dir)
        if manager.run_all_migrations():
            logger.info(f"数据库初始化完成: {db_path}")
            return True
        else:
            logger.error("数据库初始化失败")
            return False
            
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        return False

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库初始化工具')
    parser.add_argument('--db', required=True, help='数据库路径')
    parser.add_argument('--migrations-dir', default='app/db/migrations', help='迁移脚本目录')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if init_db(args.db, args.migrations_dir):
        return 0
    return 1

if __name__ == '__main__':
    sys.exit(main())