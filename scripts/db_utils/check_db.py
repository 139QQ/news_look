#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库检查工具 - 检查所有数据库文件并显示它们的新闻数量和表结构
"""

import os
import sqlite3
import glob
from datetime import datetime
import sys

def check_single_db(db_path):
    """检查单个数据库文件"""
    print(f"\n检查数据库: {db_path}")
    file_size = os.path.getsize(db_path) / 1024  # KB
    print(f"文件大小: {file_size:.1f} KB")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取表列表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"数据库表: {[table[0] for table in tables]}")
        
        # 检查每个表的记录数
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  - 表 {table_name}: {count} 条记录")
                
                # 如果是news表，检查一些记录
                if table_name == 'news' and count > 0:
                    cursor.execute(f"SELECT id, title, source, pub_time FROM {table_name} LIMIT 3")
                    rows = cursor.fetchall()
                    print(f"  - 新闻示例:")
                    for row in rows:
                        print(f"    * ID: {row[0]}, 标题: {row[1]}, 来源: {row[2]}, 时间: {row[3]}")
            except Exception as e:
                print(f"  - 表 {table_name} 查询失败: {str(e)}")
        
        # 关闭数据库连接
        conn.close()
        
    except Exception as e:
        print(f"数据库检查失败: {str(e)}")

def main():
    """主函数"""
    # 检查数据库目录是否存在
    db_dir = 'data/db'
    if not os.path.exists(db_dir):
        print(f"数据库目录不存在: {db_dir}")
        sys.exit(1)
    
    # 获取所有数据库文件
    db_files = glob.glob(os.path.join(db_dir, '*.db'))
    if not db_files:
        print(f"未找到数据库文件")
        sys.exit(1)
    
    # 按修改时间排序，最新的在前面
    db_files.sort(key=os.path.getmtime, reverse=True)
    
    print(f"找到 {len(db_files)} 个数据库文件")
    
    # 检查每个数据库文件
    for db_file in db_files[:5]:  # 只检查最新的5个
        check_single_db(db_file)
    
    print("\n数据库检查完成")

if __name__ == '__main__':
    main() 