#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主修复脚本
按照Git协作流程执行所有修复操作
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path
import json

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# 导入修复脚本
from scripts.fix_database_architecture import DatabaseArchitectureFixer
from scripts.data_consistency_fixer import DataConsistencyFixer
from scripts.api_interface_improvements import APIInterfaceImprover
from scripts.performance_architecture_optimizer import PerformanceArchitectureOptimizer

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('master_fix.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MasterFixScript:
    """主修复脚本"""
    
    def __init__(self):
        """初始化主修复脚本"""
        self.project_root = project_root
        self.scripts_dir = current_dir
        
        # 修复报告
        self.report = {
            'start_time': datetime.now().isoformat(),
            'git_operations': [],
            'fix_results': {},
            'errors': [],
            'summary': {}
        }
        
        logger.info("主修复脚本初始化完成")
    
    def run_git_command(self, command: str, check: bool = True) -> subprocess.CompletedProcess:
        """执行Git命令"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=check
            )
            
            self.report['git_operations'].append({
                'command': command,
                'success': True,
                'output': result.stdout,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Git命令执行成功: {command}")
            return result
            
        except subprocess.CalledProcessError as e:
            self.report['git_operations'].append({
                'command': command,
                'success': False,
                'error': e.stderr,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.error(f"Git命令执行失败: {command} - {e.stderr}")
            if check:
                raise
            return e
    
    def check_git_status(self) -> bool:
        """检查Git状态"""
        try:
            result = self.run_git_command("git status --porcelain")
            
            if result.stdout.strip():
                logger.info("工作目录有未提交的更改")
                return False
            else:
                logger.info("工作目录是干净的")
                return True
                
        except Exception as e:
            logger.error(f"检查Git状态失败: {e}")
            return False
    
    def verify_branch(self, expected_branch: str) -> bool:
        """验证当前分支"""
        try:
            result = self.run_git_command("git branch --show-current")
            current_branch = result.stdout.strip()
            
            if current_branch == expected_branch:
                logger.info(f"当前分支正确: {current_branch}")
                return True
            else:
                logger.warning(f"当前分支: {current_branch}, 期望分支: {expected_branch}")
                return False
                
        except Exception as e:
            logger.error(f"验证分支失败: {e}")
            return False
    
    def run_database_architecture_fix(self) -> bool:
        """运行数据库架构修复"""
        logger.info("开始数据库架构修复...")
        
        try:
            fixer = DatabaseArchitectureFixer(str(self.project_root))
            report_file = fixer.run_full_fix()
            
            self.report['fix_results']['database_architecture'] = {
                'success': True,
                'report_file': str(report_file),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("数据库架构修复完成")
            return True
            
        except Exception as e:
            self.report['fix_results']['database_architecture'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.error(f"数据库架构修复失败: {e}")
            return False
    
    def run_data_consistency_fix(self) -> bool:
        """运行数据一致性修复"""
        logger.info("开始数据一致性修复...")
        
        try:
            fixer = DataConsistencyFixer(str(self.project_root))
            report_file = fixer.run_full_consistency_check()
            
            self.report['fix_results']['data_consistency'] = {
                'success': True,
                'report_file': str(report_file),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("数据一致性修复完成")
            return True
            
        except Exception as e:
            self.report['fix_results']['data_consistency'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.error(f"数据一致性修复失败: {e}")
            return False
    
    def run_api_improvements(self) -> bool:
        """运行API接口改进"""
        logger.info("开始API接口改进...")
        
        try:
            improver = APIInterfaceImprover(str(self.project_root))
            report_file = improver.run_full_improvements()
            
            self.report['fix_results']['api_improvements'] = {
                'success': True,
                'report_file': str(report_file),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("API接口改进完成")
            return True
            
        except Exception as e:
            self.report['fix_results']['api_improvements'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.error(f"API接口改进失败: {e}")
            return False
    
    def run_performance_optimization(self) -> bool:
        """运行性能架构优化"""
        logger.info("开始性能架构优化...")
        
        try:
            optimizer = PerformanceArchitectureOptimizer(str(self.project_root))
            report_file = optimizer.run_full_optimization()
            
            self.report['fix_results']['performance_optimization'] = {
                'success': True,
                'report_file': str(report_file),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("性能架构优化完成")
            return True
            
        except Exception as e:
            self.report['fix_results']['performance_optimization'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.error(f"性能架构优化失败: {e}")
            return False
    
    def commit_changes(self, message: str) -> bool:
        """提交更改"""
        try:
            # 添加所有更改
            self.run_git_command("git add .")
            
            # 提交更改
            self.run_git_command(f'git commit -m "{message}"')
            
            logger.info(f"提交完成: {message}")
            return True
            
        except Exception as e:
            logger.error(f"提交失败: {e}")
            return False
    
    def push_changes(self) -> bool:
        """推送更改"""
        try:
            # 获取当前分支
            result = self.run_git_command("git branch --show-current")
            current_branch = result.stdout.strip()
            
            # 推送到远程
            self.run_git_command(f"git push origin {current_branch}")
            
            logger.info(f"推送完成: {current_branch}")
            return True
            
        except Exception as e:
            logger.error(f"推送失败: {e}")
            return False
    
    def generate_final_report(self) -> Path:
        """生成最终报告"""
        self.report['end_time'] = datetime.now().isoformat()
        
        # 计算成功率
        total_fixes = len(self.report['fix_results'])
        successful_fixes = sum(1 for fix in self.report['fix_results'].values() if fix['success'])
        
        self.report['summary'] = {
            'total_fixes': total_fixes,
            'successful_fixes': successful_fixes,
            'success_rate': successful_fixes / total_fixes if total_fixes > 0 else 0,
            'total_git_operations': len(self.report['git_operations']),
            'successful_git_operations': sum(1 for op in self.report['git_operations'] if op['success'])
        }
        
        # 保存报告
        report_file = self.project_root / f"master_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"生成最终报告: {report_file}")
        return report_file
    
    def run_full_fix_process(self) -> Path:
        """运行完整的修复流程"""
        logger.info("开始完整的修复流程...")
        
        # 验证当前分支
        if not self.verify_branch("fix/database-architecture-consistency"):
            logger.error("当前分支不正确，请确保在修复分支上")
            return self.generate_final_report()
        
        # 运行修复步骤
        fix_steps = [
            {
                'name': '数据库架构修复',
                'function': self.run_database_architecture_fix,
                'commit_message': 'fix: 数据库架构统一化和路径修复\n\n- 统一数据库文件路径到data/db目录\n- 清理重复和冗余数据库文件\n- 实现数据库连接池管理\n- 添加数据库备份策略\n- 优化数据库性能配置'
            },
            {
                'name': '数据一致性修复',
                'function': self.run_data_consistency_fix,
                'commit_message': 'fix: 数据一致性和重复数据清理\n\n- 移除重复新闻数据\n- 修复数据格式不一致问题\n- 标准化数据源名称\n- 优化数据库索引结构\n- 添加数据完整性验证'
            },
            {
                'name': 'API接口改进',
                'function': self.run_api_improvements,
                'commit_message': 'feat: API接口标准化和版本管理\n\n- 实现RESTful API标准\n- 添加API版本管理(v2.0)\n- 集成真实数据源到API\n- 完善API错误处理和响应格式\n- 添加API文档和测试接口'
            },
            {
                'name': '性能架构优化',
                'function': self.run_performance_optimization,
                'commit_message': 'feat: 性能架构优化和监控系统\n\n- 实现WebSocket实时通信\n- 添加Redis缓存系统\n- 集成性能监控和指标收集\n- 完善错误处理和恢复机制\n- 优化系统资源使用'
            }
        ]
        
        # 逐步执行修复
        for step in fix_steps:
            logger.info(f"执行修复步骤: {step['name']}")
            
            success = step['function']()
            
            if success:
                # 提交更改
                if self.commit_changes(step['commit_message']):
                    logger.info(f"步骤 {step['name']} 完成并提交")
                else:
                    logger.error(f"步骤 {step['name']} 提交失败")
            else:
                logger.error(f"步骤 {step['name']} 执行失败")
        
        # 推送所有更改
        if self.push_changes():
            logger.info("所有更改推送成功")
        else:
            logger.error("推送失败")
        
        # 生成最终报告
        report_file = self.generate_final_report()
        
        # 打印摘要
        self.print_summary()
        
        return report_file
    
    def print_summary(self):
        """打印修复摘要"""
        print("\n" + "="*60)
        print("修复流程完成摘要")
        print("="*60)
        
        summary = self.report['summary']
        print(f"总修复项目: {summary['total_fixes']}")
        print(f"成功修复: {summary['successful_fixes']}")
        print(f"成功率: {summary['success_rate']:.1%}")
        
        print("\n详细结果:")
        for fix_name, result in self.report['fix_results'].items():
            status = "✅ 成功" if result['success'] else "❌ 失败"
            print(f"  {fix_name}: {status}")
            if not result['success']:
                print(f"    错误: {result['error']}")
        
        print(f"\nGit操作: {summary['successful_git_operations']}/{summary['total_git_operations']} 成功")
        
        if summary['success_rate'] >= 0.8:
            print("\n🎉 修复流程基本成功！")
        else:
            print("\n⚠️  修复流程部分失败，请检查错误信息")
        
        print("="*60)

def main():
    """主函数"""
    try:
        fixer = MasterFixScript()
        report_file = fixer.run_full_fix_process()
        
        print(f"\n最终报告文件: {report_file}")
        print("修复流程完成，请查看报告了解详细信息")
        
    except KeyboardInterrupt:
        print("\n修复流程被用户中断")
    except Exception as e:
        logger.error(f"修复流程发生未预期错误: {e}", exc_info=True)
        print(f"修复失败: {e}")

if __name__ == "__main__":
    main() 