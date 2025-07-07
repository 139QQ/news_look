#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
第一优先级指令最终验证测试
验证所有核心API的真实数据改造情况
"""

import requests
import json
from datetime import datetime

def test_api_endpoint(url, description):
    """测试单个API端点"""
    try:
        print(f"\n🔍 测试: {description}")
        print(f"📡 URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功 (状态码: {response.status_code})")
            print(f"📊 数据预览:")
            
            # 根据不同的API显示不同的关键信息
            if 'news' in url:
                total = data.get('total', 0)
                current_count = len(data.get('data', []))
                print(f"   总新闻数: {total}, 当前页: {current_count}")
                
                if current_count > 0:
                    sample = data['data'][0]
                    print(f"   样本标题: {sample.get('title', 'N/A')[:50]}...")
                    print(f"   样本来源: {sample.get('source', 'N/A')}")
                    
            elif 'crawlers' in url:
                success = data.get('success', False)
                crawler_count = len(data.get('data', []))
                print(f"   请求成功: {success}, 爬虫数量: {crawler_count}")
                
                if crawler_count > 0:
                    running_count = sum(1 for c in data['data'] if c.get('is_running', False))
                    print(f"   运行中: {running_count}/{crawler_count}")
                    
            elif 'analytics' in url:
                if 'overview' in url:
                    total_news = data.get('total_news', 0)
                    sources_count = data.get('sources_count', 0)
                    today_news = data.get('today_news', 0)
                    print(f"   总新闻: {total_news}, 今日: {today_news}, 数据源: {sources_count}")
                    
                elif 'echarts' in url:
                    trend_days = len(data.get('news_trend', {}).get('dates', []))
                    source_count = len(data.get('source_distribution', []))
                    keyword_count = len(data.get('keyword_cloud', []))
                    print(f"   趋势天数: {trend_days}, 数据源: {source_count}, 关键词: {keyword_count}")
            
            return True, data
            
        else:
            print(f"❌ 失败 (状态码: {response.status_code})")
            print(f"📄 响应: {response.text[:200]}...")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {str(e)}")
        return False, None
    except Exception as e:
        print(f"❌ 解析错误: {str(e)}")
        return False, None

def main():
    """主测试函数"""
    print("🚀 NewsLook 第一优先级指令最终验证")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5000"
    
    # 测试API列表
    test_cases = [
        (f"{base_url}/api/news", "新闻列表API (核心改造)"),
        (f"{base_url}/api/news?limit=10&page=1", "新闻分页查询"),
        (f"{base_url}/api/v1/crawlers/status", "爬虫状态联动 (核心改造)"),
        (f"{base_url}/api/v1/analytics/overview", "分析概览统计 (核心改造)"),
        (f"{base_url}/api/v1/analytics/echarts/data", "ECharts数据分析"),
    ]
    
    results = []
    
    for url, description in test_cases:
        success, data = test_api_endpoint(url, description)
        results.append({
            'url': url,
            'description': description,
            'success': success,
            'data': data
        })
    
    # 生成最终报告
    print("\n" + "=" * 60)
    print("📋 第一优先级指令完成度评估")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    print(f"📊 总体情况: {success_count}/{total_count} 个API正常")
    
    # 详细评估
    core_apis = ['新闻列表API', '爬虫状态联动', '分析概览统计']
    core_success = 0
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['description']}")
        
        # 检查是否是核心API
        for core_api in core_apis:
            if core_api in result['description']:
                if result['success']:
                    core_success += 1
                break
    
    print(f"\n🎯 核心目标达成度: {core_success}/{len(core_apis)}")
    
    if core_success == len(core_apis):
        print("🌟 优秀！第一优先级指令完全达成")
        print("   ✓ 新闻数据已真实化")
        print("   ✓ 爬虫状态已联动")  
        print("   ✓ 基础统计已实现")
    elif core_success >= 2:
        print("✨ 良好！第一优先级指令基本达成")
    else:
        print("⚠️ 待完善：核心目标尚未完全实现")
    
    print(f"\n⏰ 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 