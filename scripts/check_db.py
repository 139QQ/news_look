#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库检查脚本
"""

import os
import sqlite3
import sys

def check_database(db_path):
    """检查数据库结构"""
    print(f"\n检查数据库: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        return False
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            print("数据库中没有表")
            return False
        
        print(f"数据库中的表: {', '.join([t[0] for t in tables])}")
        
        # 检查news表
        if ('news',) in tables:
            cursor.execute("PRAGMA table_info(news)")
            columns = cursor.fetchall()
            
            print("\n表news的列:")
            for col in columns:
                print(f"  {col[0]}: {col[1]} ({col[2]})")
            
            # 检查pub_time列
            has_pub_time = any(col[1] == 'pub_time' for col in columns)
            has_publish_time = any(col[1] == 'publish_time' for col in columns)
            
            if has_pub_time:
                print("\n✓ 列pub_time已存在")
            else:
                print("\n✗ 列pub_time不存在")
            
            if has_publish_time:
                print("✓ 列publish_time已存在")
            else:
                print("✗ 列publish_time不存在")
        else:
            print("表news不存在")
        
        # 关闭连接
        conn.close()
        
        return True
    except Exception as e:
        print(f"检查数据库时出错: {str(e)}")
        return False

def main():
    """主函数"""
    # 获取项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    print("开始检查数据库结构")
    
    # 检查数据库目录
    db_dir = os.path.join(project_root, "data", "db")
    if not os.path.exists(db_dir):
        print(f"错误: 数据库目录不存在: {db_dir}")
        return
    
    # 要检查的数据库列表
    db_paths = [
        os.path.join(db_dir, "finance_news.db"),
        os.path.join(db_dir, "东方财富.db"),
        os.path.join(db_dir, "凤凰财经.db"),
        os.path.join(db_dir, "新浪财经.db"),
        os.path.join(db_dir, "网易财经.db"),
        os.path.join(db_dir, "腾讯财经.db")
    ]
    
    # 检查每个数据库
    for db_path in db_paths:
        if os.path.exists(db_path):
            check_database(db_path)
    
    print("\n数据库检查完成")

if __name__ == "__main__":
    main() 