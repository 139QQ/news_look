#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 后端快速启动脚本
一键启动后端API服务器
"""

if __name__ == '__main__':
    import subprocess
    import sys
    
    print("🚀 NewsLook 后端快速启动")
    print("="*40)
    
    try:
        # 启动后端服务器
        subprocess.run([sys.executable, 'app.py'], check=True)
    except KeyboardInterrupt:
        print("\n👋 后端服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
    except FileNotFoundError:
        print("❌ 找不到app.py文件，请确保在项目根目录运行此脚本") 