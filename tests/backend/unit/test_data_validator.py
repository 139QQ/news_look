#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加项目路径 - 从tests/backend/unit/回到项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))

def test_data_validator():
    """测试DataValidator类"""
    print("=== 测试DataValidator ===")
    
    try:
        print("1. 导入DataValidator...")
        from backend.newslook.utils.data_validator import DataValidator
        print("✅ 导入成功")
        
        print("2. 创建DataValidator实例...")
        validator = DataValidator()
        print("✅ 实例创建成功")
        
        print("3. 检查发现的数据库...")
        print(f"   发现 {len(validator.db_paths)} 个数据库文件:")
        for db_path in validator.db_paths:
            size = os.path.getsize(db_path) / 1024
            print(f"   - {os.path.basename(db_path)} ({size:.1f} KB)")
        
        print("4. 测试数据库完整性验证...")
        integrity_result = validator.validate_database_integrity()
        print("✅ 数据库完整性验证成功")
        print(f"   有效数据库: {integrity_result['valid_databases']}/{integrity_result['total_databases']}")
        print(f"   总新闻数: {integrity_result['total_news_count']}")
        print(f"   去重新闻数: {integrity_result['unique_news_count']}")
        
        print("5. 测试获取一致统计...")
        stats = validator.get_consistent_statistics()
        print("✅ 一致统计获取成功")
        print(f"   统计数据键: {list(stats.keys())}")
        
        print("6. 测试生成报告...")
        report = validator.generate_report()
        print("✅ 报告生成成功")
        print(f"   报告长度: {len(report)} 字符")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        print("错误堆栈:")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_data_validator()
    print(f"\n测试结果: {'✅ 成功' if success else '❌ 失败'}") 