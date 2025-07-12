#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket后端功能测试脚本
验证WebSocket集成和API功能是否正常工作
"""

import sys
import os
import time
import requests
import json
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_health_check():
    """测试健康检查接口"""
    print("🏥 测试健康检查接口...")
    
    try:
        response = requests.get('http://localhost:5000/api/v2/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过: {data.get('status', 'unknown')}")
            print(f"   数据库状态: {data.get('components', {}).get('database', 'unknown')}")
            print(f"   WebSocket状态: {data.get('components', {}).get('websocket', 'unknown')}")
            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {str(e)}")
        return False

def test_system_status():
    """测试系统状态接口"""
    print("\n💻 测试系统状态接口...")
    
    try:
        response = requests.get('http://localhost:5000/api/v2/status/system', timeout=5)
        if response.status_code == 200:
            data = response.json()
            system_info = data.get('system', {})
            print(f"✅ 系统状态获取成功")
            print(f"   CPU使用率: {system_info.get('cpu_percent', 0):.1f}%")
            print(f"   内存使用率: {system_info.get('memory', {}).get('percent', 0):.1f}%")
            print(f"   WebSocket连接数: {data.get('websocket', {}).get('active_clients', 0)}")
            return True
        else:
            print(f"❌ 系统状态获取失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 系统状态获取异常: {str(e)}")
        return False

def test_crawler_status():
    """测试爬虫状态接口"""
    print("\n🕷️ 测试爬虫状态接口...")
    
    try:
        response = requests.get('http://localhost:5000/api/v2/status/crawler', timeout=5)
        if response.status_code == 200:
            data = response.json()
            summary = data.get('summary', {})
            print(f"✅ 爬虫状态获取成功")
            print(f"   总爬虫数: {summary.get('total', 0)}")
            print(f"   运行中: {summary.get('running', 0)}")
            print(f"   已停止: {summary.get('stopped', 0)}")
            print(f"   错误: {summary.get('error', 0)}")
            return True
        else:
            print(f"❌ 爬虫状态获取失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 爬虫状态获取异常: {str(e)}")
        return False

def test_websocket_stats():
    """测试WebSocket统计接口"""
    print("\n📊 测试WebSocket统计接口...")
    
    try:
        response = requests.get('http://localhost:5000/api/v2/websocket/stats', timeout=5)
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats', {})
            print(f"✅ WebSocket统计获取成功")
            print(f"   活跃连接数: {stats.get('active_clients', 0)}")
            print(f"   房间数: {len(stats.get('rooms', {}))}")
            print(f"   消息历史: {stats.get('message_history_count', 0)}")
            return True
        else:
            print(f"❌ WebSocket统计获取失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ WebSocket统计获取异常: {str(e)}")
        return False

def test_websocket_connection():
    """测试WebSocket连接（简单测试）"""
    print("\n🔌 测试WebSocket连接...")
    
    try:
        # 这里我们只是测试WebSocket端点是否可访问
        # 实际的WebSocket连接测试需要专门的WebSocket客户端库
        import socket
        
        # 尝试连接到WebSocket端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 5000))
        sock.close()
        
        if result == 0:
            print("✅ WebSocket端口可访问")
            return True
        else:
            print("❌ WebSocket端口不可访问")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket连接测试异常: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 NewsLook WebSocket后端功能测试")
    print("=" * 50)
    
    # 等待服务器启动
    print("⏳ 等待服务器启动...")
    time.sleep(2)
    
    # 运行测试
    tests = [
        ("健康检查", test_health_check),
        ("系统状态", test_system_status),
        ("爬虫状态", test_crawler_status),
        ("WebSocket统计", test_websocket_stats),
        ("WebSocket连接", test_websocket_connection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试 {test_name} 发生异常: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！WebSocket后端功能正常")
        return 0
    else:
        print("⚠️  部分测试未通过，请检查服务器状态")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 