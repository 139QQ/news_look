#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 数据谱系初始化脚本
设置数据库表结构和示例数据
"""

import sys
import os
import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.newslook.core.data_lineage_manager import DataLineageManager
from backend.newslook.core.lineage_tracker import get_lineage_tracker
from backend.newslook.core.config_manager import ConfigManager

class DataLineageSetup:
    """数据谱系初始化器"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.lineage_manager = DataLineageManager(self.config_manager)
        self.db_path = os.path.join(project_root, 'data/db/finance_news.db')
        
    def create_lineage_tables(self):
        """创建数据谱系相关表"""
        print("🔧 创建数据谱系表结构...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建数据血缘表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_lineage (
                    lineage_id TEXT PRIMARY KEY,
                    source_system TEXT NOT NULL,
                    source_table TEXT NOT NULL,
                    source_field TEXT,
                    target_system TEXT NOT NULL,
                    target_table TEXT NOT NULL,
                    target_field TEXT,
                    transformation_rule TEXT,
                    transformation_type TEXT,
                    created_by TEXT DEFAULT 'system',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
                ''')
                
                # 创建索引
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_lineage_source 
                ON data_lineage(source_system, source_table, source_field)
                ''')
                
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_lineage_target 
                ON data_lineage(target_system, target_table, target_field)
                ''')
                
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_lineage_type 
                ON data_lineage(transformation_type)
                ''')
                
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_lineage_created 
                ON data_lineage(created_at)
                ''')
                
                # 创建数据质量规则表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS quality_rules (
                    rule_id TEXT PRIMARY KEY,
                    rule_name TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    target_table TEXT NOT NULL,
                    target_field TEXT,
                    rule_config TEXT,
                    severity TEXT DEFAULT 'WARNING',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # 创建质量检查结果表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS quality_check_results (
                    check_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    batch_id TEXT,
                    total_records INTEGER,
                    passed_records INTEGER,
                    failed_records INTEGER,
                    pass_rate REAL,
                    check_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    error_details TEXT,
                    FOREIGN KEY (rule_id) REFERENCES quality_rules(rule_id)
                )
                ''')
                
                # 创建数据变更日志表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_change_logs (
                    change_id TEXT PRIMARY KEY,
                    table_name TEXT NOT NULL,
                    record_id TEXT,
                    operation TEXT NOT NULL,
                    old_values TEXT,
                    new_values TEXT,
                    changed_by TEXT DEFAULT 'system',
                    change_source TEXT,
                    changed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                conn.commit()
                print("✅ 数据谱系表结构创建完成")
                
        except Exception as e:
            print(f"❌ 创建表结构失败: {str(e)}")
            raise
    
    async def setup_sample_lineage_data(self):
        """设置示例血缘数据"""
        print("📊 创建示例数据血缘关系...")
        
        try:
            # 1. 爬虫数据源血缘
            crawler_mappings = [
                {
                    'source_name': '新浪财经',
                    'source_url': 'https://finance.sina.com.cn',
                    'field_mapping': {
                        'title': 'title',
                        'content': 'content',
                        'time': 'pub_time',
                        'link': 'url',
                        'author': 'author'
                    }
                },
                {
                    'source_name': '网易财经',
                    'source_url': 'https://money.163.com',
                    'field_mapping': {
                        'headline': 'title',
                        'body': 'content',
                        'publish_time': 'pub_time',
                        'source_url': 'url'
                    }
                },
                {
                    'source_name': '腾讯财经',
                    'source_url': 'https://finance.qq.com',
                    'field_mapping': {
                        'news_title': 'title',
                        'news_content': 'content',
                        'news_time': 'pub_time',
                        'news_url': 'url'
                    }
                }
            ]
            
            for mapping in crawler_mappings:
                await self.lineage_manager.record_crawler_lineage(
                    source_name=mapping['source_name'],
                    source_url=mapping['source_url'],
                    target_table='news_data',
                    field_mapping=mapping['field_mapping'],
                    crawler_type='web_crawler'
                )
            
            # 2. 数据转换血缘
            transformation_mappings = [
                {
                    'source_table': 'news_data',
                    'target_table': 'news_cleaned',
                    'transformation_type': '数据清洗',
                    'field_mappings': [
                        {'source_field': 'title', 'target_field': 'clean_title', 'transform_logic': '去除HTML标签和特殊字符'},
                        {'source_field': 'content', 'target_field': 'clean_content', 'transform_logic': '内容去重和格式化'},
                        {'source_field': 'pub_time', 'target_field': 'standard_time', 'transform_logic': '时间格式标准化'}
                    ]
                },
                {
                    'source_table': 'news_cleaned',
                    'target_table': 'news_analyzed',
                    'transformation_type': '智能分析',
                    'field_mappings': [
                        {'source_field': 'clean_content', 'target_field': 'sentiment_score', 'transform_logic': '情感分析算法'},
                        {'source_field': 'clean_content', 'target_field': 'keywords', 'transform_logic': 'NLP关键词提取'},
                        {'source_field': 'clean_content', 'target_field': 'related_stocks', 'transform_logic': '股票关联度分析'}
                    ]
                }
            ]
            
            for mapping in transformation_mappings:
                await self.lineage_manager.record_transformation_lineage(
                    source_table=mapping['source_table'],
                    target_table=mapping['target_table'],
                    transformation_type=mapping['transformation_type'],
                    transformation_rule=f"自动化{mapping['transformation_type']}流程",
                    field_mappings=mapping['field_mappings']
                )
            
            # 3. API访问血缘  
            api_access_examples = [
                {
                    'endpoint': '/api/news/list',
                    'source_table': 'news_analyzed',
                    'query_fields': ['title', 'sentiment_score', 'pub_time']
                },
                {
                    'endpoint': '/api/news/search',
                    'source_table': 'news_analyzed',
                    'query_fields': ['title', 'content', 'keywords']
                },
                {
                    'endpoint': '/api/stocks/news',
                    'source_table': 'news_analyzed',
                    'query_fields': ['related_stocks', 'sentiment_score', 'title']
                }
            ]
            
            for api_example in api_access_examples:
                await self.lineage_manager.record_api_access_lineage(
                    api_endpoint=api_example['endpoint'],
                    source_table=api_example['source_table'],
                    query_fields=api_example['query_fields'],
                    client_info={
                        'client_ip': '127.0.0.1',
                        'user_agent': 'NewsLook-Frontend/1.0',
                        'access_type': 'sample_data'
                    }
                )
            
            print("✅ 示例数据血缘关系创建完成")
            
        except Exception as e:
            print(f"❌ 创建示例血缘数据失败: {str(e)}")
            raise
    
    async def test_lineage_queries(self):
        """测试血缘查询功能"""
        print("🧪 测试数据谱系查询功能...")
        
        try:
            # 测试表血缘查询
            print("\n📋 测试表血缘查询:")
            lineage_data = await self.lineage_manager.get_lineage_by_table('news_data', 'both')
            print(f"  - news_data表有 {len(lineage_data.get('upstream', []))} 个上游数据源")
            print(f"  - news_data表有 {len(lineage_data.get('downstream', []))} 个下游处理")
            
            # 测试影响分析
            print("\n🎯 测试影响分析:")
            impact_data = await self.lineage_manager.analyze_impact('news_data', 'title', 3)
            print(f"  - title字段变更会影响 {impact_data.get('total_affected_count', 0)} 个对象")
            print(f"  - 涉及系统: {', '.join(impact_data.get('affected_systems', []))}")
            
            # 测试报告生成
            print("\n📊 测试报告生成:")
            report = await self.lineage_manager.generate_lineage_report()
            stats = report.get('statistics', {})
            print(f"  - 总血缘关系数: {stats.get('total_lineage_relations', 0)}")
            print(f"  - 涉及源表数: {stats.get('unique_source_tables', 0)}")
            print(f"  - 涉及目标表数: {stats.get('unique_target_tables', 0)}")
            
            print("✅ 数据谱系查询功能测试通过")
            
        except Exception as e:
            print(f"❌ 数据谱系查询测试失败: {str(e)}")
            raise
    
    def setup_quality_rules(self):
        """设置数据质量规则"""
        print("📐 设置数据质量规则...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                quality_rules = [
                    {
                        'rule_id': 'rule_news_title_not_null',
                        'rule_name': '新闻标题非空检查',
                        'rule_type': 'NOT_NULL',
                        'target_table': 'news_data',
                        'target_field': 'title',
                        'rule_config': '{"required": true}',
                        'severity': 'ERROR'
                    },
                    {
                        'rule_id': 'rule_news_url_unique',
                        'rule_name': '新闻URL唯一性检查',
                        'rule_type': 'UNIQUE',
                        'target_table': 'news_data',
                        'target_field': 'url',
                        'rule_config': '{"unique_key": "url"}',
                        'severity': 'ERROR'
                    },
                    {
                        'rule_id': 'rule_pub_time_range',
                        'rule_name': '发布时间范围检查',
                        'rule_type': 'RANGE',
                        'target_table': 'news_data',
                        'target_field': 'pub_time',
                        'rule_config': '{"min_date": "2020-01-01", "max_date": "2030-12-31"}',
                        'severity': 'WARNING'
                    },
                    {
                        'rule_id': 'rule_content_length',
                        'rule_name': '内容长度检查',
                        'rule_type': 'RANGE',
                        'target_table': 'news_data',
                        'target_field': 'content',
                        'rule_config': '{"min_length": 10, "max_length": 50000}',
                        'severity': 'WARNING'
                    }
                ]
                
                for rule in quality_rules:
                    cursor.execute('''
                    INSERT OR REPLACE INTO quality_rules (
                        rule_id, rule_name, rule_type, target_table, target_field,
                        rule_config, severity, is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                    ''', (
                        rule['rule_id'], rule['rule_name'], rule['rule_type'],
                        rule['target_table'], rule['target_field'], rule['rule_config'],
                        rule['severity'], datetime.now().isoformat()
                    ))
                
                conn.commit()
                print(f"✅ 已设置 {len(quality_rules)} 个数据质量规则")
                
        except Exception as e:
            print(f"❌ 设置质量规则失败: {str(e)}")
            raise
    
    def print_summary(self):
        """打印初始化总结"""
        print("\n" + "="*60)
        print("🎉 NewsLook 数据谱系初始化完成!")
        print("="*60)
        print("✅ 已完成的设置:")
        print("   📋 数据血缘表结构")
        print("   📊 示例血缘关系数据")
        print("   📐 数据质量规则")
        print("   🧪 功能测试验证")
        print("\n🚀 使用方法:")
        print("   1. 在爬虫中使用 @track_crawler() 装饰器")
        print("   2. 在API中使用 @track_api() 装饰器")
        print("   3. 访问 /api/lineage/* 查看血缘关系")
        print("   4. 使用 DataLineageManager 进行高级查询")
        print("\n📚 文档位置:")
        print("   - backend/newslook/core/data_lineage_manager.py")
        print("   - backend/newslook/core/lineage_tracker.py")
        print("   - backend/newslook/core/lineage_api.py")

async def main():
    """主函数"""
    print("🔧 NewsLook 数据谱系初始化开始...")
    
    setup = DataLineageSetup()
    
    try:
        # 1. 创建表结构
        setup.create_lineage_tables()
        
        # 2. 设置质量规则
        setup.setup_quality_rules()
        
        # 3. 创建示例血缘数据
        await setup.setup_sample_lineage_data()
        
        # 4. 测试功能
        await setup.test_lineage_queries()
        
        # 5. 打印总结
        setup.print_summary()
        
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 