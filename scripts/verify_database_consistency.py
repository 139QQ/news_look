#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库路径一致性验证脚本
检查爬虫输出位置和Web界面数据库连接是否一致
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

from backend.newslook.core.database_path_manager import get_database_path_manager
from backend.newslook.crawlers.manager import CrawlerManager
from backend.newslook.web import create_app
from backend.newslook.utils.logger import get_logger

logger = get_logger(__name__)


def check_database_path_consistency():
    """检查数据库路径一致性"""
    print("=" * 60)
    print("数据库路径一致性验证")
    print("=" * 60)
    
    # 1. 检查统一数据库路径管理器
    print("\n1. 统一数据库路径管理器")
    print("-" * 40)
    try:
        db_path_manager = get_database_path_manager()
        unified_db_dir = str(db_path_manager.db_dir)
        print(f"✓ 统一数据库目录: {unified_db_dir}")
        
        # 显示标准数据库路径
        standard_paths = {}
        for source in ["东方财富", "新浪财经", "网易财经", "凤凰财经", "腾讯财经"]:
            path = db_path_manager.get_source_db_path(source)
            standard_paths[source] = path
            print(f"  - {source}: {path}")
            
    except Exception as e:
        print(f"✗ 统一数据库路径管理器初始化失败: {e}")
        return False
    
    # 2. 检查爬虫管理器数据库路径
    print("\n2. 爬虫管理器数据库路径")
    print("-" * 40)
    try:
        crawler_manager = CrawlerManager()
        crawler_db_dir = crawler_manager.settings.get('DB_DIR')
        print(f"✓ 爬虫管理器数据库目录: {crawler_db_dir}")
        
        # 检查各个爬虫的数据库路径
        crawler_paths = {}
        for name, crawler in crawler_manager.crawlers.items():
            if hasattr(crawler, 'db_path'):
                crawler_paths[name] = crawler.db_path
                print(f"  - {name}: {crawler.db_path}")
        
        # 验证路径一致性
        if crawler_db_dir == unified_db_dir:
            print("✓ 爬虫管理器与统一路径管理器一致")
        else:
            print(f"✗ 路径不一致: 爬虫={crawler_db_dir}, 统一={unified_db_dir}")
            
    except Exception as e:
        print(f"✗ 爬虫管理器初始化失败: {e}")
        return False
    
    # 3. 检查Web应用数据库路径
    print("\n3. Web应用数据库路径")
    print("-" * 40)
    try:
        app = create_app()
        with app.app_context():
            web_db_dir = app.config.get('DB_DIR')
            print(f"✓ Web应用数据库目录: {web_db_dir}")
            
            # 检查Web应用的数据库实例
            if hasattr(app, 'db') and app.db:
                print(f"✓ Web应用数据库实例已初始化")
                print(f"  - 使用所有数据库: {app.db.use_all_dbs}")
                print(f"  - 数据库池数量: {len(app.db.pools)}")
            
            # 验证路径一致性
            if web_db_dir == unified_db_dir:
                print("✓ Web应用与统一路径管理器一致")
            else:
                print(f"✗ 路径不一致: Web={web_db_dir}, 统一={unified_db_dir}")
                
    except Exception as e:
        print(f"✗ Web应用初始化失败: {e}")
        return False
    
    # 4. 检查实际数据库文件
    print("\n4. 实际数据库文件检查")
    print("-" * 40)
    try:
        db_info = db_path_manager.get_database_info()
        total_files = len(db_info)
        standard_location_files = sum(1 for info in db_info.values() if info['location'] == 'standard')
        
        print(f"总数据库文件数: {total_files}")
        print(f"标准位置文件数: {standard_location_files}")
        print(f"其他位置文件数: {total_files - standard_location_files}")
        
        print("\n数据库文件详情:")
        for db_path, info in db_info.items():
            status = "✓" if info['location'] == 'standard' else "⚠"
            size_kb = info['size'] / 1024
            print(f"  {status} {info['name']}: {db_path} ({size_kb:.1f} KB)")
            
        if standard_location_files == total_files:
            print("✓ 所有数据库文件都在标准位置")
        else:
            print(f"⚠ 有 {total_files - standard_location_files} 个文件不在标准位置")
            
    except Exception as e:
        print(f"✗ 数据库文件检查失败: {e}")
        return False
    
    # 5. 路径一致性总结
    print("\n5. 路径一致性总结")
    print("-" * 40)
    
    all_consistent = True
    
    # 检查关键路径是否一致
    paths_to_check = [
        ("统一路径管理器", unified_db_dir),
        ("爬虫管理器", crawler_db_dir),
        ("Web应用", web_db_dir)
    ]
    
    unique_paths = set(path for _, path in paths_to_check)
    if len(unique_paths) == 1:
        print("✓ 所有组件使用相同的数据库目录")
        print(f"  统一目录: {list(unique_paths)[0]}")
    else:
        print("✗ 发现路径不一致:")
        for name, path in paths_to_check:
            print(f"  - {name}: {path}")
        all_consistent = False
    
    # 检查爬虫数据库路径是否符合标准
    inconsistent_crawlers = []
    for name, crawler_path in crawler_paths.items():
        if name in standard_paths:
            if crawler_path != standard_paths[name]:
                inconsistent_crawlers.append((name, crawler_path, standard_paths[name]))
    
    if inconsistent_crawlers:
        print("✗ 发现爬虫路径不一致:")
        for name, actual, expected in inconsistent_crawlers:
            print(f"  - {name}: 实际={actual}, 期望={expected}")
        all_consistent = False
    else:
        print("✓ 所有爬虫数据库路径符合标准")
    
    return all_consistent


def main():
    """主函数"""
    print("NewsLook 数据库路径一致性验证")
    print("检查爬虫输出位置和Web界面数据库连接是否一致")
    print()
    
    success = check_database_path_consistency()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 验证通过: 所有组件使用一致的数据库路径配置")
        print("   爬虫输出和Web界面数据库连接已统一")
    else:
        print("❌ 验证失败: 发现路径不一致的问题")
        print("   建议运行 scripts/fix_database_paths.py 修复")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 