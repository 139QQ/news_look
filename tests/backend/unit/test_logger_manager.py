#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理器单元测试
测试统一日志系统的各种功能
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目路径 - 从tests/backend/unit/回到项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

def test_logger_manager_basic():
    """测试日志管理器基础功能"""
    print("=== 测试日志管理器基础功能 ===")
    
    try:
        from backend.newslook.core.logger_manager import get_logger_manager, get_logger
        
        # 创建临时日志目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 设置临时配置
            os.environ['NEWSLOOK_LOG_DIR'] = temp_dir
            
            # 获取日志管理器
            manager = get_logger_manager()
            print("✅ 日志管理器创建成功")
            
            # 测试获取不同类型的日志记录器
            app_logger = manager.get_app_logger()
            print("✅ 应用日志记录器获取成功")
            
            web_logger = manager.get_web_logger()
            print("✅ Web日志记录器获取成功")
            
            db_logger = manager.get_database_logger()
            print("✅ 数据库日志记录器获取成功")
            
            crawler_logger = manager.get_crawler_logger('sina')
            print("✅ 爬虫日志记录器获取成功")
            
            # 测试日志输出
            app_logger.info("测试应用日志")
            web_logger.debug("测试Web日志")
            db_logger.warning("测试数据库日志")
            crawler_logger.error("测试爬虫日志")
            print("✅ 日志输出测试完成")
            
            return True
            
    except Exception as e:
        print(f"❌ 日志管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_monitoring():
    """测试性能监控功能"""
    print("\n=== 测试性能监控功能 ===")
    
    try:
        import time
        from backend.newslook.core.performance import (
            monitor_performance, 
            performance_timer,
            monitor_database_operation
        )
        
        # 测试装饰器
        @monitor_performance("test_operation")
        def test_function():
            time.sleep(0.01)  # 模拟耗时操作
            return "success"
        
        result = test_function()
        print(f"✅ 性能监控装饰器测试完成: {result}")
        
        # 测试上下文管理器
        with performance_timer("test_context_operation"):
            time.sleep(0.01)  # 模拟耗时操作
        print("✅ 性能监控上下文管理器测试完成")
        
        # 测试数据库操作监控
        @monitor_database_operation("test_db_query")
        def test_db_operation():
            time.sleep(0.005)
            return "db_result"
        
        db_result = test_db_operation()
        print(f"✅ 数据库操作监控测试完成: {db_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能监控测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_structured_logging():
    """测试结构化日志功能"""
    print("\n=== 测试结构化日志功能 ===")
    
    try:
        from backend.newslook.core.logger_manager import get_logger_manager
        
        manager = get_logger_manager()
        logger = manager.get_logger('test', 'structured')
        
        # 测试带上下文的日志
        context_logger = manager.create_context_logger(
            logger, 
            user_id="12345",
            session_id="abc123",
            test_module="test"  # 避免与日志记录的module字段冲突
        )
        
        context_logger.info("测试结构化日志", extra={
            'action': 'test_log',
            'data': {'key': 'value'},
            'event_timestamp': '2024-06-07T17:30:00'  # 避免与内置timestamp冲突
        })
        
        print("✅ 结构化日志测试完成")
        
        # 测试性能指标记录
        manager.log_performance(
            "test_performance_log",
            0.123,
            category="test",
            status="success"
        )
        
        print("✅ 性能指标记录测试完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 结构化日志测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("NewsLook 日志系统单元测试")
    print("=" * 50)
    
    tests = [
        ("日志管理器基础功能", test_logger_manager_basic),
        ("性能监控功能", test_performance_monitoring),
        ("结构化日志功能", test_structured_logging)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🔄 开始测试: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
            status = "✅ 通过" if result else "❌ 失败"
            print(f"📊 {test_name}: {status}")
        except Exception as e:
            results[test_name] = False
            print(f"📊 {test_name}: ❌ 异常 - {e}")
    
    # 总结
    print("\n" + "=" * 50)
    print("测试结果总结:")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    print(f"\n总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有日志系统测试通过！")
    else:
        print("⚠️  部分测试失败，需要进一步检查")

if __name__ == '__main__':
    main() 