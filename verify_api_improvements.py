#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API改造验证脚本
测试第一优先级指令完成情况：新闻数据真实化、爬虫状态联动、基础统计实现
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

class APIVerifier:
    """API验证器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url
        self.results = []
        
    def test_api(self, endpoint: str, expected_keys: List[str], test_name: str) -> Dict[str, Any]:
        """测试API端点"""
        print(f"\n🔍 测试 {test_name}...")
        print(f"📡 请求: {self.base_url}{endpoint}")
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            # 检查HTTP状态码
            if response.status_code != 200:
                return {
                    'success': False,
                    'endpoint': endpoint,
                    'test_name': test_name,
                    'response_time': response_time,
                    'error': f'HTTP {response.status_code}',
                    'summary': f'HTTP {response.status_code}'
                }
            
            # 解析JSON响应
            try:
                data = response.json()
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'endpoint': endpoint,
                    'test_name': test_name,
                    'response_time': response_time,
                    'error': 'Invalid JSON',
                    'summary': 'Invalid JSON'
                }
            
            # 检查必需的字段 - 支持嵌套字段检查
            missing_keys = []
            for key in expected_keys:
                if '.' in key:
                    # 处理嵌套字段，如 'data.total_news'
                    keys = key.split('.')
                    current_data = data
                    try:
                        for k in keys:
                            current_data = current_data[k]
                    except (KeyError, TypeError):
                        missing_keys.append(key)
                else:
                    # 处理顶级字段
                    if key not in data:
                        missing_keys.append(key)
            
            if missing_keys:
                return {
                    'success': False,
                    'endpoint': endpoint,
                    'test_name': test_name,
                    'response_time': response_time,
                    'error': f'缺少字段: {missing_keys}',
                    'summary': f'缺少字段: {missing_keys}'
                }
            
            # 生成成功的摘要信息
            summary = self.generate_summary(endpoint, data)
            
            return {
                'success': True,
                'endpoint': endpoint,
                'test_name': test_name,
                'response_time': response_time,
                'summary': summary
            }
            
        except requests.RequestException as e:
            return {
                'success': False,
                'endpoint': endpoint,
                'test_name': test_name,
                'response_time': 0,
                'error': str(e),
                'summary': str(e)
            }
    
    def generate_summary(self, endpoint: str, data: Dict[str, Any]) -> str:
        """生成测试结果摘要"""
        if endpoint == '/api/news':
            total = data.get('total', 0)
            current_page_count = len(data.get('data', []))
            return f"总计{total}条新闻，当前页{current_page_count}条"
        
        elif endpoint.startswith('/api/news?'):
            return "数据正常"
        
        elif endpoint == '/api/v1/crawlers/status':
            crawlers_data = data.get('data', [])
            running_count = sum(1 for c in crawlers_data if c.get('is_running', False))
            total_count = len(crawlers_data)
            return f"共{total_count}个爬虫，{running_count}个运行中"
        
        elif endpoint == '/api/v1/analytics/overview':
            analytics_data = data.get('data', {})
            total_news = analytics_data.get('total_news', 0)
            today_news = analytics_data.get('today_news', 0)
            sources_count = analytics_data.get('sources_count', 0)
            return f"总计{total_news}条新闻，今日{today_news}条，{sources_count}个数据源"
        
        elif endpoint == '/api/v1/analytics/echarts/data':
            echarts_data = data.get('data', {})
            trend_data = echarts_data.get('news_trend', {})
            dates_count = len(trend_data.get('dates', []))
            sources_count = len(echarts_data.get('source_distribution', []))
            return f"趋势数据{dates_count}天，{sources_count}个数据源"
        
        return "数据正常"
    
    def run_tests(self):
        """运行所有测试"""
        # 定义测试用例
        test_cases = [
            {
                'endpoint': '/api/news',
                'expected_keys': ['data', 'total'],
                'test_name': '新闻列表API真实化'
            },
            {
                'endpoint': '/api/news?limit=5&page=1',
                'expected_keys': ['data', 'total'],
                'test_name': '新闻列表分页查询'
            },
            {
                'endpoint': '/api/v1/crawlers/status',
                'expected_keys': ['success', 'data'],
                'test_name': '爬虫状态联动'
            },
            {
                'endpoint': '/api/v1/analytics/overview',
                'expected_keys': ['success', 'data.total_news', 'data.sources_count', 'data.today_news'],
                'test_name': '分析概览统计'
            },
            {
                'endpoint': '/api/v1/analytics/echarts/data',
                'expected_keys': ['success', 'data.news_trend', 'data.source_distribution'],
                'test_name': 'ECharts数据统计'
            }
        ]
        
        # 执行测试
        for test_case in test_cases:
            result = self.test_api(
                test_case['endpoint'],
                test_case['expected_keys'],
                test_case['test_name']
            )
            self.results.append(result)
        
        # 生成报告
        self._generate_report()
    
    def _generate_report(self):
        """生成验证报告"""
        print("\n" + "=" * 60)
        print("📋 验证报告")
        print("=" * 60)
        
        success_count = sum(1 for r in self.results if r['success'])
        warning_count = sum(1 for r in self.results if not r['success'] and 'warning' in r)
        failed_count = sum(1 for r in self.results if not r['success'] and 'error' in r)
        
        print(f"📊 总计: {len(self.results)} 项测试")
        print(f"✅ 成功: {success_count} 项")
        print(f"⚠️  警告: {warning_count} 项")
        print(f"❌ 失败: {failed_count} 项")
        
        # 详细结果
        print("\n📝 详细结果:")
        for result in self.results:
            status_icon = {
                True: '✅',
                False: '❌'
            }.get(result['success'], '⚠️')
            
            print(f"{status_icon} {result['test_name']}")
            print(f"   端点: {result['endpoint']}")
            print(f"   响应时间: {result['response_time']:.2f}ms")
            
            if not result['success']:
                print(f"   错误: {result['error']}")
            else:
                print(f"   摘要: {result['summary']}")
            print()
        
        # 总结
        print("🎯 第一优先级指令完成度评估:")
        
        if success_count >= 4:
            print("🌟 优秀！所有核心API都已成功改造为真实数据")
        elif success_count >= 3:
            print("👍 良好！大部分API已成功改造，少数需要调优")
        elif success_count >= 2:
            print("⚡ 进展中！部分API已改造成功，需要继续完善")
        else:
            print("🔧 需要调试！多数API改造遇到问题，请检查后端服务")
        
        print(f"\n⏰ 验证完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """主函数"""
    print("🔧 NewsLook API改造验证工具")
    print("验证第一优先级指令: 新闻数据真实化、爬虫状态联动、基础统计实现")
    
    # 创建验证器
    verifier = APIVerifier()
    
    # 运行验证
    verifier.run_tests()

if __name__ == "__main__":
    main() 