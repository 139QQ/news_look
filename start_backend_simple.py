#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 简化后端启动脚本
用于测试和调试
"""

import os
import sys

# 添加项目路径到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app

def main():
    """主函数"""
    print("🚀 启动 NewsLook 后端服务器 (简化版)")
    print("="*50)
    
    try:
        # 创建应用
        app = create_app()
        
        print("📍 后端地址: http://127.0.0.1:5000")
        print("🔗 API地址: http://127.0.0.1:5000/api/health")
        print("="*50)
        
        # 启动服务器
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True
        )
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 