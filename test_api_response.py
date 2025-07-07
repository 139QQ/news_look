#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API响应测试脚本
用于检查v1 API端点的具体响应数据
"""

import requests
import json

def test_api_endpoint(url, endpoint_name):
    """测试API端点"""
    print(f"\n🔍 测试 {endpoint_name}")
    print(f"📡 请求: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"📊 状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📝 响应数据结构:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 错误响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def main():
    """主函数"""
    base_url = "http://127.0.0.1:5000"
    
    # 测试有问题的端点
    endpoints = [
        ("/api/v1/analytics/overview", "分析概览"),
        ("/api/v1/analytics/echarts/data", "ECharts数据"),
        ("/api/v1/crawlers/status", "爬虫状态")
    ]
    
    print("🔧 API响应数据结构测试")
    print("="*50)
    
    for endpoint, name in endpoints:
        test_api_endpoint(f"{base_url}{endpoint}", name)
    
    print("\n✅ 测试完成")

if __name__ == '__main__':
    main() 