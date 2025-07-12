#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证README.md中描述的API是否正常工作
"""

import requests
import json
from typing import Dict, Any

def test_api_endpoint(url: str, description: str) -> bool:
    """测试单个API端点"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {description} - 状态: 正常")
            return True
        else:
            print(f"❌ {description} - 状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {description} - 连接失败 (服务器未启动?)")
        return False
    except Exception as e:
        print(f"❌ {description} - 错误: {e}")
        return False

def main():
    """主测试函数"""
    print("🌟 验证README.md中描述的API端点")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # README中描述的主要API端点
    apis = [
        ("/api/health", "健康检查API"),
        ("/api/news", "新闻列表API"),
        ("/api/v1/crawlers/status", "爬虫状态API"),
        ("/api/v1/analytics/overview", "分析概览API"),
        ("/api/v1/analytics/echarts/data", "图表数据API"),
        ("/api/news?limit=5", "新闻API分页测试"),
    ]
    
    success_count = 0
    total_count = len(apis)
    
    for endpoint, description in apis:
        url = f"{base_url}{endpoint}"
        if test_api_endpoint(url, description):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("🎉 所有API端点正常工作，README.md描述准确!")
        return True
    else:
        print("⚠️  部分API端点异常，请检查服务器状态")
        return False

if __name__ == "__main__":
    main() 