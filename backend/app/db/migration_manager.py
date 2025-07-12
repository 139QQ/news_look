#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库迁移管理器
"""

import os
import logging
import importlib.util
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self, db_path: str, migrations_dir: str = 'app/db/migrations'):
        """
        初始化迁移管理器
        
        Args:
            db_path: 数据库路径
            migrations_dir: 迁移脚本目录
        """
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        
        # 确保迁移目录存在
        os.makedirs(migrations_dir, exist_ok=True)
    
    def get_migrations(self) -> List[str]:
        """
        获取所有迁移脚本
        
        Returns:
            List[str]: 迁移脚本路径列表
        """
        migrations = []
        for file in os.listdir(self.migrations_dir):
            if file.endswith('.py') and file != '__init__.py':
                migrations.append(os.path.join(self.migrations_dir, file))
        return sorted(migrations)
    
    def run_migration(self, migration_path: str) -> bool:
        """
        运行指定的迁移脚本
        
        Args:
            migration_path: 迁移脚本路径
            
        Returns:
            bool: 是否成功
        """
        try:
            # 加载迁移模块
            spec = importlib.util.spec_from_file_location(
                f"migration_{os.path.basename(migration_path)}", 
                migration_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 执行迁移
            if hasattr(module, 'migrate'):
                module.migrate(self.db_path)
                logger.info(f"成功执行迁移: {migration_path}")
                return True
            else:
                logger.error(f"迁移脚本缺少migrate函数: {migration_path}")
                return False
                
        except Exception as e:
            logger.error(f"执行迁移失败: {migration_path}, 错误: {str(e)}")
            return False
    
    def run_all_migrations(self) -> bool:
        """
        运行所有迁移脚本
        
        Returns:
            bool: 是否全部成功
        """
        migrations = self.get_migrations()
        if not migrations:
            logger.info("没有找到迁移脚本")
            return True
        
        success = True
        for migration in migrations:
            if not self.run_migration(migration):
                success = False
                break
        
        return success
    
    def create_migration(self, name: str) -> Optional[str]:
        """
        创建新的迁移脚本
        
        Args:
            name: 迁移名称
            
        Returns:
            Optional[str]: 创建的迁移脚本路径，如果失败则返回None
        """
        try:
            # 生成迁移文件名
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{name}.py"
            filepath = os.path.join(self.migrations_dir, filename)
            
            # 创建迁移文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库迁移脚本
"""

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def migrate(db_path):
    """
    执行数据库迁移
    
    Args:
        db_path: 数据库路径
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # TODO: 在这里添加迁移逻辑
        
        conn.commit()
        logger.info("数据库迁移完成")
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()
''')
            
            logger.info(f"已创建迁移脚本: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"创建迁移脚本失败: {str(e)}")
            return None

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库迁移工具')
    parser.add_argument('--db', required=True, help='数据库路径')
    parser.add_argument('--migrations-dir', default='app/db/migrations', help='迁移脚本目录')
    parser.add_argument('--create', help='创建新的迁移脚本')
    parser.add_argument('--run', action='store_true', help='运行所有迁移')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = MigrationManager(args.db, args.migrations_dir)
    
    if args.create:
        filepath = manager.create_migration(args.create)
        if not filepath:
            return 1
    
    if args.run:
        if not manager.run_all_migrations():
            return 1
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main()) 