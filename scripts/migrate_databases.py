#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 数据库迁移脚本

将旧的分散数据库文件迁移到统一的主数据库中。
"""

import os
import sys
import sqlite3
import shutil
import glob
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from backend.newslook.config import get_unified_db_path, get_unified_db_dir
    from backend.newslook.utils.logger import get_logger
except ImportError as e:
    print(f"[ERROR] 导入模块失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)

logger = get_logger(__name__)

class DatabaseMigrator:
    """数据库迁移器"""
    
    def __init__(self):
        self.project_root = project_root
        self.unified_db_path = get_unified_db_path()
        self.unified_db_dir = get_unified_db_dir()
        self.backup_dir = os.path.join(self.project_root, 'data', 'backups', 'migration')
        
        # 确保目录存在
        os.makedirs(self.unified_db_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def find_old_databases(self):
        """查找旧的分散数据库文件"""
        old_dbs = []
        
        # 搜索可能的旧数据库文件位置
        search_dirs = [
            self.project_root / 'data' / 'databases',
            self.project_root / 'data' / 'db',
            self.project_root / 'backend' / 'data',
            self.project_root / 'backend' / 'newslook' / 'crawlers' / 'data'
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                db_files = list(search_dir.glob('*.db'))
                for db_file in db_files:
                    # 排除统一的主数据库
                    if str(db_file) != self.unified_db_path:
                        old_dbs.append(str(db_file))
                        
        return old_dbs
    
    def backup_databases(self, db_files):
        """备份数据库文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_subdir = os.path.join(self.backup_dir, f'migration_{timestamp}')
        os.makedirs(backup_subdir, exist_ok=True)
        
        print(f"备份数据库文件到: {backup_subdir}")
        
        for db_file in db_files:
            if os.path.exists(db_file):
                backup_file = os.path.join(backup_subdir, os.path.basename(db_file))
                shutil.copy2(db_file, backup_file)
                print(f"  备份: {db_file} -> {backup_file}")
                
        # 也备份统一数据库（如果存在）
        if os.path.exists(self.unified_db_path):
            backup_unified = os.path.join(backup_subdir, 'finance_news_before_migration.db')
            shutil.copy2(self.unified_db_path, backup_unified)
            print(f"  备份统一数据库: {self.unified_db_path} -> {backup_unified}")
            
        return backup_subdir
    
    def create_unified_database(self):
        """创建统一数据库结构"""
        print(f"创建统一数据库: {self.unified_db_path}")
        
        conn = sqlite3.connect(self.unified_db_path)
        cursor = conn.cursor()
        
        # 创建新闻表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            content_html TEXT,
            pub_time TEXT,
            author TEXT,
            source TEXT,
            url TEXT UNIQUE,
            keywords TEXT,
            images TEXT,
            related_stocks TEXT,
            sentiment TEXT,
            classification TEXT,
            category TEXT,
            crawl_time TEXT
        )
        ''')
        
        # 创建关键词表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE,
            count INTEGER DEFAULT 1,
            last_updated TEXT
        )
        ''')
        
        # 创建新闻-关键词关联表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_keywords (
            news_id TEXT,
            keyword_id INTEGER,
            PRIMARY KEY (news_id, keyword_id),
            FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
            FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建股票表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            code TEXT PRIMARY KEY,
            name TEXT,
            count INTEGER DEFAULT 1,
            last_updated TEXT
        )
        ''')
        
        # 创建新闻-股票关联表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_stocks (
            news_id TEXT,
            stock_code TEXT,
            PRIMARY KEY (news_id, stock_code),
            FOREIGN KEY (news_id) REFERENCES news(id) ON DELETE CASCADE,
            FOREIGN KEY (stock_code) REFERENCES stocks(code) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        conn.close()
        print("统一数据库结构创建完成")
    
    def migrate_database(self, source_db_path):
        """迁移单个数据库"""
        print(f"迁移数据库: {source_db_path}")
        
        if not os.path.exists(source_db_path):
            print(f"  数据库文件不存在，跳过: {source_db_path}")
            return 0
            
        try:
            # 连接源数据库
            source_conn = sqlite3.connect(source_db_path)
            source_cursor = source_conn.cursor()
            
            # 连接目标数据库
            target_conn = sqlite3.connect(self.unified_db_path)
            target_cursor = target_conn.cursor()
            
            # 检查源数据库中的表
            source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = source_cursor.fetchall()
            
            migrated_count = 0
            
            for (table_name,) in tables:
                if table_name == 'news':
                    # 迁移新闻数据
                    source_cursor.execute("SELECT * FROM news")
                    news_rows = source_cursor.fetchall()
                    
                    # 获取列名
                    source_cursor.execute("PRAGMA table_info(news)")
                    columns_info = source_cursor.fetchall()
                    column_names = [col[1] for col in columns_info]
                    
                    for row in news_rows:
                        try:
                            # 构建插入语句
                            placeholders = ','.join(['?' for _ in column_names])
                            insert_sql = f"INSERT OR IGNORE INTO news ({','.join(column_names)}) VALUES ({placeholders})"
                            
                            target_cursor.execute(insert_sql, row)
                            migrated_count += 1
                            
                        except sqlite3.Error as e:
                            print(f"    迁移新闻记录失败: {e}")
                            continue
                            
            target_conn.commit()
            source_conn.close()
            target_conn.close()
            
            print(f"  成功迁移 {migrated_count} 条新闻记录")
            return migrated_count
            
        except Exception as e:
            print(f"  迁移失败: {e}")
            return 0
    
    def verify_migration(self, old_dbs):
        """验证迁移结果"""
        print("\n验证迁移结果:")
        
        # 统计统一数据库中的记录数
        conn = sqlite3.connect(self.unified_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news")
        unified_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT source, COUNT(*) FROM news GROUP BY source")
        source_counts = cursor.fetchall()
        
        conn.close()
        
        print(f"统一数据库总记录数: {unified_count}")
        print("按来源统计:")
        for source, count in source_counts:
            print(f"  {source}: {count} 条")
            
        # 统计原数据库记录数
        total_old_count = 0
        for old_db in old_dbs:
            try:
                conn = sqlite3.connect(old_db)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM news")
                count = cursor.fetchone()[0]
                total_old_count += count
                conn.close()
                print(f"原数据库 {os.path.basename(old_db)}: {count} 条")
            except Exception as e:
                print(f"无法读取 {old_db}: {e}")
                
        print(f"原数据库总记录数: {total_old_count}")
        
        if unified_count >= total_old_count * 0.9:  # 允许10%的数据丢失（去重等原因）
            print("✅ 迁移验证通过")
            return True
        else:
            print("❌ 迁移验证失败，数据丢失过多")
            return False
    
    def cleanup_old_databases(self, old_dbs, backup_dir):
        """清理旧数据库文件"""
        print(f"\n清理旧数据库文件（已备份到 {backup_dir}）:")
        
        for old_db in old_dbs:
            try:
                if os.path.exists(old_db):
                    os.remove(old_db)
                    print(f"  删除: {old_db}")
            except Exception as e:
                print(f"  删除失败 {old_db}: {e}")
    
    def migrate_all(self, cleanup=False):
        """执行完整的迁移流程"""
        print("=" * 60)
        print("NewsLook 数据库迁移")
        print("=" * 60)
        print(f"迁移时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"统一数据库路径: {self.unified_db_path}")
        print()
        
        # 1. 查找旧数据库
        old_dbs = self.find_old_databases()
        if not old_dbs:
            print("未发现需要迁移的旧数据库文件")
            return True
            
        print(f"发现 {len(old_dbs)} 个旧数据库文件:")
        for db in old_dbs:
            file_size = os.path.getsize(db) / 1024 if os.path.exists(db) else 0
            print(f"  - {db} ({file_size:.1f} KB)")
        print()
        
        # 2. 备份数据库
        backup_dir = self.backup_databases(old_dbs)
        print()
        
        # 3. 创建统一数据库
        self.create_unified_database()
        print()
        
        # 4. 迁移数据
        print("开始迁移数据:")
        total_migrated = 0
        for old_db in old_dbs:
            migrated = self.migrate_database(old_db)
            total_migrated += migrated
        print(f"总共迁移 {total_migrated} 条记录")
        print()
        
        # 5. 验证迁移
        migration_success = self.verify_migration(old_dbs)
        print()
        
        # 6. 清理旧文件（可选）
        if cleanup and migration_success:
            self.cleanup_old_databases(old_dbs, backup_dir)
        elif not cleanup:
            print("旧数据库文件保留，如需删除请手动执行或使用 --cleanup 参数")
        
        print("=" * 60)
        if migration_success:
            print("✅ 数据库迁移完成")
            print(f"统一数据库: {self.unified_db_path}")
            print(f"备份位置: {backup_dir}")
        else:
            print("❌ 数据库迁移失败")
            
        return migration_success

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NewsLook 数据库迁移工具")
    parser.add_argument('--cleanup', action='store_true', help='迁移完成后删除旧数据库文件')
    parser.add_argument('--force', action='store_true', help='强制执行迁移（覆盖现有统一数据库）')
    
    args = parser.parse_args()
    
    migrator = DatabaseMigrator()
    
    # 检查统一数据库是否已存在
    if os.path.exists(migrator.unified_db_path) and not args.force:
        print(f"统一数据库已存在: {migrator.unified_db_path}")
        print("如需重新迁移，请使用 --force 参数")
        return 1
    
    success = migrator.migrate_all(cleanup=args.cleanup)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 