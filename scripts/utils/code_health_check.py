#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
代码健康检查工具

此脚本会扫描项目代码并运行各种代码质量检查，
包括代码风格检查(flake8)、静态类型检查(mypy)、
重复代码检查(pylint)等。

用法：
python scripts/utils/code_health_check.py [--fix]
"""

import os
import sys
import subprocess
import argparse
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("code_health_check")

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

def check_tool_installed(tool_name, install_cmd=None):
    """检查工具是否已安装，若未安装则提示安装"""
    success, _ = run_command(f"{tool_name} --version", f"检查{tool_name}是否已安装")
    if not success:
        logger.warning(f"{tool_name} 未安装")
        if install_cmd:
            answer = input(f"是否安装 {tool_name}? (y/n): ").lower()
            if answer == 'y':
                success, output = run_command(install_cmd, f"安装 {tool_name}")
                if success:
                    logger.info(f"{tool_name} 安装成功")
                    return True
                else:
                    logger.error(f"{tool_name} 安装失败")
                    return False
            else:
                logger.info(f"跳过 {tool_name} 检查")
                return False
        return False
    return True

def run_flake8(fix=False):
    """运行flake8代码风格检查"""
    if not check_tool_installed("flake8", "pip install flake8"):
        return False, "flake8未安装"
    
    targets = ["newslook", "scripts", "tests"]
    cmd = f"flake8 {' '.join(targets)}"
    
    success, output = run_command(cmd, "运行flake8代码风格检查")
    
    if fix and not success:
        logger.info("尝试自动修复代码风格问题...")
        if check_tool_installed("autopep8", "pip install autopep8"):
            fix_cmd = f"autopep8 --in-place --aggressive --aggressive {' '.join(targets)}"
            fix_success, fix_output = run_command(fix_cmd, "使用autopep8修复代码风格")
            if fix_success:
                logger.info("代码风格问题已修复")
                # 重新运行检查
                success, output = run_command(cmd, "重新运行flake8检查")
    
    return success, output

def run_mypy():
    """运行mypy静态类型检查"""
    if not check_tool_installed("mypy", "pip install mypy"):
        return False, "mypy未安装"
    
    cmd = "mypy newslook"
    return run_command(cmd, "运行mypy静态类型检查")

def run_pylint():
    """运行pylint代码分析"""
    if not check_tool_installed("pylint", "pip install pylint"):
        return False, "pylint未安装"
    
    cmd = "pylint newslook --disable=C0111,C0103"
    return run_command(cmd, "运行pylint代码分析")

def run_bandit():
    """运行bandit安全漏洞扫描"""
    if not check_tool_installed("bandit", "pip install bandit"):
        return False, "bandit未安装"
    
    cmd = "bandit -r newslook -ll"
    return run_command(cmd, "运行bandit安全漏洞扫描")

def run_pytest():
    """运行pytest单元测试"""
    if not check_tool_installed("pytest", "pip install pytest pytest-cov"):
        return False, "pytest未安装"
    
    cmd = "pytest -xvs tests"
    return run_command(cmd, "运行pytest单元测试")

def run_black(fix=False):
    """运行black代码格式化"""
    if not check_tool_installed("black", "pip install black"):
        return False, "black未安装"
    
    targets = ["newslook", "scripts", "tests"]
    check_cmd = f"black --check {' '.join(targets)}"
    
    if fix:
        cmd = f"black {' '.join(targets)}"
        success, output = run_command(cmd, "使用black格式化代码")
        return success, output
    else:
        return run_command(check_cmd, "检查代码格式是否符合black标准")

def check_circular_imports():
    """检查循环导入"""
    if not check_tool_installed("pycycle", "pip install pycycle"):
        return False, "pycycle未安装"
    
    cmd = "pycycle newslook"
    return run_command(cmd, "检查循环导入")

def find_fixme_todos():
    """查找TODO和FIXME标记"""
    logger.info("查找TODO和FIXME标记...")
    
    patterns = ["TODO", "FIXME", "XXX", "HACK"]
    targets = ["newslook", "scripts", "tests"]
    
    found = False
    for pattern in patterns:
        for target in targets:
            if os.path.exists(target):
                cmd = f"grep -r '{pattern}' --include='*.py' {target} || true"
                success, output = run_command(cmd)
                if output.strip():
                    if not found:
                        logger.info(f"发现{pattern}标记:")
                        found = True
                    print(output)
    
    if not found:
        logger.info("未发现待办标记")
        return True, ""
    return True, "发现待办标记，请查看输出"

def check_import_style():
    """检查导入风格"""
    logger.info("检查导入风格...")
    
    # 检查是否使用import *
    cmd = "grep -r 'import \\*' --include='*.py' newslook scripts tests || true"
    success, output = run_command(cmd)
    
    if output.strip():
        logger.warning("发现使用了'import *'，这可能导致命名空间污染:")
        print(output)
        return False, "存在'import *'导入，建议改为明确导入"
    
    # 检查相对导入是否正确
    cmd = "grep -r 'from \\.' --include='*.py' newslook scripts tests || true"
    success, output = run_command(cmd)
    
    if output.strip():
        logger.info("发现相对导入:")
        print(output)
    
    return True, "导入风格检查完成"

def generate_report(results):
    """生成检查报告"""
    logger.info("生成代码健康检查报告...")
    
    report_file = f"code_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(" " * 25 + "代码健康检查报告\n")
        f.write(f" 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # 计算总体健康得分
        total_checks = len(results)
        passed_checks = sum(1 for result in results if result['success'])
        health_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        f.write(f"代码健康得分: {health_score:.1f}% ({passed_checks}/{total_checks}通过)\n\n")
        
        # 写入各项检查结果
        for result in results:
            status = "通过" if result['success'] else "失败"
            f.write(f"[{status}] {result['name']}\n")
            if not result['success'] and result['output']:
                f.write("-" * 40 + "\n")
                f.write(result['output'][:500] + ("\n..." if len(result['output']) > 500 else ""))
                f.write("\n" + "-" * 40 + "\n")
            f.write("\n")
        
        # 写入总结和建议
        f.write("\n总结和建议:\n")
        if health_score >= 90:
            f.write("✅ 代码质量良好，继续保持!\n")
        elif health_score >= 70:
            f.write("⚠️ 代码质量一般，建议解决失败的检查项。\n")
        else:
            f.write("❌ 代码质量需要提升，请优先解决失败的检查项。\n")
        
        # 列出失败项
        failed_checks = [result['name'] for result in results if not result['success']]
        if failed_checks:
            f.write("\n需要优先解决的问题:\n")
            for i, check in enumerate(failed_checks, 1):
                f.write(f"{i}. {check}\n")
    
    logger.info(f"报告已生成: {report_file}")
    return report_file

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="代码健康检查工具")
    parser.add_argument("--fix", action="store_true", help="尝试自动修复发现的问题")
    args = parser.parse_args()
    
    logger.info("开始代码健康检查...")
    
    results = []
    
    # 运行各种检查
    checks = [
        {"func": run_flake8, "name": "Flake8代码风格检查", "args": {"fix": args.fix}},
        {"func": run_black, "name": "Black代码格式检查", "args": {"fix": args.fix}},
        {"func": run_mypy, "name": "MyPy静态类型检查", "args": {}},
        {"func": run_pylint, "name": "Pylint代码分析", "args": {}},
        {"func": run_bandit, "name": "Bandit安全漏洞扫描", "args": {}},
        {"func": run_pytest, "name": "PyTest单元测试", "args": {}},
        {"func": check_circular_imports, "name": "循环导入检查", "args": {}},
        {"func": find_fixme_todos, "name": "TODO标记检查", "args": {}},
        {"func": check_import_style, "name": "导入风格检查", "args": {}}
    ]
    
    for check in checks:
        try:
            success, output = check["func"](**check["args"])
            results.append({
                "name": check["name"],
                "success": success,
                "output": output
            })
            if success:
                logger.info(f"✅ {check['name']} 通过")
            else:
                logger.warning(f"❌ {check['name']} 失败")
        except Exception as e:
            logger.error(f"运行 {check['name']} 时出错: {str(e)}")
            results.append({
                "name": check["name"],
                "success": False,
                "output": str(e)
            })
    
    # 生成报告
    report_file = generate_report(results)
    
    # 打印总结
    total_checks = len(results)
    passed_checks = sum(1 for result in results if result['success'])
    logger.info(f"代码健康检查完成: {passed_checks}/{total_checks} 通过")
    logger.info(f"详细报告: {report_file}")

if __name__ == "__main__":
    main() 