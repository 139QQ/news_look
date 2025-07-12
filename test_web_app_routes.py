#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试Web应用路由注册"""

import sys
import os

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("=== 测试Web应用路由注册 ===")
    
    # 导入Web应用创建函数
    from backend.app.web import create_app
    print("✅ Web应用模块导入成功")
    
    # 创建应用
    app = create_app()
    print("✅ Web应用创建成功")
    
    # 列出所有路由
    print(f"\n=== 应用中已注册的路由数量: {len(list(app.url_map.iter_rules()))} ===")
    for rule in app.url_map.iter_rules():
        print(f"{rule.rule} [{', '.join(rule.methods)}]")
    
    # 检查监控路由
    monitoring_routes = [rule for rule in app.url_map.iter_rules() if 'monitoring' in rule.rule]
    print(f"\n=== 监控路由数量: {len(monitoring_routes)} ===")
    if monitoring_routes:
        for route in monitoring_routes:
            print(f"- {route.rule} [{', '.join(route.methods)}]")
        print("✅ 监控路由注册成功")
    else:
        print("❌ 监控路由未找到")
        
    # 检查API路由
    api_routes = [rule for rule in app.url_map.iter_rules() if '/api/' in rule.rule]
    print(f"\n=== API路由数量: {len(api_routes)} ===")
    for route in api_routes:
        print(f"- {route.rule}")
        
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    
except Exception as e:
    print(f"❌ 其他错误: {e}")
    import traceback
    traceback.print_exc() 