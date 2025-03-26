#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能分析工具

此脚本用于分析项目代码的性能瓶颈，支持CPU分析、内存分析和执行时间分析。
可以生成分析报告，并提供性能优化建议。

用法：
python scripts/utils/performance_profiler.py [-h] [--mode {cpu,memory,time,all}] [--target TARGET]
                                            [--output OUTPUT] [--iterations ITERATIONS]
                                            [--include INCLUDE [INCLUDE ...]] [--exclude EXCLUDE [EXCLUDE ...]]
"""

import os
import sys
import time
import argparse
import logging
import importlib
import cProfile
import pstats
import io
import tracemalloc
import inspect
import functools
import glob
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("performance_profiler")

# 定义装饰器来测量函数执行时间
def timeit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"函数 {func.__name__} 执行时间: {elapsed_time:.4f} 秒")
        return result
    return wrapper

def format_bytes(size):
    """将字节格式化为人类可读的格式"""
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def check_dependencies():
    """检查分析工具依赖是否已安装"""
    dependencies = {
        "memory_profiler": "pip install memory_profiler",
        "psutil": "pip install psutil",
        "matplotlib": "pip install matplotlib",
        "snakeviz": "pip install snakeviz"
    }
    
    all_installed = True
    for dep, install_cmd in dependencies.items():
        try:
            importlib.import_module(dep)
            logger.info(f"✅ {dep} 已安装")
        except ImportError:
            logger.warning(f"❌ {dep} 未安装")
            answer = input(f"是否安装 {dep}? (y/n): ").lower()
            if answer == 'y':
                logger.info(f"正在安装 {dep}...")
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                logger.info(f"{dep} 安装完成")
            else:
                logger.info(f"跳过 {dep} 安装，某些功能可能不可用")
                all_installed = False
    
    return all_installed

def get_module_functions(module_path):
    """获取模块中的所有函数"""
    try:
        # 将文件路径转换为模块路径
        if module_path.endswith('.py'):
            module_path = module_path[:-3]
        module_path = module_path.replace(os.path.sep, '.')
        
        # 导入模块
        module = importlib.import_module(module_path)
        
        # 获取模块中的所有函数
        functions = {}
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and obj.__module__ == module.__name__:
                functions[name] = obj
        
        return functions
    except Exception as e:
        logger.error(f"获取模块 {module_path} 中的函数时出错: {str(e)}")
        return {}

@timeit
def profile_cpu(target, output, iterations=1):
    """CPU性能分析"""
    logger.info(f"开始CPU性能分析: {target}")
    
    # 使用cProfile进行性能分析
    profiler = cProfile.Profile()
    
    if os.path.isfile(target):
        # 分析单个文件
        functions = get_module_functions(target)
        for _ in range(iterations):
            for name, func in functions.items():
                logger.info(f"分析函数 {name}...")
                profiler.enable()
                try:
                    if inspect.signature(func).parameters:
                        logger.warning(f"跳过函数 {name}，因为它需要参数")
                        continue
                    func()
                except Exception as e:
                    logger.error(f"执行函数 {name} 时出错: {str(e)}")
                finally:
                    profiler.disable()
    else:
        # 分析整个模块
        logger.info(f"分析模块 {target}...")
        profiler.enable()
        try:
            # 简单执行import语句
            exec(f"import {target}")
        except Exception as e:
            logger.error(f"导入模块 {target} 时出错: {str(e)}")
        finally:
            profiler.disable()
    
    # 生成统计信息
    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream).sort_stats('cumulative')
    stats.print_stats(30)  # 打印前30个最重要的结果
    
    # 保存为文本文件
    stats_file = f"{output}_cpu_stats.txt"
    with open(stats_file, 'w') as f:
        f.write(stats_stream.getvalue())
    
    # 保存为二进制文件供其他工具使用
    profile_file = f"{output}_cpu_profile.prof"
    stats.dump_stats(profile_file)
    
    logger.info(f"CPU性能分析完成，结果保存在: {stats_file} 和 {profile_file}")
    return stats_file, profile_file

@timeit
def profile_memory(target, output):
    """内存使用分析"""
    logger.info(f"开始内存使用分析: {target}")
    
    # 启动内存跟踪
    tracemalloc.start()
    
    if os.path.isfile(target):
        # 分析单个文件
        functions = get_module_functions(target)
        for name, func in functions.items():
            logger.info(f"分析函数 {name} 的内存使用...")
            try:
                if inspect.signature(func).parameters:
                    logger.warning(f"跳过函数 {name}，因为它需要参数")
                    continue
                func()
            except Exception as e:
                logger.error(f"执行函数 {name} 时出错: {str(e)}")
    else:
        # 分析整个模块
        logger.info(f"分析模块 {target} 的内存使用...")
        try:
            # 简单执行import语句
            exec(f"import {target}")
        except Exception as e:
            logger.error(f"导入模块 {target} 时出错: {str(e)}")
    
    # 获取内存快照
    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()
    
    # 按大小排序
    top_stats = snapshot.statistics('lineno')
    
    # 保存为文本文件
    memory_file = f"{output}_memory_stats.txt"
    with open(memory_file, 'w') as f:
        f.write("内存使用统计信息 (按大小排序):\n")
        f.write("=" * 80 + "\n")
        for stat in top_stats[:30]:  # 仅显示前30个最重要的结果
            f.write(f"{stat}\n")
        
        # 添加总体统计信息
        total = sum(stat.size for stat in top_stats)
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"总内存使用: {format_bytes(total)}\n")
    
    logger.info(f"内存使用分析完成，结果保存在: {memory_file}")
    return memory_file, top_stats

@timeit
def profile_time(target, output, iterations=5):
    """执行时间分析"""
    logger.info(f"开始执行时间分析: {target}")
    
    # 用于存储执行时间
    execution_times = {}
    
    if os.path.isfile(target):
        # 分析单个文件
        functions = get_module_functions(target)
        
        for name, func in functions.items():
            if inspect.signature(func).parameters:
                logger.warning(f"跳过函数 {name}，因为它需要参数")
                continue
            
            logger.info(f"分析函数 {name} 的执行时间 ({iterations}次)...")
            times = []
            
            for i in range(iterations):
                try:
                    start_time = time.time()
                    func()
                    end_time = time.time()
                    elapsed = end_time - start_time
                    times.append(elapsed)
                    logger.debug(f"  迭代 {i+1}: {elapsed:.6f} 秒")
                except Exception as e:
                    logger.error(f"执行函数 {name} 时出错: {str(e)}")
                    break
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                execution_times[name] = {
                    'avg': avg_time,
                    'min': min_time,
                    'max': max_time,
                    'times': times
                }
    else:
        # 分析整个模块
        logger.info(f"分析模块 {target} 的导入时间 ({iterations}次)...")
        times = []
        
        for i in range(iterations):
            try:
                # 清除已导入的模块
                if target in sys.modules:
                    del sys.modules[target]
                
                start_time = time.time()
                exec(f"import {target}")
                end_time = time.time()
                elapsed = end_time - start_time
                times.append(elapsed)
                logger.debug(f"  迭代 {i+1}: {elapsed:.6f} 秒")
            except Exception as e:
                logger.error(f"导入模块 {target} 时出错: {str(e)}")
                break
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            execution_times[f"import {target}"] = {
                'avg': avg_time,
                'min': min_time,
                'max': max_time,
                'times': times
            }
    
    # 保存为文本文件
    time_file = f"{output}_time_stats.txt"
    with open(time_file, 'w') as f:
        f.write("执行时间统计信息:\n")
        f.write("=" * 80 + "\n\n")
        
        # 按平均时间排序
        sorted_times = sorted(execution_times.items(), key=lambda x: x[1]['avg'], reverse=True)
        
        for name, stats in sorted_times:
            f.write(f"函数: {name}\n")
            f.write(f"  平均执行时间: {stats['avg']:.6f} 秒\n")
            f.write(f"  最小执行时间: {stats['min']:.6f} 秒\n")
            f.write(f"  最大执行时间: {stats['max']:.6f} 秒\n")
            f.write(f"  执行次数: {len(stats['times'])}\n\n")
    
    logger.info(f"执行时间分析完成，结果保存在: {time_file}")
    return time_file, execution_times

def generate_visualizations(cpu_profile, output):
    """生成可视化图表"""
    try:
        import snakeviz
        import subprocess
        
        # 使用snakeviz生成HTML
        html_file = f"{output}_cpu_profile.html"
        subprocess.run([
            sys.executable, "-m", "snakeviz", 
            "--hostname", "localhost", 
            "--server", 
            "--output", html_file, 
            cpu_profile
        ], check=True)
        
        logger.info(f"CPU分析可视化已生成: {html_file}")
        return True
    except Exception as e:
        logger.error(f"生成可视化图表时出错: {str(e)}")
        return False

def find_python_files(directory, include_patterns=None, exclude_patterns=None):
    """查找目录中的Python文件"""
    if not os.path.exists(directory):
        logger.error(f"目录不存在: {directory}")
        return []
    
    # 默认包含所有.py文件
    if include_patterns is None:
        include_patterns = ["**/*.py"]
    
    # 收集匹配的文件
    matched_files = []
    for pattern in include_patterns:
        matched_files.extend(glob.glob(os.path.join(directory, pattern), recursive=True))
    
    # 过滤排除的文件
    if exclude_patterns:
        excluded_files = []
        for pattern in exclude_patterns:
            excluded_files.extend(glob.glob(os.path.join(directory, pattern), recursive=True))
        
        # 移除排除的文件
        matched_files = [f for f in matched_files if f not in excluded_files]
    
    # 确保所有文件都是.py文件
    return [f for f in matched_files if f.endswith('.py')]

def get_optimization_suggestions(cpu_stats_file, memory_stats, time_stats):
    """根据分析结果生成优化建议"""
    suggestions = []
    
    # 根据CPU性能分析生成建议
    try:
        with open(cpu_stats_file, 'r') as f:
            cpu_stats_content = f.read()
        
        # 检查是否有长时间运行的函数
        if "cumtime" in cpu_stats_content:
            suggestions.append("- 考虑优化累计时间较长的函数，它们占用了大量CPU时间。")
        
        # 检查是否有被频繁调用的函数
        if any(line for line in cpu_stats_content.splitlines() if "ncalls" in line and int(line.split()[0].split('/')[0]) > 1000):
            suggestions.append("- 某些函数被频繁调用，可以考虑使用缓存（如functools.lru_cache）来提高性能。")
    except Exception as e:
        logger.error(f"分析CPU统计数据时出错: {str(e)}")
    
    # 根据内存分析生成建议
    if memory_stats:
        large_memory_objects = [stat for stat in memory_stats if stat.size > 1024 * 1024]  # 大于1MB的对象
        if large_memory_objects:
            suggestions.append("- 发现大量内存使用。考虑使用生成器、迭代器或分批处理来减少内存占用。")
        
        if any("list" in str(stat.traceback) for stat in memory_stats[:10]):
            suggestions.append("- 列表操作占用大量内存，考虑使用生成器表达式代替列表推导式。")
        
        if any("dict" in str(stat.traceback) for stat in memory_stats[:10]):
            suggestions.append("- 字典操作占用大量内存，考虑使用更高效的数据结构如defaultdict或Counter。")
    
    # 根据时间分析生成建议
    if time_stats:
        slow_functions = [(name, stats) for name, stats in time_stats.items() if stats['avg'] > 0.1]
        if slow_functions:
            suggestions.append("- 以下函数执行较慢，需要优化:")
            for name, stats in slow_functions:
                suggestions.append(f"  * {name} (平均: {stats['avg']:.6f}s)")
    
    # 添加一般性能优化建议
    general_suggestions = [
        "- 考虑使用并行处理（multiprocessing或concurrent.futures）来提高性能。",
        "- 对频繁访问的数据使用缓存机制。",
        "- 使用适当的数据结构，如集合(set)用于成员检查，字典(dict)用于快速查找。",
        "- 避免在循环中创建对象，尽可能在循环外创建。",
        "- 使用列表推导式、生成器表达式和内置函数（如map、filter）提高性能。",
        "- 考虑使用numba或Cython加速计算密集型代码。"
    ]
    
    # 如果没有具体建议，添加一般建议
    if not suggestions:
        suggestions = general_suggestions
    else:
        suggestions.extend(general_suggestions)
    
    return suggestions

def generate_report(results, output_base, target, optimization_suggestions):
    """生成分析报告"""
    logger.info("生成性能分析报告...")
    
    report_file = f"{output_base}_performance_report.html"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        # HTML头部
        f.write("<!DOCTYPE html>\n")
        f.write("<html>\n<head>\n")
        f.write("    <meta charset='utf-8'>\n")
        f.write("    <title>性能分析报告</title>\n")
        f.write("    <style>\n")
        f.write("        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }\n")
        f.write("        h1 { color: #2c3e50; }\n")
        f.write("        h2 { color: #3498db; }\n")
        f.write("        .section { margin-bottom: 30px; }\n")
        f.write("        .summary { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }\n")
        f.write("        .success { color: #27ae60; }\n")
        f.write("        .warning { color: #f39c12; }\n")
        f.write("        .error { color: #e74c3c; }\n")
        f.write("        table { border-collapse: collapse; width: 100%; }\n")
        f.write("        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n")
        f.write("        th { background-color: #f2f2f2; }\n")
        f.write("        tr:nth-child(even) { background-color: #f9f9f9; }\n")
        f.write("    </style>\n")
        f.write("</head>\n<body>\n")
        
        # 报告标题
        f.write("    <h1>性能分析报告</h1>\n")
        f.write(f"    <p>分析目标: <code>{target}</code></p>\n")
        f.write(f"    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
        
        # 摘要部分
        f.write("    <div class='section summary'>\n")
        f.write("        <h2>分析摘要</h2>\n")
        f.write("        <table>\n")
        f.write("            <tr><th>分析类型</th><th>状态</th><th>结果文件</th></tr>\n")
        
        for analysis_type, (status, file_path) in results.items():
            status_class = "success" if status else "error"
            status_text = "成功" if status else "失败"
            file_name = os.path.basename(file_path) if file_path else "N/A"
            
            f.write(f"            <tr>\n")
            f.write(f"                <td>{analysis_type}</td>\n")
            f.write(f"                <td class='{status_class}'>{status_text}</td>\n")
            f.write(f"                <td>{file_name}</td>\n")
            f.write(f"            </tr>\n")
        
        f.write("        </table>\n")
        f.write("    </div>\n")
        
        # 优化建议部分
        f.write("    <div class='section'>\n")
        f.write("        <h2>优化建议</h2>\n")
        
        if optimization_suggestions:
            f.write("        <ul>\n")
            for suggestion in optimization_suggestions:
                f.write(f"            <li>{suggestion}</li>\n")
            f.write("        </ul>\n")
        else:
            f.write("        <p>未生成优化建议。</p>\n")
        
        f.write("    </div>\n")
        
        # 详细结果链接
        f.write("    <div class='section'>\n")
        f.write("        <h2>详细结果</h2>\n")
        f.write("        <p>请查看生成的结果文件获取详细信息：</p>\n")
        f.write("        <ul>\n")
        
        for analysis_type, (status, file_path) in results.items():
            if status and file_path:
                file_name = os.path.basename(file_path)
                f.write(f"            <li><a href='{file_name}'>{analysis_type}分析结果</a></li>\n")
        
        f.write("        </ul>\n")
        f.write("    </div>\n")
        
        # HTML尾部
        f.write("</body>\n</html>")
    
    logger.info(f"报告已生成: {report_file}")
    return report_file

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="性能分析工具")
    parser.add_argument("--mode", choices=["cpu", "memory", "time", "all"], default="all", 
                        help="分析模式: cpu(CPU分析), memory(内存分析), time(执行时间分析), all(全部)")
    parser.add_argument("--target", default="newslook", 
                        help="要分析的目标(文件或模块)")
    parser.add_argument("--output", default="performance", 
                        help="输出文件名前缀")
    parser.add_argument("--iterations", type=int, default=5, 
                        help="执行时间分析的迭代次数")
    parser.add_argument("--include", nargs="+", default=None, 
                        help="要包含的文件模式(如 '**/*.py')")
    parser.add_argument("--exclude", nargs="+", default=None, 
                        help="要排除的文件模式(如 '**/test_*.py')")
    
    args = parser.parse_args()
    
    logger.info("开始性能分析...")
    
    # 检查依赖
    check_dependencies()
    
    # 找到要分析的文件
    target_files = []
    if os.path.isdir(args.target):
        target_files = find_python_files(args.target, args.include, args.exclude)
        if not target_files:
            logger.error(f"未在目录 '{args.target}' 中找到匹配的Python文件")
            return
        logger.info(f"找到 {len(target_files)} 个要分析的Python文件")
    else:
        target_files = [args.target]
    
    results = {}
    cpu_stats_file = None
    memory_stats = None
    time_stats = None
    
    # 执行分析
    for target_file in target_files[:1]:  # 只分析第一个文件，作为示例
        output_base = f"{args.output}_{os.path.basename(target_file).replace('.py', '')}"
        
        if args.mode in ["cpu", "all"]:
            try:
                cpu_stats_file, cpu_profile = profile_cpu(target_file, output_base, args.iterations)
                results["CPU性能"] = (True, cpu_stats_file)
                
                # 生成可视化
                if generate_visualizations(cpu_profile, output_base):
                    results["CPU可视化"] = (True, f"{output_base}_cpu_profile.html")
                else:
                    results["CPU可视化"] = (False, None)
            except Exception as e:
                logger.error(f"CPU性能分析失败: {str(e)}")
                results["CPU性能"] = (False, None)
        
        if args.mode in ["memory", "all"]:
            try:
                memory_file, memory_stats = profile_memory(target_file, output_base)
                results["内存使用"] = (True, memory_file)
            except Exception as e:
                logger.error(f"内存使用分析失败: {str(e)}")
                results["内存使用"] = (False, None)
        
        if args.mode in ["time", "all"]:
            try:
                time_file, time_stats = profile_time(target_file, output_base, args.iterations)
                results["执行时间"] = (True, time_file)
            except Exception as e:
                logger.error(f"执行时间分析失败: {str(e)}")
                results["执行时间"] = (False, None)
    
    # 生成优化建议
    optimization_suggestions = get_optimization_suggestions(
        cpu_stats_file if "CPU性能" in results and results["CPU性能"][0] else None,
        memory_stats,
        time_stats
    )
    
    # 生成报告
    report_file = generate_report(results, args.output, args.target, optimization_suggestions)
    
    # 打印总结
    logger.info(f"性能分析完成，报告已生成: {report_file}")

if __name__ == "__main__":
    main() 