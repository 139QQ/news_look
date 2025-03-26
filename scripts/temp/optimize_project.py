#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NewsLook项目优化脚本

该脚本用于执行所有项目优化操作，包括：
1. 修复日志记录重复输出问题
2. 优化项目目录结构
3. 整理Markdown文档
4. 清理冗余脚本
"""

import os
import sys
import logging
import importlib.util
import subprocess
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_python_script(script_path):
    """
    运行Python脚本
    
    Args:
        script_path: 脚本路径
    
    Returns:
        bool: 运行是否成功
    """
    try:
        logger.info(f"运行脚本: {script_path}")
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"脚本输出: \n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"脚本运行失败: {e}")
        logger.error(f"错误输出: \n{e.stderr}")
        return False

def import_and_run_module(module_path, function_name="main"):
    """
    导入并运行模块中的函数
    
    Args:
        module_path: 模块路径
        function_name: 要运行的函数名
    
    Returns:
        bool: 运行是否成功
    """
    try:
        logger.info(f"导入模块: {module_path}")
        
        # 构建模块名
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        
        # 导入模块
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 运行函数
        function = getattr(module, function_name)
        logger.info(f"运行函数: {function_name}")
        function()
        
        return True
    except Exception as e:
        logger.error(f"运行模块函数失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def optimize_project():
    """执行项目优化"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    logger.info(f"开始优化项目: {project_root}")
    
    # 脚本路径
    scripts = {
        "fix_logger": os.path.join(project_root, "scripts", "fix_logger.py"),
        "optimize_dir": os.path.join(project_root, "scripts", "optimize_project.py"),
        "organize_docs": os.path.join(project_root, "scripts", "organize_md_docs.py")
    }
    
    # 确保脚本目录存在
    scripts_dir = os.path.join(project_root, "scripts")
    if not os.path.exists(scripts_dir):
        logger.warning(f"脚本目录不存在: {scripts_dir}，将尝试创建")
        os.makedirs(scripts_dir, exist_ok=True)
    
    # 检查脚本是否存在
    for name, path in scripts.items():
        if not os.path.exists(path):
            logger.warning(f"脚本不存在: {path}")
    
    # 执行优化步骤
    steps = [
        {"name": "修复日志模块", "script": scripts["fix_logger"]},
        {"name": "优化目录结构", "script": scripts["optimize_dir"]},
        {"name": "整理文档", "script": scripts["organize_docs"]}
    ]
    
    for step in steps:
        logger.info(f"执行步骤: {step['name']}")
        if os.path.exists(step["script"]):
            if not run_python_script(step["script"]):
                logger.warning(f"步骤执行失败: {step['name']}")
        else:
            logger.warning(f"步骤跳过，脚本不存在: {step['script']}")
    
    logger.info("项目优化完成")

if __name__ == "__main__":
    optimize_project() 