#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器集成测试
测试新配置管理器与各组件的集成情况
"""

import os
import sys
from pathlib import Path

# 添加项目路径 - 从tests/backend/integration/回到项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

def test_config_manager_basic():
    """测试配置管理器基础功能"""
    print("=== 测试配置管理器基础功能 ===")
    
    try:
        from backend.newslook.core.config_manager import get_config
        config = get_config()
        
        print("✅ 配置管理器导入成功")
        
        # 测试各种配置访问
        app_info = config.get_app_info()
        print(f"应用信息: {app_info}")
        
        db_config = config.database
        print(f"数据库配置: type={db_config.type}, dir={db_config.db_dir}")
        
        web_config = config.web
        print(f"Web配置: host={web_config.host}, port={web_config.port}, debug={web_config.debug}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("NewsLook 配置管理器集成测试")
    print("=" * 50)
    
    result = test_config_manager_basic()
    
    if result:
        print("🎉 配置管理器集成测试通过！")
    else:
        print("⚠️  配置管理器集成测试失败")

if __name__ == '__main__':
    main() 