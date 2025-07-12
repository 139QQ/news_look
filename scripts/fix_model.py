#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型修复脚本

该脚本用于修复NewsLook项目的模型与数据库结构的一致性问题，包括：
1. 修复News模型中的字段名与数据库字段名的不一致
2. 更新相关的查询代码
"""

import os
import re
import logging
import shutil
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_file(file_path):
    """
    备份文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        备份文件路径
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_path = f"{file_path}.{timestamp}.bak"
    
    # 复制文件
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"已备份文件: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"备份文件失败: {str(e)}")
        return None

def fix_news_model():
    """修复News模型与数据库结构的一致性"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # News模型文件路径
    model_paths = [
        os.path.join(project_root, "app", "models", "news.py"),
        os.path.join(project_root, "app", "web", "models.py")
    ]
    
    # 数据库访问文件
    db_paths = [
        os.path.join(project_root, "app", "db", "database.py"),
        os.path.join(project_root, "app", "web", "database.py")
    ]
    
    # 修复News模型
    for model_path in model_paths:
        if not os.path.exists(model_path):
            logger.warning(f"模型文件不存在: {model_path}")
            continue
        
        logger.info(f"修复模型文件: {model_path}")
        
        # 备份文件
        backup_file(model_path)
        
        # 读取文件内容
        try:
            with open(model_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复字段名
            # 1. 将 publish_time 字段改为 pub_time
            content = re.sub(
                r'publish_time\s*=\s*Column\(([^)]*)\)',
                r'pub_time = Column(\1)',
                content
            )
            
            # 如果没有找到 publish_time 字段，但找到 news 类，则添加 pub_time 字段
            if 'pub_time' not in content and 'class News' in content:
                # 找到 news 类的位置
                match = re.search(r'class News\([^)]*\):\s*([^#]*)', content, re.DOTALL)
                if match:
                    class_content = match.group(1)
                    # 如果没有 pub_time 字段，添加它
                    if 'pub_time' not in class_content:
                        # 寻找合适的插入位置，在 content 字段后面
                        content_pos = class_content.find('content')
                        if content_pos != -1:
                            # 找到 content 字段行的结束位置
                            content_line_end = class_content.find('\n', content_pos)
                            if content_line_end != -1:
                                # 构建新的类内容
                                new_class_content = class_content[:content_line_end+1] + \
                                                  '    pub_time = Column(String, nullable=True)\n' + \
                                                  class_content[content_line_end+1:]
                                # 替换原有内容
                                content = content.replace(class_content, new_class_content)
                                logger.info("添加了 pub_time 字段到 News 模型")
            
            # 保存修改后的内容
            with open(model_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"已修复模型文件: {model_path}")
        except Exception as e:
            logger.error(f"修复模型文件失败: {model_path}, 错误: {str(e)}")
    
    # 修复数据库访问代码
    for db_path in db_paths:
        if not os.path.exists(db_path):
            logger.warning(f"数据库访问文件不存在: {db_path}")
            continue
        
        logger.info(f"修复数据库访问文件: {db_path}")
        
        # 备份文件
        backup_file(db_path)
        
        # 读取文件内容
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复字段名
            # 1. 将 news.publish_time 改为 news.pub_time
            content = re.sub(
                r'news\.publish_time',
                'news.pub_time',
                content
            )
            
            # 2. 将 'publish_time' 改为 'pub_time'（在SQL查询中）
            content = re.sub(
                r"'publish_time'",
                "'pub_time'",
                content
            )
            
            # 保存修改后的内容
            with open(db_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"已修复数据库访问文件: {db_path}")
        except Exception as e:
            logger.error(f"修复数据库访问文件失败: {db_path}, 错误: {str(e)}")

def main():
    """主函数"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    logger.info("开始修复模型与数据库结构的一致性")
    
    # 修复News模型
    fix_news_model()
    
    logger.info("模型与数据库结构的一致性修复完成")

if __name__ == "__main__":
    main() 