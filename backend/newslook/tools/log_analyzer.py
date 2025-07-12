#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志分析工具
分析JSON格式的日志文件，生成性能报告和统计信息
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import argparse

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

try:
    from backend.newslook.core.config_manager import get_config
    from backend.newslook.core.logger_manager import get_logger
except ImportError:
    # 如果导入失败，使用默认设置
    get_config = None
    get_logger = None

class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_dir: str = None):
        """初始化日志分析器"""
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            try:
                config = get_config()
                self.log_dir = Path(config.logging.file_path)
            except:
                self.log_dir = Path("logs")
        
        self.performance_data = []
        self.error_data = []
        self.general_logs = []
    
    def load_logs(self, log_file: str = "newslook.json", hours: int = 24):
        """加载指定时间范围内的日志"""
        log_path = self.log_dir / log_file
        
        if not log_path.exists():
            print(f"⚠️  日志文件不存在: {log_path}")
            return
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        print(f"📖 正在分析日志文件: {log_path}")
        print(f"⏰ 分析时间范围: 最近 {hours} 小时")
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # 解析时间戳
                        timestamp_str = log_entry.get('timestamp', '')
                        try:
                            log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            # 移除时区信息进行比较
                            log_time = log_time.replace(tzinfo=None)
                        except:
                            continue  # 跳过无法解析时间的日志
                        
                        # 只分析指定时间范围内的日志
                        if log_time < cutoff_time:
                            continue
                        
                        # 分类日志
                        if 'operation' in log_entry and 'duration_ms' in log_entry:
                            self.performance_data.append(log_entry)
                        elif log_entry.get('level') in ['ERROR', 'CRITICAL']:
                            self.error_data.append(log_entry)
                        else:
                            self.general_logs.append(log_entry)
                            
                    except json.JSONDecodeError as e:
                        print(f"⚠️  第{line_num}行JSON解析失败: {e}")
                        continue
                        
        except Exception as e:
            print(f"❌ 读取日志文件失败: {e}")
            return
        
        print(f"✅ 日志加载完成:")
        print(f"   性能日志: {len(self.performance_data)} 条")
        print(f"   错误日志: {len(self.error_data)} 条") 
        print(f"   一般日志: {len(self.general_logs)} 条")
    
    def analyze_performance(self) -> Dict[str, Any]:
        """分析性能数据"""
        if not self.performance_data:
            return {"message": "没有性能数据"}
        
        # 按操作类型分组
        operations = defaultdict(list)
        categories = defaultdict(list)
        
        for entry in self.performance_data:
            op_name = entry.get('operation', 'unknown')
            duration = entry.get('duration_ms', 0)
            category = entry.get('category', 'general')
            
            operations[op_name].append(duration)
            categories[category].append(duration)
        
        # 计算统计信息
        def calc_stats(durations):
            if not durations:
                return {}
            return {
                'count': len(durations),
                'avg': round(sum(durations) / len(durations), 2),
                'min': round(min(durations), 2),
                'max': round(max(durations), 2),
                'total': round(sum(durations), 2)
            }
        
        # 分析结果
        result = {
            'total_operations': len(self.performance_data),
            'by_operation': {op: calc_stats(durs) for op, durs in operations.items()},
            'by_category': {cat: calc_stats(durs) for cat, durs in categories.items()},
            'slowest_operations': [],
            'fastest_operations': []
        }
        
        # 找出最慢和最快的操作
        all_ops = [(entry.get('operation', 'unknown'), entry.get('duration_ms', 0)) 
                  for entry in self.performance_data]
        
        all_ops.sort(key=lambda x: x[1], reverse=True)
        result['slowest_operations'] = all_ops[:10]
        result['fastest_operations'] = all_ops[-10:]
        
        return result
    
    def analyze_errors(self) -> Dict[str, Any]:
        """分析错误数据"""
        if not self.error_data:
            return {"message": "没有错误数据"}
        
        # 错误类型统计
        error_types = Counter()
        error_modules = Counter()
        error_messages = Counter()
        
        for entry in self.error_data:
            level = entry.get('level', 'UNKNOWN')
            module = entry.get('module', 'unknown')
            message = entry.get('message', 'unknown')
            
            error_types[level] += 1
            error_modules[module] += 1
            error_messages[message] += 1
        
        return {
            'total_errors': len(self.error_data),
            'by_level': dict(error_types),
            'by_module': dict(error_modules.most_common(10)),
            'common_messages': dict(error_messages.most_common(10))
        }
    
    def analyze_general_activity(self) -> Dict[str, Any]:
        """分析一般活动"""
        if not self.general_logs:
            return {"message": "没有一般日志数据"}
        
        # 日志级别统计
        levels = Counter()
        modules = Counter()
        hourly_activity = defaultdict(int)
        
        for entry in self.general_logs:
            level = entry.get('level', 'UNKNOWN')
            module = entry.get('module', 'unknown')
            timestamp_str = entry.get('timestamp', '')
            
            levels[level] += 1
            modules[module] += 1
            
            # 按小时统计活动
            try:
                log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                hour_key = log_time.strftime('%Y-%m-%d %H:00')
                hourly_activity[hour_key] += 1
            except:
                pass
        
        return {
            'total_logs': len(self.general_logs),
            'by_level': dict(levels),
            'by_module': dict(modules.most_common(10)),
            'hourly_activity': dict(hourly_activity)
        }
    
    def generate_report(self) -> str:
        """生成完整的分析报告"""
        report = []
        report.append("=" * 60)
        report.append("NewsLook 日志分析报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"日志目录: {self.log_dir}")
        report.append("")
        
        # 性能分析
        perf_analysis = self.analyze_performance()
        report.append("📊 性能分析")
        report.append("-" * 40)
        
        if 'message' in perf_analysis:
            report.append(f"   {perf_analysis['message']}")
        else:
            report.append(f"   总操作数: {perf_analysis['total_operations']}")
            
            # 按类别统计
            report.append("\n   📈 按类别统计:")
            for category, stats in perf_analysis['by_category'].items():
                report.append(f"     {category}: {stats['count']}次, 平均{stats['avg']}ms")
            
            # 最慢操作
            report.append("\n   🐌 最慢操作 (前5):")
            for i, (op, duration) in enumerate(perf_analysis['slowest_operations'][:5], 1):
                report.append(f"     {i}. {op}: {duration}ms")
        
        report.append("")
        
        # 错误分析
        error_analysis = self.analyze_errors()
        report.append("❌ 错误分析")
        report.append("-" * 40)
        
        if 'message' in error_analysis:
            report.append(f"   {error_analysis['message']}")
        else:
            report.append(f"   总错误数: {error_analysis['total_errors']}")
            
            report.append("\n   📊 按级别统计:")
            for level, count in error_analysis['by_level'].items():
                report.append(f"     {level}: {count}")
            
            report.append("\n   📍 按模块统计 (前5):")
            for module, count in list(error_analysis['by_module'].items())[:5]:
                report.append(f"     {module}: {count}")
        
        report.append("")
        
        # 活动分析
        activity_analysis = self.analyze_general_activity()
        report.append("📋 活动分析")
        report.append("-" * 40)
        
        if 'message' in activity_analysis:
            report.append(f"   {activity_analysis['message']}")
        else:
            report.append(f"   总日志数: {activity_analysis['total_logs']}")
            
            report.append("\n   📊 按级别统计:")
            for level, count in activity_analysis['by_level'].items():
                report.append(f"     {level}: {count}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def save_report(self, filename: str = None):
        """保存分析报告到文件"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"log_analysis_report_{timestamp}.txt"
        
        report_path = self.log_dir / filename
        report_content = self.generate_report()
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"✅ 分析报告已保存到: {report_path}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='NewsLook 日志分析工具')
    parser.add_argument('--log-dir', help='日志目录路径')
    parser.add_argument('--log-file', default='newslook.json', help='日志文件名')
    parser.add_argument('--hours', type=int, default=24, help='分析最近N小时的日志')
    parser.add_argument('--save', action='store_true', help='保存报告到文件')
    parser.add_argument('--output', help='输出文件名')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = LogAnalyzer(args.log_dir)
    
    # 加载日志
    analyzer.load_logs(args.log_file, args.hours)
    
    # 生成并显示报告
    report = analyzer.generate_report()
    print(report)
    
    # 保存报告（如果指定）
    if args.save:
        analyzer.save_report(args.output)

if __name__ == '__main__':
    main() 