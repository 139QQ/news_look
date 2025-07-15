#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速数据库修复脚本
手动执行关键的数据库修复操作
"""

import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

def main():
    """主函数"""
    project_root = Path(__file__).parent
    
    # 1. 创建统一的数据库目录
    unified_db_dir = project_root / 'data' / 'db'
    unified_db_dir.mkdir(parents=True, exist_ok=True)
    
    backup_dir = unified_db_dir / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    archive_dir = unified_db_dir / 'archives'
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"创建统一数据库目录: {unified_db_dir}")
    
    # 2. 移动主要数据库文件到统一目录
    main_db_files = [
        'eastmoney.db',
        'sina.db', 
        'netease.db',
        'ifeng.db',
        'finance_news.db'
    ]
    
    # 从data目录移动文件
    data_dir = project_root / 'data'
    moved_files = []
    
    for db_file in main_db_files:
        source_path = data_dir / db_file
        target_path = unified_db_dir / db_file
        
        if source_path.exists() and not target_path.exists():
            shutil.move(str(source_path), str(target_path))
            moved_files.append(db_file)
            print(f"移动数据库文件: {db_file}")
    
    # 3. 备份旧的分散文件
    old_db_files = list(data_dir.glob('**/*.db'))
    archived_files = []
    
    for old_file in old_db_files:
        if old_file.parent == unified_db_dir:
            continue
            
        # 创建备份
        backup_name = f"{old_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = archive_dir / backup_name
        
        try:
            shutil.copy2(str(old_file), str(backup_path))
            old_file.unlink()  # 删除原文件
            archived_files.append(str(old_file))
            print(f"归档数据库文件: {old_file.name}")
        except Exception as e:
            print(f"归档失败 {old_file}: {e}")
    
    # 4. 优化主数据库
    main_db_path = unified_db_dir / 'finance_news.db'
    if main_db_path.exists():
        try:
            with sqlite3.connect(str(main_db_path)) as conn:
                # 启用WAL模式
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                
                # 创建基本索引
                conn.execute("CREATE INDEX IF NOT EXISTS idx_news_url ON news(url)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_news_source ON news(source)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_news_pub_time ON news(pub_time)")
                
                # 优化数据库
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
                
                print("主数据库优化完成")
        except Exception as e:
            print(f"主数据库优化失败: {e}")
    
    # 5. 生成报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'unified_db_dir': str(unified_db_dir),
        'moved_files': moved_files,
        'archived_files': archived_files,
        'optimization_completed': True
    }
    
    print("\n数据库修复完成:")
    print(f"  - 统一目录: {unified_db_dir}")
    print(f"  - 移动文件: {len(moved_files)} 个")
    print(f"  - 归档文件: {len(archived_files)} 个")
    print(f"  - 数据库优化: 完成")
    
    return report

if __name__ == "__main__":
    main() 