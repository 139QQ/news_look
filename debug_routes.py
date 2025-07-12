#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路由调试脚本
用于检查API端点注册情况和诊断路由问题
"""

import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_app_creation():
    """测试应用创建过程"""
    print("🔧 测试应用创建过程...")
    
    try:
        from app import create_app
        print("✅ 成功导入create_app函数")
        
        # 创建应用
        app = create_app()
        print("✅ 成功创建Flask应用")
        
        # 获取所有注册的路由
        print("\n📝 已注册的路由:")
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'route': str(rule.rule),
                'methods': list(rule.methods)
            })
        
        # 按路由排序
        routes.sort(key=lambda x: x['route'])
        
        # 打印所有路由
        api_routes = []
        other_routes = []
        
        for route in routes:
            route_info = f"{route['route']} -> {route['endpoint']} {route['methods']}"
            if route['route'].startswith('/api'):
                api_routes.append(route_info)
            else:
                other_routes.append(route_info)
        
        print(f"\n🔗 API路由 ({len(api_routes)}个):")
        for route in api_routes:
            print(f"  {route}")
        
        print(f"\n🌐 其他路由 ({len(other_routes)}个):")
        for route in other_routes:
            print(f"  {route}")
        
        # 检查特定的v1 API端点
        v1_endpoints = [
            '/api/v1/crawlers/status',
            '/api/v1/analytics/overview', 
            '/api/v1/analytics/echarts/data'
        ]
        
        print(f"\n🎯 检查关键v1端点:")
        for endpoint in v1_endpoints:
            found = any(route['route'] == endpoint for route in routes)
            status = "✅ 已注册" if found else "❌ 未注册"
            print(f"  {endpoint}: {status}")
        
        return app
        
    except Exception as e:
        print(f"❌ 应用创建失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_individual_functions():
    """测试独立函数"""
    print("\n🧪 测试独立组件...")
    
    try:
        # 测试数据库管理器
        from backend.newslook.core.unified_database_manager import get_unified_database_manager
        print("✅ 成功导入统一数据库管理器")
        
        db_manager = get_unified_database_manager()
        print("✅ 成功创建数据库管理器实例")
        
        # 测试爬虫管理器
        from backend.newslook.crawlers.manager import CrawlerManager
        print("✅ 成功导入爬虫管理器")
        
        crawler_manager = CrawlerManager()
        print("✅ 成功创建爬虫管理器实例")
        
    except Exception as e:
        print(f"❌ 组件测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_direct_api_call():
    """直接测试API调用"""
    print("\n🚀 测试直接API调用...")
    
    try:
        app = test_app_creation()
        if not app:
            return
        
        with app.test_client() as client:
            # 测试健康检查
            response = client.get('/api/health')
            print(f"健康检查: {response.status_code} - {response.get_json()}")
            
            # 测试新闻API
            response = client.get('/api/news')
            print(f"新闻API: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"  数据: {len(data.get('data', []))} 条新闻")
            
            # 测试v1端点
            v1_endpoints = [
                '/api/v1/crawlers/status',
                '/api/v1/analytics/overview',
                '/api/v1/analytics/echarts/data'
            ]
            
            for endpoint in v1_endpoints:
                response = client.get(endpoint)
                print(f"{endpoint}: {response.status_code}")
                if response.status_code != 200:
                    print(f"  错误: {response.get_data(as_text=True)}")
                    
    except Exception as e:
        print(f"❌ 直接API测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("🔍 NewsLook 路由调试工具")
    print("="*50)
    
    # 测试应用创建
    test_app_creation()
    
    # 测试独立组件
    test_individual_functions()
    
    # 测试直接API调用
    test_direct_api_call()
    
    print("\n✅ 调试完成")

if __name__ == '__main__':
    main() 