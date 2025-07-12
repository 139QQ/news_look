#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
前端API调用诊断脚本
帮助调试数据概览页面的API问题
"""

import requests
import json
import time
from typing import Dict, Any

class FrontendAPIDebugger:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NewsLook-Debug/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def test_api_endpoint(self, endpoint: str, description: str) -> Dict[str, Any]:
        """测试单个API端点"""
        print(f"\n🔍 测试 {description}")
        print(f"📍 URL: {self.base_url}{endpoint}")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
            end_time = time.time()
            
            result = {
                'endpoint': endpoint,
                'description': description,
                'status_code': response.status_code,
                'response_time': round((end_time - start_time) * 1000, 2),
                'success': response.status_code == 200,
                'data': None,
                'error': None
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result['data'] = data
                    result['data_type'] = type(data).__name__
                    result['data_keys'] = list(data.keys()) if isinstance(data, dict) else None
                    
                    print(f"✅ 成功 (HTTP {response.status_code}) - {result['response_time']}ms")
                    print(f"📊 数据类型: {result['data_type']}")
                    if result['data_keys']:
                        print(f"🔑 数据字段: {result['data_keys']}")
                    
                    # 检查关键字段
                    if isinstance(data, dict):
                        key_fields = ['total_news', 'today_news', 'active_sources', 'sources_count']
                        available_fields = [field for field in key_fields if field in data]
                        if available_fields:
                            print(f"✨ 关键字段: {available_fields}")
                            for field in available_fields:
                                print(f"   {field}: {data[field]}")
                        
                        # 检查嵌套数据结构
                        if 'data' in data:
                            print(f"📦 嵌套数据结构: data -> {type(data['data']).__name__}")
                            if isinstance(data['data'], dict):
                                print(f"   嵌套字段: {list(data['data'].keys())}")
                
                except json.JSONDecodeError as e:
                    result['error'] = f"JSON解析失败: {str(e)}"
                    result['raw_response'] = response.text[:200]
                    print(f"❌ JSON解析失败: {str(e)}")
                    
            else:
                result['error'] = f"HTTP {response.status_code}: {response.reason}"
                print(f"❌ 失败 (HTTP {response.status_code}): {response.reason}")
                
        except requests.exceptions.RequestException as e:
            result = {
                'endpoint': endpoint,
                'description': description,
                'success': False,
                'error': f"网络错误: {str(e)}",
                'data': None
            }
            print(f"❌ 网络错误: {str(e)}")
            
        return result
    
    def run_comprehensive_test(self):
        """运行全面的API测试"""
        print("🚀 NewsLook 前端API诊断工具")
        print("=" * 50)
        
        # 测试的API端点
        endpoints = [
            ("/api/health", "健康检查"),
            ("/api/stats", "统计数据（Dashboard主要使用）"),
            ("/api/v1/analytics/overview", "分析概览（新版API）"),
            ("/api/sources", "数据源列表"),
            ("/api/stats/sources", "来源统计"),
            ("/api/news", "新闻列表"),
        ]
        
        results = []
        
        for endpoint, description in endpoints:
            result = self.test_api_endpoint(endpoint, description)
            results.append(result)
        
        # 生成报告
        print("\n" + "=" * 50)
        print("📋 诊断报告")
        print("=" * 50)
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        print(f"✅ 成功: {len(successful)}/{len(results)} 个API")
        print(f"❌ 失败: {len(failed)}/{len(results)} 个API")
        
        if failed:
            print("\n❌ 失败的API:")
            for result in failed:
                print(f"   {result['endpoint']}: {result['error']}")
        
        # 数据一致性检查
        print("\n🔍 数据一致性检查:")
        stats_data = None
        analytics_data = None
        
        for result in results:
            if result['endpoint'] == '/api/stats' and result['success']:
                stats_data = result['data']
            elif result['endpoint'] == '/api/v1/analytics/overview' and result['success']:
                analytics_data = result['data']
        
        if stats_data and analytics_data:
            print("   检查 /api/stats vs /api/v1/analytics/overview:")
            
            # 提取总新闻数
            stats_total = stats_data.get('total_news', 0)
            analytics_total = analytics_data.get('total_news', 0)
            
            if stats_total == analytics_total:
                print(f"   ✅ 总新闻数一致: {stats_total}")
            else:
                print(f"   ❌ 总新闻数不一致: stats={stats_total}, analytics={analytics_total}")
            
            # 检查今日新闻数
            stats_today = stats_data.get('today_news', 0)
            analytics_today = analytics_data.get('today_news', 0)
            
            if stats_today == analytics_today:
                print(f"   ✅ 今日新闻数一致: {stats_today}")
            else:
                print(f"   ❌ 今日新闻数不一致: stats={stats_today}, analytics={analytics_today}")
        
        print("\n🎯 前端数据格式建议:")
        if stats_data:
            print("   Dashboard.vue 应该使用以下字段映射:")
            print(f"   - total_news: {stats_data.get('total_news', 'N/A')}")
            print(f"   - today_news: {stats_data.get('today_news', 'N/A')}")
            print(f"   - active_sources: {stats_data.get('active_sources', 'N/A')}")
            print(f"   - crawl_success_rate: {stats_data.get('crawl_success_rate', 'N/A')}")
        
        return results

def main():
    debugger = FrontendAPIDebugger()
    debugger.run_comprehensive_test()

if __name__ == "__main__":
    main() 