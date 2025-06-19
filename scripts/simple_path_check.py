#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化的数据库路径检查脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

def check_database_paths():
    """检查数据库路径配置"""
    print("=" * 50)
    print("数据库路径配置检查")
    print("=" * 50)
    
    # 1. 检查统一数据库路径管理器
    print("\n1. 统一数据库路径管理器")
    print("-" * 30)
    try:
        from backend.newslook.core.database_path_manager import get_database_path_manager
        
        db_path_manager = get_database_path_manager()
        unified_db_dir = str(db_path_manager.db_dir)
        print(f"✓ 统一数据库目录: {unified_db_dir}")
        
        # 检查各数据源路径
        sources = ["东方财富", "新浪财经", "网易财经", "凤凰财经"]
        for source in sources:
            path = db_path_manager.get_source_db_path(source)
            print(f"  - {source}: {path}")
            
    except Exception as e:
        print(f"✗ 统一数据库路径管理器失败: {e}")
        return False
    
    # 2. 检查配置文件
    print("\n2. 配置文件检查")
    print("-" * 30)
    try:
        config_file = project_root / "configs" / "app.yaml"
        if config_file.exists():
            print(f"✓ 配置文件存在: {config_file}")
            
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            db_config = config.get('database', {})
            config_db_dir = db_config.get('db_dir', 'data/db')
            print(f"✓ 配置中的数据库目录: {config_db_dir}")
            
            # 检查是否一致
            if config_db_dir == "data/db" and unified_db_dir.endswith("data/db"):
                print("✓ 配置与实际路径一致")
            else:
                print(f"⚠ 配置与实际路径可能不一致")
                
        else:
            print(f"✗ 配置文件不存在: {config_file}")
            
    except Exception as e:
        print(f"✗ 配置文件检查失败: {e}")
    
    # 3. 检查实际数据库文件
    print("\n3. 实际数据库文件")
    print("-" * 30)
    try:
        db_info = db_path_manager.get_database_info()
        
        print(f"总数据库文件数: {len(db_info)}")
        
        standard_files = 0
        for db_path, info in db_info.items():
            status = "✓" if info['location'] == 'standard' else "⚠"
            size_mb = info['size_mb']
            print(f"  {status} {info['name']}: {size_mb:.1f} MB")
            if info['location'] == 'standard':
                standard_files += 1
        
        print(f"\n标准位置文件: {standard_files}/{len(db_info)}")
        
        if standard_files == len(db_info):
            print("✓ 所有数据库文件都在标准位置")
        else:
            print(f"⚠ 有 {len(db_info) - standard_files} 个文件不在标准位置")
            
    except Exception as e:
        print(f"✗ 数据库文件检查失败: {e}")
    
    # 4. 环境变量检查
    print("\n4. 环境变量检查")
    print("-" * 30)
    
    db_dir_env = os.environ.get('DB_DIR')
    if db_dir_env:
        print(f"✓ DB_DIR环境变量: {db_dir_env}")
        if db_dir_env == unified_db_dir:
            print("✓ 环境变量与统一路径一致")
        else:
            print("⚠ 环境变量与统一路径不一致")
    else:
        print("⚠ DB_DIR环境变量未设置")
    
    return True


def main():
    """主函数"""
    print("NewsLook 数据库路径简化检查")
    print()
    
    success = check_database_paths()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 检查完成")
        print("   如发现问题，请运行 scripts/fix_database_paths.py 修复")
    else:
        print("❌ 检查过程中出现错误")
    print("=" * 50)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 