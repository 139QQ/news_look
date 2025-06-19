#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻详情修复效果测试脚本
验证前端界面设计问题是否已解决
"""

import requests
import json
import sys
import time
from datetime import datetime


class NewsDetailTester:
    """新闻详情测试器"""
    
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        
    def test_api_health(self):
        """测试API健康状态"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API服务正常运行")
                return True
            else:
                print(f"❌ API服务状态异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API服务连接失败: {str(e)}")
            return False
    
    def get_news_list(self, limit=5):
        """获取新闻列表"""
        try:
            response = requests.get(f"{self.api_url}/news", 
                                  params={'per_page': limit}, 
                                  timeout=10)
            if response.status_code == 200:
                data = response.json()
                news_list = data.get('data', [])
                print(f"✅ 获取到 {len(news_list)} 条新闻")
                return news_list
            else:
                print(f"❌ 获取新闻列表失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ 获取新闻列表异常: {str(e)}")
            return []
    
    def test_news_detail(self, news_id):
        """测试单个新闻详情"""
        print(f"\n🔍 测试新闻详情 ID: {news_id}")
        
        try:
            response = requests.get(f"{self.api_url}/news/{news_id}", timeout=10)
            
            if response.status_code != 200:
                print(f"❌ HTTP状态码异常: {response.status_code}")
                return False
            
            data = response.json()
            
            # 检查响应结构
            if 'data' not in data:
                print("❌ 响应缺少'data'字段")
                return False
            
            news_data = data['data']
            
            # 检查核心字段
            result = self.check_news_data_completeness(news_data)
            
            # 检查数据质量诊断信息
            if '_debug' in news_data:
                debug_info = news_data['_debug']
                quality_score = debug_info.get('quality_score', 0)
                print(f"📊 数据质量分数: {quality_score:.2f}")
                
                if debug_info.get('missing_fields'):
                    print(f"⚠️  缺失字段: {debug_info['missing_fields']}")
                
                if debug_info.get('data_issues'):
                    print(f"❌ 数据问题: {debug_info['data_issues']}")
            
            return result
            
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def check_news_data_completeness(self, news_data):
        """检查新闻数据完整性"""
        required_fields = ['id', 'title', 'content', 'source']
        optional_fields = ['category', 'publish_time', 'url', 'keywords']
        
        missing_required = []
        missing_optional = []
        
        # 检查必要字段
        for field in required_fields:
            value = news_data.get(field)
            if not value or value == '':
                missing_required.append(field)
            else:
                print(f"✅ {field}: {str(value)[:50]}...")
        
        # 检查可选字段
        for field in optional_fields:
            value = news_data.get(field)
            if not value or value == '':
                missing_optional.append(field)
            else:
                print(f"✅ {field}: {str(value)[:50]}...")
        
        # 检查特殊字段
        self.check_keywords(news_data.get('keywords'))
        self.check_time_fields(news_data)
        
        # 总结检查结果
        if missing_required:
            print(f"❌ 缺少必要字段: {missing_required}")
            return False
        
        if missing_optional:
            print(f"⚠️  缺少可选字段: {missing_optional}")
        
        total_fields = len(required_fields) + len(optional_fields)
        present_fields = total_fields - len(missing_required) - len(missing_optional)
        completeness = present_fields / total_fields
        
        print(f"📊 数据完整度: {completeness:.2f} ({present_fields}/{total_fields})")
        
        return completeness >= 0.6  # 60%完整度为及格线
    
    def check_keywords(self, keywords):
        """检查关键词字段"""
        if not keywords:
            print("⚠️  关键词字段为空")
            return
        
        if isinstance(keywords, list):
            print(f"✅ 关键词: {len(keywords)}个 - {keywords[:3]}...")
        elif isinstance(keywords, str):
            print(f"⚠️  关键词为字符串格式: {keywords[:50]}...")
        else:
            print(f"❌ 关键词格式异常: {type(keywords)}")
    
    def check_time_fields(self, news_data):
        """检查时间字段"""
        time_fields = ['publish_time', 'crawl_time']
        
        for field in time_fields:
            value = news_data.get(field)
            if value:
                try:
                    # 尝试解析时间
                    if 'T' in value:
                        dt = datetime.fromisoformat(value.replace('Z', ''))
                        print(f"✅ {field}: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        print(f"✅ {field}: {value}")
                except Exception as e:
                    print(f"⚠️  {field}格式可能异常: {value}")
    
    def test_error_scenarios(self):
        """测试错误场景"""
        print("\n🧪 测试错误场景")
        
        # 测试不存在的新闻ID
        error_ids = ['999999', 'nonexistent', '', 'null']
        
        for news_id in error_ids:
            print(f"\n测试错误ID: '{news_id}'")
            try:
                response = requests.get(f"{self.api_url}/news/{news_id}", timeout=5)
                data = response.json()
                
                if response.status_code == 200 and data.get('data'):
                    news_data = data['data']
                    if 'diagnostic' in news_data.get('classification', ''):
                        print("✅ 返回了诊断信息")
                    else:
                        print("⚠️  返回了新闻数据，但可能不是预期的")
                else:
                    print(f"✅ 正确返回错误状态: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ 请求异常: {str(e)}")
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("🚀 开始新闻详情修复效果测试")
        print("=" * 50)
        
        # 1. 测试API健康状态
        if not self.test_api_health():
            print("❌ API服务不可用，测试终止")
            return False
        
        # 2. 获取新闻列表
        news_list = self.get_news_list()
        if not news_list:
            print("❌ 无法获取新闻列表，测试终止")
            return False
        
        # 3. 测试新闻详情
        success_count = 0
        total_count = min(3, len(news_list))  # 测试前3条新闻
        
        for i, news in enumerate(news_list[:total_count]):
            news_id = news.get('id')
            if news_id:
                if self.test_news_detail(news_id):
                    success_count += 1
                time.sleep(1)  # 避免请求过快
        
        # 4. 测试错误场景
        self.test_error_scenarios()
        
        # 5. 总结测试结果
        print("\n" + "=" * 50)
        print("📋 测试总结")
        print(f"✅ 成功测试: {success_count}/{total_count}")
        
        if success_count == total_count:
            print("🎉 所有测试通过！新闻详情修复成功")
            return True
        elif success_count > 0:
            print("⚠️  部分测试通过，仍有待改进")
            return False
        else:
            print("❌ 所有测试失败，需要进一步修复")
            return False


def main():
    """主函数"""
    print("NewsLook 新闻详情修复测试工具")
    print("作者: AI Assistant")
    print("时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print()
    
    # 创建测试器实例
    tester = NewsDetailTester()
    
    # 运行测试
    success = tester.run_comprehensive_test()
    
    # 退出程序
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 