#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
依赖版本锁定工具

此脚本会生成完整的依赖锁定文件(requirements.lock),
记录当前环境中所有包的确切版本，包括间接依赖。

用法：
python scripts/utils/freeze_requirements.py
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("freeze_requirements")

def run_command(command):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"命令执行失败: {e}")
        logger.error(f"错误输出: {e.stderr}")
        return None

def get_python_version():
    """获取Python版本"""
    return sys.version.split()[0]

def freeze_requirements():
    """冻结依赖版本"""
    logger.info("开始冻结依赖版本...")
    
    # 创建锁定文件路径
    lock_file = "requirements.lock"
    
    # 获取pip freeze输出
    output = run_command("pip freeze")
    if not output:
        logger.error("无法获取依赖列表")
        return False
    
    # 获取Python版本
    python_version = get_python_version()
    
    # 写入锁定文件
    try:
        with open(lock_file, 'w', encoding='utf-8') as f:
            f.write(f"# 依赖锁定文件 - 由freeze_requirements.py生成\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Python版本: {python_version}\n\n")
            f.write(output)
        
        logger.info(f"依赖锁定文件已生成: {lock_file}")
        return True
    except Exception as e:
        logger.error(f"生成锁定文件失败: {str(e)}")
        return False

def generate_separate_lock_files():
    """为每个环境生成独立的锁定文件"""
    
    # 确保requirements目录存在
    os.makedirs("requirements", exist_ok=True)
    
    # 锁定文件模板
    templates = {
        "base": "requirements/base.txt",
        "dev": "requirements/dev.txt",
        "prod": "requirements/prod.txt",
        "test": "requirements/test.txt"
    }
    
    # 为每个环境创建锁定文件
    for env, template_file in templates.items():
        if not os.path.exists(template_file):
            logger.warning(f"模板文件不存在，跳过: {template_file}")
            continue
        
        logger.info(f"处理环境: {env}")
        
        # 读取模板文件
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 创建临时环境并安装依赖
            venv_command = f"python -m venv .venv_{env} && " + \
                          (f".venv_{env}\\Scripts\\activate" if sys.platform == "win32" else f"source .venv_{env}/bin/activate") + \
                          f" && pip install -r {template_file} && pip freeze > requirements/{env}.lock && deactivate"
            
            if sys.platform != "win32":
                venv_command = f"python -m venv .venv_{env} && source .venv_{env}/bin/activate && pip install -r {template_file} && pip freeze > requirements/{env}.lock && deactivate"
            
            logger.info(f"执行命令: {venv_command}")
            result = run_command(venv_command)
            
            if os.path.exists(f"requirements/{env}.lock"):
                logger.info(f"已生成锁定文件: requirements/{env}.lock")
            else:
                logger.error(f"无法生成锁定文件: requirements/{env}.lock")
            
            # 清理临时环境
            if os.path.exists(f".venv_{env}"):
                import shutil
                shutil.rmtree(f".venv_{env}")
                logger.info(f"已清理临时环境: .venv_{env}")
            
        except Exception as e:
            logger.error(f"处理环境 {env} 时出错: {str(e)}")
    
    logger.info("所有环境的锁定文件生成完成")

def main():
    """主函数"""
    # 生成主锁定文件
    freeze_requirements()
    
    # 询问是否生成分环境锁定文件
    answer = input("是否为各环境生成独立的锁定文件? (y/n): ").lower()
    if answer == 'y':
        generate_separate_lock_files()
    
    logger.info("依赖锁定完成!")

if __name__ == "__main__":
    main() 