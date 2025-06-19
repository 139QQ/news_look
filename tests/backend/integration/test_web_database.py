#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Web应用数据库访问
验证Web应用能否正确访问所有数据库文件并获取数据
"""

import os
import sys
import requests
import json
from datetime import datetime

# 添加项目路径 - 从tests/backend/integration/回到项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))

def test_web_api_endpoints():
    """测试Web API端点"""
    print("=== 测试Web API端点 ===")
    
    base_url = "http://localhost:5000"
    
    # 测试API端点列表
    endpoints = [
        "/api/stats",
        "/api/sources", 
        "/api/news",
        "/api/data/validation-report"
    ]
    
    for endpoint in endpoints:
        try:
            url = base_url + endpoint
            print(f"\n测试 {endpoint}:")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  ✅ 状态码: {response.status_code}")
                    
                    # 分析不同端点的响应
                    if endpoint == "/api/stats":
                        print(f"  📊 统计数据:")
                        if 'total_news' in data:
                            print(f"     总新闻数: {data['total_news']}")
                        if 'today_news' in data:
                            print(f"     今日新闻: {data['today_news']}")
                        if 'active_sources' in data:
                            print(f"     活跃来源: {data['active_sources']}")
                        if 'crawl_success_rate' in data:
                            print(f"     成功率: {data['crawl_success_rate']:.2%}")
                            
                    elif endpoint == "/api/sources":
                        if isinstance(data, list):
                            print(f"  📋 找到 {len(data)} 个新闻来源: {data}")
                        else:
                            print(f"  📋 来源数据: {data}")
                            
                    elif endpoint == "/api/news":
                        if isinstance(data, list):
                            print(f"  📰 获取到 {len(data)} 条新闻")
                            if data:
                                print(f"     最新新闻: {data[0].get('title', 'N/A')[:50]}...")
                        elif isinstance(data, dict) and 'news' in data:
                            news_list = data['news']
                            print(f"  📰 获取到 {len(news_list)} 条新闻")
                            
                    elif endpoint == "/api/data/validation-report":
                        print(f"  🔍 数据验证报告:")
                        if 'total_news_count' in data:
                            print(f"     总新闻数: {data['total_news_count']}")
                        if 'database_files' in data:
                            print(f"     数据库文件数: {len(data['database_files'])}")
                        if 'sources_found' in data:
                            print(f"     发现来源: {data['sources_found']}")
                            
                except json.JSONDecodeError:
                    print(f"  ⚠️  响应不是有效的JSON格式")
                    print(f"     响应内容: {response.text[:200]}...")
                    
            else:
                print(f"  ❌ HTTP错误: {response.status_code}")
                print(f"     错误信息: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            print(f"  ❌ 连接失败: 无法连接到服务器 {base_url}")
            return False
        except requests.exceptions.Timeout:
            print(f"  ❌ 请求超时")
        except Exception as e:
            print(f"  ❌ 测试失败: {str(e)}")
    
    return True

def test_database_direct_access():
    """直接测试数据库访问"""
    print("\n=== 直接测试数据库访问 ===")
    
    try:
        from backend.newslook.utils.database import NewsDatabase
        
        # 测试使用所有数据库
        db = NewsDatabase(use_all_dbs=True)
        print(f"✅ 成功创建NewsDatabase实例")
        
        # 获取基本统计信息
        total_count = db.get_news_count()
        print(f"📊 总新闻数: {total_count}")
        
        sources = db.get_sources()
        print(f"📋 新闻来源 ({len(sources)}个): {sources}")
        
        # 测试每个来源的数据
        print(f"\n各来源详细统计:")
        for source in sources:
            count = db.get_news_count(source=source)
            print(f"  - {source}: {count} 条新闻")
            
        # 测试今日新闻
        today_count = db.get_news_count(days=1)
        print(f"📅 今日新闻数: {today_count}")
        
        # 测试最近新闻
        recent_news = db.query_news(limit=5)
        print(f"📰 最近 {len(recent_news)} 条新闻:")
        for i, news in enumerate(recent_news[:3]):
            print(f"  {i+1}. {news.get('title', 'N/A')[:50]}... (来源: {news.get('source', 'N/A')})")
            
        return True
        
    except Exception as e:
        print(f"❌ 直接数据库访问失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_web_server_status():
    """检查Web服务器状态"""
    print("=== 检查Web服务器状态 ===")
    
    try:
        response = requests.get("http://localhost:5000/", timeout=5)
        if response.status_code == 200:
            print("✅ Web服务器运行正常")
            return True
        else:
            print(f"⚠️  Web服务器响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Web服务器未运行或无法连接")
        print("请先启动Web服务器: python test_web_server.py")
        return False
    except Exception as e:
        print(f"❌ 检查Web服务器状态失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("NewsLook Web应用数据库访问测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 检查Web服务器状态
    web_running = check_web_server_status()
    
    # 直接测试数据库访问
    db_direct_ok = test_database_direct_access()
    
    # 如果Web服务器运行，测试API端点
    if web_running:
        api_ok = test_web_api_endpoints()
    else:
        api_ok = False
        
    print("\n" + "=" * 60)
    print("测试结果总结:")
    print(f"- 直接数据库访问: {'✅ 成功' if db_direct_ok else '❌ 失败'}")
    print(f"- Web服务器状态: {'✅ 运行中' if web_running else '❌ 未运行'}")
    print(f"- API端点测试: {'✅ 成功' if api_ok else '❌ 失败/跳过'}")
    
    if not web_running:
        print("\n💡 提示: 请先启动Web服务器再测试API功能")
        print("   启动命令: python test_web_server.py")

if __name__ == '__main__':
    main() 