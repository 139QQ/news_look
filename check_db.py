#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3

def check_database(db_path):
    """检查数据库内容"""
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    print(f"数据库文件存在: {db_path}")
    print(f"文件大小: {os.path.getsize(db_path)} 字节")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            print("数据库中没有表")
        else:
            print(f"数据库中存在 {len(tables)} 个表:")
            for table in tables:
                table_name = table[0]
                print(f"- {table_name}")
                
                # 查询表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print(f"  表 {table_name} 有 {len(columns)} 列:")
                for col in columns:
                    print(f"    {col[1]} ({col[2]})")
                
                # 查询数据数量
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  表 {table_name} 有 {count} 行数据")
                
                # 如果有数据，显示第一行
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                    row = cursor.fetchone()
                    print(f"  示例数据: {row}")
        
        conn.close()
    except Exception as e:
        print(f"查询数据库出错: {str(e)}")

if __name__ == "__main__":
    # 检查主数据库文件
    main_db_path = "db/finance_news.db"
    print("检查主数据库:")
    check_database(main_db_path)
    
    print("\n检查最近爬取的数据库:")
    data_db_dir = "data/db"
    if os.path.exists(data_db_dir):
        db_files = [f for f in os.listdir(data_db_dir) if f.endswith(".db")]
        if db_files:
            latest_db = sorted(db_files)[-1]
            latest_db_path = os.path.join(data_db_dir, latest_db)
            check_database(latest_db_path)
        else:
            print(f"目录 {data_db_dir} 中没有数据库文件")
    else:
        print(f"目录 {data_db_dir} 不存在") 