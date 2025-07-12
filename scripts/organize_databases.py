#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库文件整理脚本
整理杂乱的数据库文件，统一命名规范和目录结构
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from backend.app.db.database_manager import DatabaseManager

def setup_logging():
    """设置日志"""
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'database_organize.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """主函数"""
    logger = setup_logging()
    
    print("=" * 60)
    print("NewsLook 数据库文件整理工具")
    print("=" * 60)
    
    # 显示当前分散的数据库文件
    print("\n📂 扫描分散的数据库文件...")
    
    # 初始化数据库管理器
    manager = DatabaseManager(str(project_root))
    
    # 显示统计信息
    print("\n📊 整理前统计信息:")
    stats = manager.get_database_stats()
    for source, info in stats.items():
        if info['exists'] and 'records' in info:
            print(f"  {source}: {info['records']} 条记录, {info['size_mb']} MB")
        else:
            print(f"  {source}: 文件不存在或无法访问")
    
    # 询问用户是否继续
    print(f"\n🎯 新的标准目录结构:")
    print(f"  {manager.db_dir}/")
    print(f"  ├── sina_finance.db")
    print(f"  ├── eastmoney_finance.db")
    print(f"  ├── netease_finance.db")
    print(f"  ├── ifeng_finance.db")
    print(f"  ├── backups/")
    print(f"  ├── archives/")
    print(f"  └── temp/")
    
    try:
        user_input = input("\n❓ 是否开始整理数据库文件? (y/N): ").strip().lower()
        if user_input not in ['y', 'yes']:
            print("❌ 用户取消操作")
            return
    except KeyboardInterrupt:
        print("\n❌ 用户中断操作")
        return
    
    # 开始整理
    print("\n🚀 开始整理数据库文件...")
    logger.info("开始数据库文件整理")
    
    try:
        results = manager.normalize_database_files()
        
        # 显示结果
        print("\n✅ 整理完成!")
        print(f"  📁 移动文件: {len(results['moved_files'])}")
        print(f"  💾 备份文件: {len(results['backup_files'])}")
        print(f"  ❌ 错误: {len(results['errors'])}")
        
        if results['moved_files']:
            print("\n📋 移动的文件:")
            for item in results['moved_files'][:10]:  # 只显示前10个
                print(f"  {item}")
            if len(results['moved_files']) > 10:
                print(f"  ... 共 {len(results['moved_files'])} 个文件")
        
        if results['backup_files']:
            print("\n💾 备份的文件:")
            for item in results['backup_files'][:10]:  # 只显示前10个
                print(f"  {item}")
            if len(results['backup_files']) > 10:
                print(f"  ... 共 {len(results['backup_files'])} 个文件")
        
        if results['errors']:
            print("\n⚠️ 错误信息:")
            for error in results['errors']:
                print(f"  {error}")
        
        # 显示整理后的统计信息
        print("\n📊 整理后统计信息:")
        stats = manager.get_database_stats()
        for source, info in stats.items():
            if info['exists'] and 'records' in info:
                print(f"  ✅ {source}: {info['records']} 条记录, {info['size_mb']} MB")
            else:
                print(f"  ❌ {source}: 文件不存在")
        
        # 生成报告
        report_path = project_root / 'DATABASE_CLEANUP_REPORT.md'
        print(f"\n📄 详细报告已生成: {report_path}")
        
        logger.info("数据库文件整理完成")
        
    except Exception as e:
        print(f"\n💥 整理过程中发生错误: {e}")
        logger.error(f"整理过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 