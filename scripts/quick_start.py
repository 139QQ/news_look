#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 快速启动脚本
启动后端服务器并测试API连接
"""

import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def start_backend_server():
    """启动后端服务器"""
    try:
        # 设置环境变量
        os.environ['DB_DIR'] = os.path.join(project_root, 'databases')
        
        # 导入Web应用
        from backend.app.web import create_app
        
        config = {
            'DB_DIR': os.path.join(project_root, 'databases'),
            'DEBUG': False
        }
        
        app = create_app(config)
        
        print("✅ 后端API服务器启动成功")
        print("📊 访问地址: http://127.0.0.1:5000")
        print("🔍 健康检查: http://127.0.0.1:5000/health")
        print("📰 新闻API: http://127.0.0.1:5000/api/news")
        print()
        
        # 启动服务器
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
        
    except Exception as e:
        print(f"❌ 启动后端服务器失败: {e}")
        import traceback
        traceback.print_exc()

def test_api_after_delay():
    """延迟后测试API"""
    time.sleep(3)  # 等待服务器启动
    
    try:
        import requests
        
        print("🔍 测试API连接...")
        
        # 测试健康检查
        response = requests.get("http://127.0.0.1:5000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查成功 - 数据库文件数: {data.get('database_files', 0)}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return
        
        # 测试新闻API
        response = requests.get("http://127.0.0.1:5000/api/news?page=1&page_size=3", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                news_count = len(data.get('data', []))
                total = data.get('total', 0)
                print(f"✅ 新闻API成功 - 返回 {news_count} 条新闻，总计 {total} 条")
            else:
                print(f"❌ 新闻API失败: {data.get('message', '未知错误')}")
        else:
            print(f"❌ 新闻API失败: {response.status_code}")
        
        print()
        print("🎉 系统启动成功！可以开始使用了")
        print("💡 在浏览器中访问 http://127.0.0.1:5000/health 查看系统状态")
        
        # 自动打开浏览器
        webbrowser.open("http://127.0.0.1:5000/health")
        
    except Exception as e:
        print(f"❌ API测试失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("         NewsLook 快速启动")
    print("=" * 60)
    print()
    
    # 检查数据库
    db_dir = os.path.join(project_root, 'databases')
    if os.path.exists(db_dir):
        db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
        print(f"📊 发现 {len(db_files)} 个数据库文件")
        for db_file in db_files:
            file_size = os.path.getsize(os.path.join(db_dir, db_file)) / 1024
            print(f"   - {db_file} ({file_size:.1f} KB)")
    else:
        print("⚠️  数据库目录不存在，将创建空数据库")
    
    print()
    print("🚀 启动后端API服务器...")
    
    # 在后台线程中测试API
    test_thread = threading.Thread(target=test_api_after_delay, daemon=True)
    test_thread.start()
    
    # 启动服务器（阻塞）
    try:
        start_backend_server()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")

if __name__ == "__main__":
    main() 