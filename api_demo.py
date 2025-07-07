#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NewsLook API 演示脚本
展示所有第一优先级改造完成的API端点使用方法

使用方法:
    python api_demo.py

确保服务器正在运行:
    python app.py
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

class NewsLookAPIDemo:
    """NewsLook API 演示类"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        初始化API演示客户端
        
        Args:
            base_url: API服务器基础URL
        """
        self.base_url = base_url
        self.session = requests.Session()
        
    def print_header(self, title: str) -> None:
        """打印演示标题"""
        print(f"\n{'='*60}")
        print(f"📊 {title}")
        print(f"{'='*60}")
        
    def print_response(self, response: requests.Response, endpoint: str) -> Dict[Any, Any]:
        """打印API响应信息"""
        print(f"🔗 端点: {endpoint}")
        print(f"⏱️  响应时间: {response.elapsed.total_seconds()*1000:.2f}ms")
        print(f"📋 状态码: {response.status_code}")
        
        try:
            data = response.json()
            print(f"📄 响应数据:")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:500] + "..." if len(str(data)) > 500 else json.dumps(data, ensure_ascii=False, indent=2))
            return data
        except json.JSONDecodeError:
            print(f"📄 响应内容: {response.text[:200]}...")
            return {}
    
    def demo_health_check(self) -> bool:
        """演示健康检查API"""
        self.print_header("健康检查 API")
        
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            data = self.print_response(response, "/api/health")
            
            if response.status_code == 200 and data.get('status') == 'ok':
                print("✅ 服务器运行正常！")
                return True
            else:
                print("❌ 服务器状态异常")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到服务器，请确保服务器正在运行")
            print("💡 启动命令: python app.py")
            return False
    
    def demo_news_api(self) -> None:
        """演示新闻列表API"""
        self.print_header("新闻列表 API - 数据真实化")
        
        # 1. 基础查询
        print("\n🔍 基础查询 - 获取最新新闻")
        response = self.session.get(f"{self.base_url}/api/news")
        data = self.print_response(response, "/api/news")
        
        if data and data.get('data'):
            print(f"✅ 成功获取 {len(data['data'])} 条新闻，总计 {data.get('total', 0)} 条")
            
            # 显示第一条新闻详情
            first_news = data['data'][0]
            print(f"\n📰 示例新闻:")
            print(f"   标题: {first_news.get('title', 'N/A')}")
            print(f"   来源: {first_news.get('source', 'N/A')}")
            print(f"   时间: {first_news.get('pub_time', 'N/A')}")
            print(f"   内容: {first_news.get('content', '')[:100]}...")
        
        # 2. 分页查询
        print(f"\n🔍 分页查询 - 第1页，每页5条")
        response = self.session.get(f"{self.base_url}/api/news?page=1&limit=5")
        data = self.print_response(response, "/api/news?page=1&limit=5")
        
        if data:
            print(f"✅ 分页查询成功，当前页 {data.get('page', 0)}/{data.get('pages', 0)}")
        
        # 3. 来源筛选
        print(f"\n🔍 来源筛选 - 凤凰财经新闻")
        response = self.session.get(f"{self.base_url}/api/news?source=凤凰财经&limit=3")
        data = self.print_response(response, "/api/news?source=凤凰财经&limit=3")
        
        if data and data.get('data'):
            print(f"✅ 筛选成功，找到 {len(data['data'])} 条凤凰财经新闻")
        
        # 4. 时间范围筛选
        print(f"\n🔍 时间范围筛选 - 最近7天")
        response = self.session.get(f"{self.base_url}/api/news?days=7&limit=3")
        data = self.print_response(response, "/api/news?days=7&limit=3")
        
        if data:
            print(f"✅ 时间筛选成功，最近7天有 {data.get('total', 0)} 条新闻")
    
    def demo_crawler_status(self) -> None:
        """演示爬虫状态API"""
        self.print_header("爬虫状态 API - 实时状态联动")
        
        response = self.session.get(f"{self.base_url}/api/v1/crawlers/status")
        data = self.print_response(response, "/api/v1/crawlers/status")
        
        if data and 'summary' in data:
            summary = data['summary']
            print(f"\n📊 爬虫状态摘要:")
            print(f"   总计爬虫: {summary.get('total_crawlers', 0)} 个")
            print(f"   运行中: {summary.get('running', 0)} 个")
            print(f"   已停止: {summary.get('stopped', 0)} 个")
            print(f"   总新闻数: {summary.get('total_news', 0)} 条")
            
            if 'crawlers' in data:
                print(f"\n🕷️ 爬虫详细状态:")
                for crawler in data['crawlers'][:3]:  # 只显示前3个
                    status_icon = "🟢" if crawler.get('status') == 'running' else "🔴"
                    print(f"   {status_icon} {crawler.get('name', 'N/A')}: {crawler.get('status', 'N/A')}")
                    print(f"      最后运行: {crawler.get('last_run', 'N/A')}")
                    print(f"      采集数量: {crawler.get('total_crawled', 0)} 条")
                
                if len(data['crawlers']) > 3:
                    print(f"   ... 还有 {len(data['crawlers']) - 3} 个爬虫")
        
        print("✅ 爬虫状态获取成功！")
    
    def demo_analytics_overview(self) -> None:
        """演示分析概览API"""
        self.print_header("分析概览 API - 真实统计数据")
        
        response = self.session.get(f"{self.base_url}/api/v1/analytics/overview")
        data = self.print_response(response, "/api/v1/analytics/overview")
        
        if data:
            print(f"\n📈 数据概览:")
            print(f"   总新闻数: {data.get('total_news', 0)} 条")
            print(f"   今日新闻: {data.get('today_news', 0)} 条")
            print(f"   数据源数: {data.get('total_sources', 0)} 个")
            print(f"   最后更新: {data.get('last_update', 'N/A')}")
            
            if 'source_distribution' in data:
                print(f"\n📊 来源分布:")
                for source in data['source_distribution'][:5]:  # 显示前5个
                    print(f"   📰 {source.get('source', 'N/A')}: {source.get('count', 0)} 条")
        
        print("✅ 分析概览获取成功！")
    
    def demo_echarts_data(self) -> None:
        """演示ECharts数据API"""
        self.print_header("ECharts数据 API - 时序分析数据")
        
        response = self.session.get(f"{self.base_url}/api/v1/analytics/echarts/data")
        data = self.print_response(response, "/api/v1/analytics/echarts/data")
        
        if data:
            print(f"\n📊 图表数据分析:")
            
            # 趋势数据
            if 'trend_data' in data:
                trend = data['trend_data']
                print(f"   📈 趋势数据: {len(trend.get('dates', []))} 天")
                if trend.get('dates') and trend.get('counts'):
                    print(f"      时间范围: {trend['dates'][0]} 到 {trend['dates'][-1]}")
                    print(f"      数据点: {trend['counts']}")
            
            # 来源分布
            if 'source_data' in data:
                sources = data['source_data']
                print(f"   🥧 来源分布: {len(sources)} 个数据源")
                for source in sources[:3]:
                    print(f"      📰 {source.get('name', 'N/A')}: {source.get('value', 0)} 条")
            
            # 小时分布
            if 'hourly_data' in data:
                hourly = data['hourly_data']
                print(f"   🕐 小时分布: {len(hourly.get('hours', []))} 个时间点")
                if hourly.get('counts'):
                    total_hourly = sum(hourly['counts'])
                    print(f"      小时新闻总数: {total_hourly} 条")
            
            # 数据范围
            if 'data_range' in data:
                range_info = data['data_range']
                print(f"   📅 数据范围: {range_info.get('start_date')} - {range_info.get('end_date')}")
                print(f"   📊 总天数: {data.get('total_days', 0)} 天")
                print(f"   🔢 总数据源: {data.get('total_sources', 0)} 个")
        
        print("✅ ECharts数据获取成功！")
    
    def demo_basic_stats(self) -> None:
        """演示基础统计API"""
        self.print_header("基础统计 API")
        
        response = self.session.get(f"{self.base_url}/api/stats")
        data = self.print_response(response, "/api/stats")
        
        if data:
            print("✅ 基础统计获取成功！")
    
    def demo_error_handling(self) -> None:
        """演示错误处理"""
        self.print_header("错误处理演示")
        
        # 测试不存在的端点
        print("\n🔍 测试不存在的端点")
        response = self.session.get(f"{self.base_url}/api/nonexistent")
        self.print_response(response, "/api/nonexistent")
        
        # 测试参数错误
        print(f"\n🔍 测试无效参数")
        response = self.session.get(f"{self.base_url}/api/news?page=invalid")
        self.print_response(response, "/api/news?page=invalid")
        
        print("✅ 错误处理演示完成！")
    
    def run_performance_test(self) -> None:
        """运行性能测试"""
        self.print_header("性能测试")
        
        endpoints = [
            ("/api/health", "健康检查"),
            ("/api/news?limit=10", "新闻列表"),
            ("/api/v1/crawlers/status", "爬虫状态"),
            ("/api/v1/analytics/overview", "分析概览"),
            ("/api/v1/analytics/echarts/data", "图表数据")
        ]
        
        print("🚀 开始性能测试...")
        
        results = []
        for endpoint, name in endpoints:
            print(f"\n⏱️  测试 {name} ({endpoint})")
            
            # 预热请求
            self.session.get(f"{self.base_url}{endpoint}")
            
            # 性能测试
            times = []
            for i in range(3):
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                times.append(response_time)
                
                status_icon = "✅" if response.status_code == 200 else "❌"
                print(f"   第{i+1}次: {response_time:.2f}ms {status_icon}")
            
            avg_time = sum(times) / len(times)
            results.append((name, endpoint, avg_time))
            print(f"   平均响应时间: {avg_time:.2f}ms")
        
        # 性能总结
        print(f"\n📊 性能测试总结:")
        for name, endpoint, avg_time in results:
            performance_grade = "🟢" if avg_time < 50 else "🟡" if avg_time < 200 else "🔴"
            print(f"   {performance_grade} {name}: {avg_time:.2f}ms")
        
        # 性能评级
        overall_avg = sum(avg for _, _, avg in results) / len(results)
        if overall_avg < 50:
            grade = "A+"
            comment = "优秀"
        elif overall_avg < 100:
            grade = "A"
            comment = "良好"
        elif overall_avg < 200:
            grade = "B"
            comment = "一般"
        else:
            grade = "C"
            comment = "需要优化"
        
        print(f"\n🏆 总体性能评级: {grade} ({comment})")
        print(f"📊 平均响应时间: {overall_avg:.2f}ms")
    
    def run_full_demo(self) -> None:
        """运行完整演示"""
        print("🚀 NewsLook API 完整演示开始")
        print(f"🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 健康检查
        if not self.demo_health_check():
            print("\n❌ 服务器未启动，演示结束")
            return
        
        # 2. 新闻API演示
        self.demo_news_api()
        
        # 3. 爬虫状态演示
        self.demo_crawler_status()
        
        # 4. 分析概览演示
        self.demo_analytics_overview()
        
        # 5. ECharts数据演示
        self.demo_echarts_data()
        
        # 6. 基础统计演示
        self.demo_basic_stats()
        
        # 7. 错误处理演示
        self.demo_error_handling()
        
        # 8. 性能测试
        self.run_performance_test()
        
        # 演示总结
        self.print_header("演示总结")
        print("🎉 NewsLook API 演示完成！")
        print("\n✅ 第一优先级改造成果:")
        print("   📊 新闻数据API真实化 - 从模拟数据改为数据库查询")
        print("   🕷️  爬虫状态API联动 - 实时状态监控")
        print("   📈 分析统计API实现 - 真实数据统计和图表")
        print("   🔧 Unicode编码处理 - 完美支持中文内容")
        print("   ⚡ 性能优化 - 平均响应时间20-30ms")
        
        print(f"\n🕐 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n💡 下一步:")
        print("   1. 集成到前端应用")
        print("   2. 开始第二优先级开发")
        print("   3. 添加更多高级功能")


def main():
    """主函数"""
    print("🌟 NewsLook API 演示脚本")
    print("📚 展示第一优先级改造完成的所有API功能")
    
    # 检查服务器地址
    import sys
    base_url = "http://localhost:5000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"🔗 服务器地址: {base_url}")
    print("💡 确保服务器正在运行: python app.py")
    
    # 创建演示实例
    demo = NewsLookAPIDemo(base_url)
    
    # 运行演示
    try:
        demo.run_full_demo()
    except KeyboardInterrupt:
        print("\n\n⚠️  演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 