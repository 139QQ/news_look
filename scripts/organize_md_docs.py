#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Markdown文档整理脚本

该脚本用于整理NewsLook项目的Markdown文档，包括：
1. 将根目录中的.md文件移动到docs目录
2. 按主题对文档进行分类
3. 创建文档索引
"""

import os
import shutil
import glob
from pathlib import Path
import logging
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 文档分类规则
DOC_CATEGORIES = {
    "database": ["数据库", "database", "db", "存储"],
    "crawler": ["爬虫", "crawler", "抓取", "采集"],
    "web": ["web", "网页", "界面", "前端"],
    "api": ["api", "接口"],
    "structure": ["结构", "structure", "架构", "组织"],
    "guide": ["guide", "指南", "教程", "使用方法"]
}

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"创建目录: {directory}")

def categorize_document(filename):
    """
    根据文件名和内容对文档进行分类
    
    Args:
        filename: 文件名
    
    Returns:
        分类名称
    """
    base_name = os.path.basename(filename).lower()
    
    # 检查文件名是否匹配某个分类
    for category, keywords in DOC_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in base_name:
                return category
    
    # 如果通过文件名无法分类，检查文件内容
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            
            # 计算每个分类的关键词匹配次数
            matches = {}
            for category, keywords in DOC_CATEGORIES.items():
                matches[category] = sum(content.count(keyword.lower()) for keyword in keywords)
            
            # 返回匹配次数最多的分类
            if matches:
                return max(matches.items(), key=lambda x: x[1])[0]
    except Exception as e:
        logger.warning(f"读取文件 {filename} 内容时出错: {str(e)}")
    
    # 默认分类
    return "misc"

def move_and_organize_docs():
    """移动并组织文档"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # 确保docs目录及分类子目录存在
    docs_dir = os.path.join(project_root, "docs")
    ensure_dir(docs_dir)
    
    for category in list(DOC_CATEGORIES.keys()) + ["misc"]:
        ensure_dir(os.path.join(docs_dir, category))
    
    # 查找根目录中的所有.md文件（不包括README.md）
    md_files = [f for f in glob.glob("*.md") if os.path.basename(f).lower() != "readme.md"]
    
    if not md_files:
        logger.info("没有找到需要整理的Markdown文档")
        return
    
    # 移动并分类文档
    for file_path in md_files:
        file_name = os.path.basename(file_path)
        category = categorize_document(file_path)
        target_dir = os.path.join(docs_dir, category)
        target_path = os.path.join(target_dir, file_name)
        
        # 检查目标文件是否已存在
        if os.path.exists(target_path):
            logger.warning(f"{file_name} 已存在于 {target_dir} 中，跳过")
            continue
        
        try:
            shutil.move(file_path, target_path)
            logger.info(f"已移动 {file_name} 到 {target_dir}")
        except Exception as e:
            logger.error(f"移动 {file_name} 时出错: {str(e)}")
    
    # 创建文档索引
    create_docs_index(docs_dir)

def create_docs_index(docs_dir):
    """
    创建文档索引
    
    Args:
        docs_dir: 文档目录
    """
    index_content = "# 项目文档索引\n\n"
    
    # 遍历所有分类目录
    for category in sorted(os.listdir(docs_dir)):
        category_dir = os.path.join(docs_dir, category)
        
        if not os.path.isdir(category_dir):
            continue
        
        # 中文分类名称
        category_zh = {
            "database": "数据库文档",
            "crawler": "爬虫文档",
            "web": "Web应用文档",
            "api": "API文档",
            "structure": "项目结构文档",
            "guide": "使用指南",
            "misc": "其他文档"
        }.get(category, category)
        
        # 添加分类标题
        index_content += f"## {category_zh}\n\n"
        
        # 获取该分类下的所有md文件
        md_files = glob.glob(os.path.join(category_dir, "*.md"))
        
        if not md_files:
            index_content += "暂无文档\n\n"
            continue
        
        # 添加文件链接
        for file_path in sorted(md_files):
            file_name = os.path.basename(file_path)
            rel_path = os.path.join(category, file_name)
            
            # 尝试从文件中提取标题
            title = file_name
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('# '):
                        title = first_line[2:]
            except Exception:
                pass
            
            index_content += f"- [{title}]({rel_path})\n"
        
        index_content += "\n"
    
    # 写入索引文件
    index_path = os.path.join(docs_dir, "INDEX.md")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    logger.info(f"已创建文档索引: {index_path}")

def main():
    """主函数"""
    logger.info("开始整理Markdown文档")
    move_and_organize_docs()
    logger.info("文档整理完成")

if __name__ == "__main__":
    main() 