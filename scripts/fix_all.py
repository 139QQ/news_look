#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
整合修复脚本

该脚本用于执行所有的修复任务，包括：
1. 修复日志重复问题
2. 修复模型与数据库字段不一致问题
3. 修复数据库结构问题
"""

import os
import sys
import logging
import subprocess
import importlib.util
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_script(script_path, script_name):
    """
    执行Python脚本
    
    Args:
        script_path: 脚本路径
        script_name: 脚本名称
    
    Returns:
        是否成功执行
    """
    if not os.path.exists(script_path):
        logger.error(f"脚本不存在: {script_path}")
        return False
    
    logger.info(f"开始执行脚本: {script_name}")
    
    try:
        # 使用subprocess执行脚本
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"脚本执行成功: {script_name}")
            logger.debug(f"脚本输出: {result.stdout}")
            return True
        else:
            logger.error(f"脚本执行失败: {script_name}, 错误码: {result.returncode}")
            logger.error(f"错误输出: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"脚本执行出错: {script_name}, 错误: {str(e)}")
        logger.error(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"执行脚本时发生异常: {script_name}, 异常: {str(e)}")
        return False

def import_and_run_function(module_path, function_name):
    """
    导入并执行模块中的函数
    
    Args:
        module_path: 模块路径
        function_name: 函数名
    
    Returns:
        函数返回值
    """
    if not os.path.exists(module_path):
        logger.error(f"模块不存在: {module_path}")
        return None
    
    try:
        # 导入模块
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 获取函数
        function = getattr(module, function_name, None)
        if function is None:
            logger.error(f"函数不存在: {function_name} in {module_path}")
            return None
        
        # 执行函数
        logger.info(f"执行函数: {function_name} from {module_name}")
        result = function()
        logger.info(f"函数执行完成: {function_name}")
        
        return result
    except Exception as e:
        logger.error(f"导入或执行函数时出错: {function_name}, 错误: {str(e)}")
        return None

def run_fix_tasks():
    """执行所有修复任务"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts_dir = os.path.join(project_root, "scripts")
    
    # 修复任务列表
    fix_tasks = [
        {"path": os.path.join(scripts_dir, "fix_logger.py"), "name": "修复日志重复问题"},
        {"path": os.path.join(scripts_dir, "fix_model.py"), "name": "修复模型与数据库字段不一致问题"},
        {"path": os.path.join(scripts_dir, "fix_database.py"), "name": "修复数据库结构问题"}
    ]
    
    # 执行修复任务
    all_success = True
    for task in fix_tasks:
        if not run_script(task["path"], task["name"]):
            logger.warning(f"任务失败: {task['name']}")
            all_success = False
        
        # 添加延时，避免同时修改文件导致的问题
        time.sleep(1)
    
    return all_success

def main():
    """主函数"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    logger.info("开始执行全部修复任务")
    
    # 执行修复任务
    if run_fix_tasks():
        logger.info("所有修复任务执行完成")
    else:
        logger.warning("部分修复任务执行失败")
    
    logger.info("系统修复完成，请检查日志确认修复结果")

if __name__ == "__main__":
    main() 