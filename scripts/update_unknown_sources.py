#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
未知来源更新工具 - 更新现有数据库中未标记来源的新闻

用法:
python scripts/update_unknown_sources.py [--db-file 数据库文件名]

功能:
1. 扫描指定数据库或所有数据库中的未知来源新闻
2. 根据URL和内容特征识别正确的来源
3. 更新数据库中的来源字段
"""

import sqlite3
import os
import re
import argparse
import time
from datetime import datetime

# 数据库路径
db_dir = 'data/db'

# URL模式匹配规则
url_patterns = {
    'finance.sina.com.cn': '新浪财经',
    'sina.com.cn/finance': '新浪财经',
    'money.163.com': '网易财经',
    'finance.qq.com': '腾讯财经',
    'finance.ifeng.com': '凤凰财经',
    'eastmoney.com': '东方财富',
    'em.com.cn': '东方财富'
}

def identify_source_by_url(url):
    """通过URL识别新闻来源"""
    if not url:
        return None
    
    for pattern, source in url_patterns.items():
        if pattern in url:
            return source
    
    return None

def identify_source_by_content(title, content):
    """通过内容识别新闻来源"""
    # 简单的关键词匹配逻辑
    keywords = {
        '新浪财经': ['新浪财经', '新浪网'],
        '腾讯财经': ['腾讯财经', '财经腾讯网'],
        '东方财富': ['东方财富', '东财'],
        '网易财经': ['网易财经', '网易财报'],
        '凤凰财经': ['凤凰财经', '凤凰网财经']
    }
    
    # 合并标题和内容以增加匹配机会
    full_text = f"{title} {content if content else ''}"
    
    for source, source_keywords in keywords.items():
        for keyword in source_keywords:
            if keyword in full_text:
                return source
    
    return None

def identify_source_by_filename(filename):
    """根据数据库文件名识别来源"""
    # 移除扩展名和路径
    base_name = os.path.basename(filename)
    name_without_ext = os.path.splitext(base_name)[0]
    
    # 已知来源列表
    known_sources = ['腾讯财经', '新浪财经', '东方财富', '网易财经', '凤凰财经']
    
    # 如果文件名直接匹配某个来源
    if name_without_ext in known_sources:
        return name_without_ext
    
    return None

def update_unknown_sources(db_file, use_filename_source=True):
    """更新数据库中的未知来源"""
    db_path = os.path.join(db_dir, db_file)
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在 {db_path}")
        return 0
    
    # 从文件名识别默认来源
    default_source = None
    if use_filename_source:
        default_source = identify_source_by_filename(db_file)
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询未知来源的新闻
        cursor.execute("SELECT id, title, content, url FROM news WHERE source IS NULL OR source = '' OR source = '未知来源'")
        unknown_news = cursor.fetchall()
        
        if not unknown_news:
            print(f"数据库 {db_file} 中没有未知来源的新闻")
            conn.close()
            return 0
        
        print(f"在 {db_file} 中找到 {len(unknown_news)} 条未知来源的新闻")
        
        # 更新来源
        updated_count = 0
        default_count = 0
        
        for news_id, title, content, url in unknown_news:
            # 尝试识别来源
            source = identify_source_by_url(url)
            if not source:
                source = identify_source_by_content(title, content)
            
            # 如果无法识别但有默认来源，使用默认来源
            if not source and default_source:
                source = default_source
                default_count += 1
            
            # 更新数据库
            if source:
                cursor.execute("UPDATE news SET source = ? WHERE id = ?", (source, news_id))
                updated_count += 1
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print(f"成功更新 {updated_count} 条新闻的来源")
        if default_count > 0:
            print(f"其中 {default_count} 条使用默认来源 {default_source}")
        
        return updated_count
    
    except Exception as e:
        print(f"更新 {db_file} 时出错: {e}")
        return 0

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='更新数据库中的未知来源')
    parser.add_argument('--db-file', help='要处理的数据库文件名', default=None)
    args = parser.parse_args()
    
    print("===== 未知来源更新工具 =====")
    
    # 确保数据库目录存在
    if not os.path.exists(db_dir):
        print(f"创建数据库目录: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
    
    # 处理单个数据库或所有数据库
    total_updated = 0
    
    if args.db_file:
        # 处理指定数据库
        print(f"处理数据库: {args.db_file}")
        total_updated = update_unknown_sources(args.db_file)
    else:
        # 处理所有数据库
        print("处理所有数据库中的未知来源...")
        for db_file in os.listdir(db_dir):
            if db_file.endswith('.db') and not db_file.endswith('.bak'):
                print(f"\n处理数据库: {db_file}")
                updated = update_unknown_sources(db_file)
                total_updated += updated
    
    print(f"\n操作完成! 总共更新了 {total_updated} 条新闻的来源")

if __name__ == "__main__":
    main() 