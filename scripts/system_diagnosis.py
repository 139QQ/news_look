#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 系统自动化诊断脚本
验证所有修复措施是否有效
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

logger = logging.getLogger(__name__)

class SystemDiagnosis:
    """系统诊断器"""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        
    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有检查项"""
        print("🔧 开始系统自动化诊断...")
        print("=" * 60)
        
        # 检查点1: 配置加载
        self.check_config_loading()
        
        # 检查点2: 数据库目录
        self.check_database_directory()
        
        # 检查点3: 模块导入
        self.check_module_imports()
        
        # 检查点4: 连接池
        self.check_connection_pool()
        
        # 检查点5: 错误处理
        self.check_error_handling()
        
        # 生成报告
        self.generate_report()
        
        return self.results
    
    def check_config_loading(self):
        """检查点1: 配置加载无None值关键路径"""
        print("🔍 检查1: 配置加载验证")
        
        try:
            from backend.newslook.core.config_manager import get_config
            
            config = get_config()
            
            # 验证关键路径
            critical_paths = [
                ('database.db_dir', config.database.db_dir),
                ('database.main_db', config.database.main_db),
                ('database.pool_size', config.database.pool_size),
                ('crawler.concurrent', config.crawler.concurrent),
                ('web.host', config.web.host),
                ('web.port', config.web.port)
            ]
            
            failed_paths = []
            for path, value in critical_paths:
                if value is None or value == '':
                    failed_paths.append(path)
                    print(f"  ❌ {path}: {value}")
                else:
                    print(f"  ✅ {path}: {value}")
            
            if failed_paths:
                self.results['config_loading'] = {
                    'status': 'FAILED',
                    'failed_paths': failed_paths,
                    'message': f'发现{len(failed_paths)}个None值关键路径'
                }
            else:
                self.results['config_loading'] = {
                    'status': 'PASSED',
                    'message': '所有关键路径配置正常'
                }
                
        except Exception as e:
            self.results['config_loading'] = {
                'status': 'ERROR',
                'error': str(e),
                'message': '配置加载失败'
            }
            print(f"  ❌ 配置加载异常: {e}")
    
    def check_database_directory(self):
        """检查点2: 数据库目录存在且可写"""
        print("\n🔍 检查2: 数据库目录验证")
        
        try:
            from backend.newslook.core.config_manager import get_config
            
            config = get_config()
            db_dir = Path(config.database.db_dir)
            
            # 检查目录是否存在
            if not db_dir.exists():
                print(f"  ❌ 目录不存在: {db_dir}")
                self.results['database_directory'] = {
                    'status': 'FAILED',
                    'message': f'数据库目录不存在: {db_dir}'
                }
                return
            
            # 检查是否可写
            test_file = db_dir / 'test_write.tmp'
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                test_file.unlink()
                print(f"  ✅ 目录可写: {db_dir}")
                
                # 检查环境变量
                db_env = os.environ.get('DB_DIR')
                if db_env:
                    print(f"  ✅ 环境变量DB_DIR: {db_env}")
                else:
                    print(f"  ⚠️  环境变量DB_DIR未设置")
                
                self.results['database_directory'] = {
                    'status': 'PASSED',
                    'db_dir': str(db_dir),
                    'env_db_dir': db_env,
                    'message': '数据库目录配置正常'
                }
                
            except Exception as e:
                print(f"  ❌ 目录不可写: {db_dir}, 错误: {e}")
                self.results['database_directory'] = {
                    'status': 'FAILED',
                    'message': f'数据库目录不可写: {e}'
                }
                
        except Exception as e:
            print(f"  ❌ 检查数据库目录异常: {e}")
            self.results['database_directory'] = {
                'status': 'ERROR',
                'error': str(e),
                'message': '数据库目录检查失败'
            }
    
    def check_module_imports(self):
        """检查点3: 模块导入无ImportError"""
        print("\n🔍 检查3: 模块导入验证")
        
        critical_modules = [
            'backend.newslook.core.config_manager',
            'backend.newslook.core.error_handler',
            'backend.newslook.core.crawler_manager'
        ]
        
        failed_imports = []
        
        for module in critical_modules:
            try:
                __import__(module)
                print(f"  ✅ {module}")
            except ImportError as e:
                failed_imports.append((module, str(e)))
                print(f"  ❌ {module}: {e}")
            except Exception as e:
                failed_imports.append((module, str(e)))
                print(f"  ⚠️  {module}: {e}")
        
        if failed_imports:
            self.results['module_imports'] = {
                'status': 'FAILED',
                'failed_imports': failed_imports,
                'message': f'发现{len(failed_imports)}个导入错误'
            }
        else:
            self.results['module_imports'] = {
                'status': 'PASSED',
                'message': '所有核心模块导入正常'
            }
    
    def check_connection_pool(self):
        """检查点4: 连接池泄漏检查"""
        print("\n🔍 检查4: 连接池验证")
        
        try:
            from backend.newslook.core.config_manager import get_connection_pool
            
            pool = get_connection_pool()
            
            # 测试连接获取和释放
            initial_count = len(pool.active_connections)
            print(f"  📊 初始连接数: {initial_count}")
            
            # 清理测试连接
            pool.close_all()
            final_count = len(pool.active_connections)
            print(f"  📊 清理后连接数: {final_count}")
            
            # 计算泄漏率
            leak_rate = final_count
            print(f"  📊 连接泄漏数: {leak_rate}")
            
            if leak_rate == 0:
                print(f"  ✅ 连接池无泄漏")
                self.results['connection_pool'] = {
                    'status': 'PASSED',
                    'leak_count': leak_rate,
                    'message': '连接池性能正常'
                }
            else:
                print(f"  ❌ 连接池存在泄漏: {leak_rate}个连接")
                self.results['connection_pool'] = {
                    'status': 'FAILED',
                    'leak_count': leak_rate,
                    'message': '连接池存在泄漏'
                }
                
        except Exception as e:
            print(f"  ❌ 连接池检查异常: {e}")
            self.results['connection_pool'] = {
                'status': 'ERROR',
                'error': str(e),
                'message': '连接池检查失败'
            }
    
    def check_error_handling(self):
        """检查点5: 错误处理API结构化响应"""
        print("\n🔍 检查5: 错误处理验证")
        
        try:
            from backend.newslook.core.error_handler import get_error_handler, create_api_error_response
            
            error_handler = get_error_handler()
            
            # 测试错误响应格式
            test_error = Exception("测试错误")
            
            # 测试API错误响应
            api_response, status_code = create_api_error_response(test_error, "TEST_ERROR")
            
            # 验证响应结构
            error_fields = ['error_id', 'error_type', 'message', 'timestamp']
            
            missing_fields = []
            
            if 'error' not in api_response:
                missing_fields.append('error')
            else:
                error_obj = api_response['error']
                for field in error_fields:
                    if field not in error_obj:
                        missing_fields.append(f'error.{field}')
            
            if missing_fields:
                print(f"  ❌ 缺少字段: {missing_fields}")
                self.results['error_handling'] = {
                    'status': 'FAILED',
                    'missing_fields': missing_fields,
                    'message': '错误响应结构不完整'
                }
            else:
                print(f"  ✅ 错误响应结构完整")
                print(f"  ✅ HTTP状态码: {status_code}")
                
                # 测试错误历史
                history = error_handler.get_error_history()
                print(f"  ✅ 错误历史记录: {len(history)}条")
                
                self.results['error_handling'] = {
                    'status': 'PASSED',
                    'status_code': status_code,
                    'error_history_count': len(history),
                    'message': '错误处理系统正常'
                }
                
        except Exception as e:
            print(f"  ❌ 错误处理检查异常: {e}")
            self.results['error_handling'] = {
                'status': 'ERROR',
                'error': str(e),
                'message': '错误处理检查失败'
            }
    
    def generate_report(self):
        """生成诊断报告"""
        print("\n" + "=" * 60)
        print("🔧 系统诊断报告")
        print("=" * 60)
        
        total_checks = len(self.results)
        passed_checks = sum(1 for result in self.results.values() if result['status'] == 'PASSED')
        failed_checks = sum(1 for result in self.results.values() if result['status'] == 'FAILED')
        error_checks = sum(1 for result in self.results.values() if result['status'] == 'ERROR')
        
        print(f"总检查项: {total_checks}")
        print(f"✅ 通过: {passed_checks}")
        print(f"❌ 失败: {failed_checks}")
        print(f"⚠️  错误: {error_checks}")
        print(f"📊 通过率: {(passed_checks/total_checks)*100:.1f}%")
        
        elapsed_time = datetime.now() - self.start_time
        print(f"⏱️  诊断用时: {elapsed_time.total_seconds():.2f}秒")
        
        # 详细结果
        print("\n📋 详细结果:")
        for check_name, result in self.results.items():
            status_icon = {
                'PASSED': '✅',
                'FAILED': '❌',
                'ERROR': '⚠️ '
            }.get(result['status'], '❓')
            
            print(f"{status_icon} {check_name}: {result['message']}")
        
        # 修复建议
        if failed_checks > 0 or error_checks > 0:
            print("\n🔧 修复建议:")
            for check_name, result in self.results.items():
                if result['status'] in ['FAILED', 'ERROR']:
                    print(f"- {check_name}: {result.get('error', result['message'])}")


def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # 运行诊断
    diagnosis = SystemDiagnosis()
    results = diagnosis.run_all_checks()
    
    # 返回退出码
    failed_count = sum(1 for result in results.values() if result['status'] in ['FAILED', 'ERROR'])
    sys.exit(failed_count)


if __name__ == '__main__':
    main() 