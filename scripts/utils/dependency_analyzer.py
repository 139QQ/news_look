#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
依赖分析工具

此脚本分析项目中的依赖关系，并生成依赖图。
可以分析模块间依赖、包依赖以及循环依赖。

用法：
python scripts/utils/dependency_analyzer.py [--output OUTPUT] [--format {png,svg,pdf}] [--mode {modules,packages,imports}]
"""

import os
import sys
import argparse
import logging
import importlib
import subprocess
from datetime import datetime
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dependency_analyzer")

def run_command(command, description=None):
    """执行命令并返回结果"""
    if description:
        logger.info(f"正在执行: {description}")
    
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"命令执行失败 ({result.returncode}): {command}")
            if result.stderr:
                logger.error(f"错误输出: {result.stderr}")
            return False, result.stdout
        return True, result.stdout
    except Exception as e:
        logger.error(f"执行命令时出错: {str(e)}")
        return False, str(e)

def check_dependencies():
    """检查分析工具依赖是否已安装"""
    dependencies = {
        "pydeps": "pip install pydeps",
        "graphviz": "pip install graphviz",
        "pipdeptree": "pip install pipdeptree"
    }
    
    all_installed = True
    for dep, install_cmd in dependencies.items():
        if dep in ["pydeps", "pipdeptree"]:
            # 检查Python包
            try:
                importlib.import_module(dep)
                logger.info(f"✅ {dep} 已安装")
            except ImportError:
                logger.warning(f"❌ {dep} 未安装")
                answer = input(f"是否安装 {dep}? (y/n): ").lower()
                if answer == 'y':
                    success, _ = run_command(install_cmd, f"安装 {dep}")
                    if not success:
                        all_installed = False
                else:
                    all_installed = False
        else:
            # 检查系统工具
            success, _ = run_command(f"{dep} -V", f"检查 {dep} 是否已安装")
            if not success:
                logger.warning(f"❌ {dep} 未安装")
                answer = input(f"是否安装 {dep}? (y/n): ").lower()
                if answer == 'y':
                    if sys.platform.startswith('win'):
                        logger.info(f"请通过以下网址下载并安装Graphviz: https://graphviz.org/download/")
                    elif sys.platform.startswith('darwin'):
                        run_command("brew install graphviz", "安装 graphviz")
                    else:
                        run_command("apt-get update && apt-get install -y graphviz", "安装 graphviz")
                else:
                    all_installed = False
    
    return all_installed

def analyze_module_dependencies(output, format):
    """分析模块级依赖"""
    logger.info("分析模块级依赖...")
    
    # 使用pydeps生成模块依赖图
    cmd = f"pydeps newslook --noshow --max-bacon=10 --cluster -o {output}_modules.{format}"
    success, output_text = run_command(cmd, "生成模块依赖图")
    
    if success:
        logger.info(f"✅ 模块依赖图已生成: {output}_modules.{format}")
        return True
    else:
        logger.error("❌ 模块依赖图生成失败")
        return False

def analyze_package_dependencies(output, format):
    """分析包级依赖"""
    logger.info("分析包级依赖...")
    
    # 使用pipdeptree生成依赖树并导出为DOT格式
    cmd = "pipdeptree --graph-output dot > dependencies.dot"
    success, _ = run_command(cmd, "导出依赖树为DOT格式")
    
    if not success:
        logger.error("❌ 包依赖图生成失败")
        return False
    
    # 使用graphviz将DOT文件转换为图像
    cmd = f"dot -T{format} dependencies.dot -o {output}_packages.{format}"
    success, _ = run_command(cmd, "生成包依赖图")
    
    if success:
        logger.info(f"✅ 包依赖图已生成: {output}_packages.{format}")
        # 清理临时文件
        try:
            os.remove("dependencies.dot")
        except:
            pass
        return True
    else:
        logger.error("❌ 包依赖图生成失败")
        return False

def analyze_imports(directory="newslook"):
    """分析导入关系"""
    logger.info(f"分析'{directory}'中的导入关系...")
    
    imports = defaultdict(set)
    file_count = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                module_name = os.path.relpath(file_path, os.path.dirname(directory))
                module_name = module_name.replace(os.path.sep, ".").replace(".py", "")
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # 分析导入语句
                    for line in content.split("\n"):
                        line = line.strip()
                        if line.startswith("import ") or line.startswith("from "):
                            # 忽略注释行
                            if "#" in line:
                                line = line[:line.index("#")]
                            
                            if line.startswith("import "):
                                imported = line[7:].strip()
                                # 处理多导入: import os, sys
                                for imp in imported.split(","):
                                    imp = imp.strip()
                                    if " as " in imp:
                                        imp = imp.split(" as ")[0].strip()
                                    imports[module_name].add(imp)
                            
                            elif line.startswith("from "):
                                if " import " in line:
                                    from_mod, import_what = line.split(" import ", 1)
                                    from_mod = from_mod[5:].strip()
                                    
                                    # 处理相对导入
                                    if from_mod.startswith("."):
                                        current_package = ".".join(module_name.split(".")[:-1])
                                        level = from_mod.count(".")
                                        if from_mod == "." * level:
                                            # 只有点，例如 from ... import x
                                            parent_levels = current_package.split(".")
                                            if len(parent_levels) >= level - 1:
                                                parent_package = ".".join(parent_levels[:-level+1]) if level > 1 else current_package
                                                imports[module_name].add(parent_package)
                                        else:
                                            # 带有模块名，例如 from ..utils import x
                                            parent_levels = current_package.split(".")
                                            if len(parent_levels) >= level:
                                                parent_package = ".".join(parent_levels[:-level])
                                                rel_module = from_mod[level:]
                                                if parent_package:
                                                    full_module = f"{parent_package}.{rel_module}"
                                                else:
                                                    full_module = rel_module
                                                imports[module_name].add(full_module)
                                    else:
                                        imports[module_name].add(from_mod)
                    
                    file_count += 1
                except Exception as e:
                    logger.error(f"分析文件 {file_path} 时出错: {str(e)}")
    
    # 过滤掉标准库和第三方库的导入
    project_prefix = directory.replace(os.path.sep, ".")
    filtered_imports = defaultdict(set)
    
    for module, deps in imports.items():
        for dep in deps:
            # 只保留项目内的导入关系
            if dep.startswith(project_prefix) or any(module_part == dep.split(".")[0] for module_part in project_prefix.split(".")):
                filtered_imports[module].add(dep)
    
    logger.info(f"已分析 {file_count} 个Python文件中的导入关系")
    return filtered_imports

def generate_import_graph(imports, output, format):
    """根据导入关系生成图形"""
    logger.info("生成导入关系图...")
    
    # 创建DOT文件
    dot_file = "imports.dot"
    with open(dot_file, "w", encoding="utf-8") as f:
        f.write("digraph imports {\n")
        f.write('  rankdir="LR";\n')
        f.write('  node [shape=box, style=filled, fillcolor=lightblue];\n')
        f.write('  edge [color=gray];\n\n')
        
        # 添加节点和边
        for module, deps in imports.items():
            module_short = module.split(".")[-1]
            f.write(f'  "{module}" [label="{module_short}"];\n')
            
            for dep in deps:
                dep_short = dep.split(".")[-1]
                f.write(f'  "{dep}" [label="{dep_short}"];\n')
                f.write(f'  "{module}" -> "{dep}";\n')
        
        f.write("}\n")
    
    # 使用graphviz将DOT文件转换为图像
    cmd = f"dot -T{format} {dot_file} -o {output}_imports.{format}"
    success, _ = run_command(cmd, "生成导入关系图")
    
    if success:
        logger.info(f"✅ 导入关系图已生成: {output}_imports.{format}")
        # 清理临时文件
        try:
            os.remove(dot_file)
        except:
            pass
        return True
    else:
        logger.error("❌ 导入关系图生成失败")
        return False

def detect_circular_dependencies(imports):
    """检测循环依赖"""
    logger.info("检测循环依赖...")
    
    cycles = []
    visited = set()
    stack = []
    in_stack = set()
    
    def dfs(node):
        nonlocal cycles, visited, stack, in_stack
        
        if node in in_stack:
            # 找到循环
            cycle_start = stack.index(node)
            cycles.append(stack[cycle_start:] + [node])
            return
        
        if node in visited:
            return
        
        visited.add(node)
        in_stack.add(node)
        stack.append(node)
        
        for neighbor in imports.get(node, []):
            dfs(neighbor)
        
        stack.pop()
        in_stack.remove(node)
    
    # 从每个节点开始DFS
    for node in imports:
        if node not in visited:
            dfs(node)
    
    # 打印循环依赖
    if cycles:
        logger.warning(f"发现 {len(cycles)} 个循环依赖:")
        for i, cycle in enumerate(cycles, 1):
            cycle_str = " -> ".join(cycle)
            logger.warning(f"循环依赖 #{i}: {cycle_str}")
    else:
        logger.info("✅ 未发现循环依赖")
    
    return cycles

def generate_report(results, output_base):
    """生成分析报告"""
    logger.info("生成依赖分析报告...")
    
    report_file = f"{output_base}_dependency_report.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(" " * 25 + "依赖分析报告\n")
        f.write(f" 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # 写入分析结果
        f.write("1. 分析结果\n")
        f.write("-" * 40 + "\n")
        for item, status in results.items():
            status_str = "✅ 成功" if status else "❌ 失败"
            f.write(f"{item}: {status_str}\n")
        f.write("\n")
        
        # 写入循环依赖信息
        if 'cycles' in results:
            cycles = results['cycles']
            f.write("2. 循环依赖\n")
            f.write("-" * 40 + "\n")
            
            if cycles:
                f.write(f"发现 {len(cycles)} 个循环依赖:\n\n")
                for i, cycle in enumerate(cycles, 1):
                    cycle_str = " -> ".join(cycle)
                    f.write(f"循环依赖 #{i}: {cycle_str}\n")
                
                f.write("\n循环依赖可能导致以下问题:\n")
                f.write("- 导入错误和不可预测的行为\n")
                f.write("- 增加代码复杂性和维护难度\n")
                f.write("- 影响应用程序启动时间\n")
                f.write("- 妨碍代码重用和模块化\n\n")
                
                f.write("建议:\n")
                f.write("- 重构代码以消除循环依赖\n")
                f.write("- 引入接口或中间层\n")
                f.write("- 使用依赖注入模式\n")
                f.write("- 将共享代码移至单独的模块\n")
            else:
                f.write("✅ 未发现循环依赖，代码结构良好。\n")
        f.write("\n")
        
        # 写入总结和建议
        f.write("3. 总结和建议\n")
        f.write("-" * 40 + "\n")
        
        success_count = sum(1 for status in results.values() if status is True)
        if 'cycles' in results:
            success_count -= 1  # 不将cycles计入成功计数
        
        if success_count == len(results) - ('cycles' in results):
            f.write("✅ 依赖分析完成，项目结构良好。\n\n")
            if not results.get('cycles'):
                f.write("项目没有循环依赖，这是一个良好的架构设计。继续保持良好的模块化和低耦合原则。\n")
            else:
                f.write("建议解决发现的循环依赖问题，以提高代码的可维护性和可扩展性。\n")
        else:
            f.write("⚠️ 依赖分析部分完成，某些分析未能成功执行。\n\n")
            f.write("请确保所有必要的依赖工具已正确安装，并检查日志以获取更多信息。\n")
        
        f.write("\n依赖图文件:\n")
        for item in ["模块依赖图", "包依赖图", "导入关系图"]:
            if item in results and results[item]:
                base = item.replace("依赖图", "").replace("关系图", "").strip()
                f.write(f"- {item}: {output_base}_{base.lower()}s.{results['format']}\n")
    
    logger.info(f"报告已生成: {report_file}")
    return report_file

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="项目依赖分析工具")
    parser.add_argument("--output", default="dependency", help="输出文件名前缀")
    parser.add_argument("--format", choices=["png", "svg", "pdf"], default="png", help="输出图形格式")
    parser.add_argument("--mode", choices=["all", "modules", "packages", "imports"], default="all", help="分析模式")
    
    args = parser.parse_args()
    
    logger.info("开始依赖分析...")
    
    # 检查依赖
    if not check_dependencies():
        logger.error("缺少必要的依赖工具，无法完成分析")
        return
    
    results = {
        "format": args.format
    }
    
    # 根据模式执行相应的分析
    if args.mode in ["all", "modules"]:
        results["模块依赖图"] = analyze_module_dependencies(args.output, args.format)
    
    if args.mode in ["all", "packages"]:
        results["包依赖图"] = analyze_package_dependencies(args.output, args.format)
    
    if args.mode in ["all", "imports"]:
        imports = analyze_imports()
        results["导入关系图"] = generate_import_graph(imports, args.output, args.format)
        
        # 检测循环依赖
        cycles = detect_circular_dependencies(imports)
        results["cycles"] = cycles
    
    # 生成报告
    report_file = generate_report(results, args.output)
    
    # 打印总结
    logger.info(f"依赖分析完成，报告已生成: {report_file}")

if __name__ == "__main__":
    main() 