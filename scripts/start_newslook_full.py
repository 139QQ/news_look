#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 完整启动脚本
自动启动后端API服务器，并提供访问前端界面的链接
"""

import os
import sys
import subprocess
import time
import webbrowser
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def check_databases():
    """检查数据库文件"""
    db_dir = os.path.join(project_root, 'databases')
    if not os.path.exists(db_dir):
        print("❌ 数据库目录不存在: databases/")
        print("   请先运行爬虫生成数据: python run.py")
        return False
    
    db_files = [f for f in os.listdir(db_dir) if f.endswith('.db')]
    if not db_files:
        print("❌ 未发现任何数据库文件")
        print("   请先运行爬虫生成数据: python run.py")
        return False
    
    print(f"✅ 发现 {len(db_files)} 个数据库文件")
    for db_file in db_files:
        file_size = os.path.getsize(os.path.join(db_dir, db_file)) / 1024
        print(f"   - {db_file} ({file_size:.1f} KB)")
    
    return True

def create_frontend_files():
    """创建前端文件"""
    from start_frontend_simple import create_simple_frontend
    return create_simple_frontend()

def main():
    """主函数"""
    print("=" * 60)
    print("         NewsLook 财经新闻爬虫系统")
    print("=" * 60)
    print()
    
    # 检查数据库
    print("🔍 检查数据库文件...")
    if not check_databases():
        print("\n❓ 是否要先运行爬虫获取数据？(y/n): ", end="")
        choice = input().lower().strip()
        if choice in ['y', 'yes', '是']:
            print("🚀 启动爬虫...")
            try:
                subprocess.run([sys.executable, 'run.py'], check=True)
            except subprocess.CalledProcessError:
                print("❌ 爬虫运行失败")
                return
        else:
            print("⚠️  将使用空数据库启动系统")
    
    print()
    
    # 创建前端文件
    print("📁 准备前端文件...")
    try:
        static_dir = create_frontend_files()
        print(f"✅ 前端文件准备完成: {static_dir}")
    except Exception as e:
        print(f"❌ 前端文件创建失败: {e}")
        return
    
    print()
    
    # 启动后端API服务器
    print("🚀 启动后端API服务器...")
    try:
        # 设置环境变量
        os.environ['DB_DIR'] = os.path.join(project_root, 'databases')
        
        # 导入Web应用
        from backend.app.web import create_app
        
        config = {
            'DB_DIR': os.path.join(project_root, 'databases'),
            'DEBUG': False  # 生产模式
        }
        
        app = create_app(config)
        
        print("✅ 后端API服务器启动成功")
        print()
        print("📊 系统访问地址:")
        print("   - 后端API服务器: http://127.0.0.1:5000")
        print("   - 前端管理界面: http://127.0.0.1:5000/static/index.html")
        print("   - API健康检查: http://127.0.0.1:5000/health")
        print()
        print("💡 提示:")
        print("   - 在另一个终端运行 'python start_frontend_simple.py' 启动独立前端服务器")
        print("   - 按 Ctrl+C 停止服务器")
        print()
        
        # 注册静态文件路由
        @app.route('/static/<path:filename>')
        def serve_static(filename):
            return app.send_static_file(filename)
        
        # 将前端文件复制到Flask静态目录
        import shutil
        flask_static_dir = os.path.join(app.root_path, 'static')
        os.makedirs(flask_static_dir, exist_ok=True)
        
        # 复制index.html
        src_html = os.path.join(static_dir, 'index.html')
        dst_html = os.path.join(flask_static_dir, 'index.html')
        if os.path.exists(src_html):
            shutil.copy2(src_html, dst_html)
            print(f"📋 前端文件已复制到Flask静态目录")
        
        # 自动打开浏览器
        time.sleep(1)  # 等待服务器启动
        webbrowser.open('http://127.0.0.1:5000/static/index.html')
        
        # 启动服务器
        app.run(host='127.0.0.1', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 