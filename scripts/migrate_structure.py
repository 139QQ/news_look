#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
目录结构迁移工具

该脚本用于将原有目录结构迁移到新的标准化结构

用法：
python scripts/migrate_structure.py [--dry-run]
"""

import os
import sys
import shutil
import argparse
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("migrate_structure")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="目录结构迁移工具")
    parser.add_argument("--dry-run", action="store_true", help="仅显示将执行的操作，不实际执行")
    return parser.parse_args()

def ensure_dir(path, dry_run=False):
    """确保目录存在"""
    if dry_run:
        logger.info(f"[DRY RUN] 将创建目录: {path}")
        return
    
    os.makedirs(path, exist_ok=True)
    logger.info(f"创建目录: {path}")

def copy_file(src, dst, dry_run=False):
    """复制文件"""
    if not os.path.exists(src):
        logger.warning(f"源文件不存在: {src}")
        return False
    
    if dry_run:
        logger.info(f"[DRY RUN] 将复制: {src} -> {dst}")
        return True
    
    # 确保目标目录存在
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    
    try:
        shutil.copy2(src, dst)
        logger.info(f"复制文件: {src} -> {dst}")
        return True
    except Exception as e:
        logger.error(f"复制文件失败 {src} -> {dst}: {str(e)}")
        return False

def move_file(src, dst, dry_run=False):
    """移动文件"""
    if not os.path.exists(src):
        logger.warning(f"源文件不存在: {src}")
        return False
    
    if dry_run:
        logger.info(f"[DRY RUN] 将移动: {src} -> {dst}")
        return True
    
    # 确保目标目录存在
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    
    try:
        shutil.move(src, dst)
        logger.info(f"移动文件: {src} -> {dst}")
        return True
    except Exception as e:
        logger.error(f"移动文件失败 {src} -> {dst}: {str(e)}")
        return False

def create_init_files(dirs, dry_run=False):
    """在目录中创建__init__.py文件"""
    for dir_path in dirs:
        init_file = os.path.join(dir_path, "__init__.py")
        if dry_run:
            logger.info(f"[DRY RUN] 将创建初始化文件: {init_file}")
            continue
        
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(f"# 自动生成的初始化文件 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            logger.info(f"创建初始化文件: {init_file}")

def archive_directory(src, dry_run=False):
    """归档目录"""
    if not os.path.exists(src):
        logger.warning(f"源目录不存在: {src}")
        return False
    
    archive_name = f"_archived_{os.path.basename(src)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    archive_path = os.path.join(os.path.dirname(src), archive_name)
    
    if dry_run:
        logger.info(f"[DRY RUN] 将归档目录: {src} -> {archive_path}")
        return True
    
    try:
        shutil.move(src, archive_path)
        logger.info(f"归档目录: {src} -> {archive_path}")
        return True
    except Exception as e:
        logger.error(f"归档目录失败 {src}: {str(e)}")
        return False

def migrate_structure(dry_run=False):
    """迁移目录结构"""
    # 1. 创建新的目录结构
    new_dirs = [
        "newslook",
        "newslook/api",
        "newslook/crawlers",
        "newslook/tasks",
        "newslook/utils",
        "newslook/web",
        "newslook/web/static",
        "newslook/web/templates",
        "data/db/backup",
        "docs/api",
        "docs/database",
        "docs/development",
        "docs/user",
        "scripts/backup",
        "scripts/database",
        "scripts/deployment",
        "scripts/utils",
        "tests/unit",
        "tests/integration",
        "tests/data",
        "requirements",
        "logs"
    ]
    
    for dir_path in new_dirs:
        ensure_dir(dir_path, dry_run)
    
    # 2. 创建__init__.py文件
    init_dirs = [
        "newslook",
        "newslook/api",
        "newslook/crawlers",
        "newslook/tasks",
        "newslook/utils",
        "newslook/web"
    ]
    create_init_files(init_dirs, dry_run)
    
    # 3. 移动文件
    file_moves = [
        # 爬虫模块
        ("app/crawlers", "newslook/crawlers"),
        # 任务模块
        ("app/tasks", "newslook/tasks"),
        # 工具模块
        ("app/utils", "newslook/utils"),
        # Web应用
        ("app/web", "newslook/web"),
        # API
        ("api", "newslook/api"),
        # 静态资源
        ("static", "newslook/web/static"),
        # 模板
        ("templates", "newslook/web/templates"),
        # 数据库工具脚本
        ("scripts/merge_unknown_source.py", "scripts/database/merge_unknown_source.py"),
        ("scripts/update_unknown_sources.py", "scripts/database/update_unknown_sources.py"),
        ("scripts/check_unknown_sources.py", "scripts/database/check_unknown_sources.py"),
        # 配置生成脚本
        ("scripts/create_config.py", "scripts/utils/create_config.py"),
        # 文档
        ("docs/数据库工具使用说明.md", "docs/database/数据库工具使用说明.md"),
        ("docs/数据库连接说明.md", "docs/database/数据库连接说明.md"),
        ("docs/项目目录优化建议.md", "docs/development/项目目录优化建议.md")
    ]
    
    for src, dst in file_moves:
        if os.path.isdir(src):
            # 源是目录，需要复制整个目录
            if os.path.exists(src):
                files = os.listdir(src)
                for file in files:
                    src_file = os.path.join(src, file)
                    dst_file = os.path.join(dst, file)
                    if os.path.isfile(src_file):
                        copy_file(src_file, dst_file, dry_run)
        else:
            # 源是文件
            copy_file(src, dst, dry_run)
    
    # 4. 依赖文件处理
    if os.path.exists("requirements.txt"):
        copy_file("requirements.txt", "requirements/base.txt", dry_run)
    
    # 创建其他依赖文件
    dependency_files = {
        "requirements/dev.txt": "# 开发环境依赖\n-r base.txt\npylint>=2.6.0\npytest>=6.0.0\n",
        "requirements/prod.txt": "# 生产环境依赖\n-r base.txt\ngunicorn>=20.0.4\n",
        "requirements/test.txt": "# 测试环境依赖\n-r base.txt\npytest>=6.0.0\npytest-cov>=2.10.0\n"
    }
    
    for file_path, content in dependency_files.items():
        if dry_run:
            logger.info(f"[DRY RUN] 将创建文件: {file_path}")
            continue
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"创建文件: {file_path}")
    
    # 5. 更新入口文件
    if os.path.exists("run.py.new"):
        if not dry_run:
            # 备份原入口文件
            if os.path.exists("run.py"):
                backup_file = f"run.py.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2("run.py", backup_file)
                logger.info(f"备份原入口文件: run.py -> {backup_file}")
            
            # 复制新入口文件
            shutil.copy2("run.py.new", "run.py")
            logger.info("更新入口文件: run.py.new -> run.py")
        else:
            logger.info("[DRY RUN] 将更新入口文件: run.py.new -> run.py")
    
    # 6. 归档废弃目录
    archived_dirs = ["today3"]
    for dir_path in archived_dirs:
        if os.path.exists(dir_path):
            archive_directory(dir_path, dry_run)
    
    logger.info("目录结构迁移完成!")

def main():
    """主函数"""
    args = parse_args()
    
    logger.info(f"开始迁移目录结构 {'(DRY RUN)' if args.dry_run else ''}")
    
    if args.dry_run:
        logger.info("注意: 这是一个DRY RUN，不会实际执行任何操作")
    
    migrate_structure(args.dry_run)
    
    if args.dry_run:
        logger.info("DRY RUN完成，如果确认无误，请去掉--dry-run参数重新运行")
    else:
        logger.info("迁移完成，请检查新的目录结构并更新导入语句")

if __name__ == "__main__":
    main() 