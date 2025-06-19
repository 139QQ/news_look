#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def check_database(db_path, db_name):
    """检查数据库中的数据"""
    if not os.path.exists(db_path):
        print(f"❌ {db_name} 数据库不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查记录数
        cursor.execute('SELECT COUNT(*) FROM news')
        count = cursor.fetchone()[0]
        print(f"📊 {db_name} 数据库记录数: {count}")
        
        if count > 0:
            # 查看最新的几条记录
            cursor.execute('SELECT title, source, pub_time FROM news ORDER BY crawl_time DESC LIMIT 3')
            rows = cursor.fetchall()
            print(f"🔍 {db_name} 最新记录:")
            for i, row in enumerate(rows, 1):
                title = row[0][:50] + '...' if len(row[0]) > 50 else row[0]
                print(f"  {i}. {title} | 来源: {row[1]} | 时间: {row[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 检查 {db_name} 数据库时出错: {e}")

def main():
    print("🔍 检查NewsLook数据库数据...")
    print("=" * 60)
    
    # 检查主数据库文件
    databases = [
        ('data/eastmoney.db', '东方财富(主目录)'),
        ('data/sina.db', '新浪财经(主目录)'),
        ('data/sources/东方财富.db', '东方财富(旧中文名)'),
        ('data/sources/新浪财经.db', '新浪财经(旧中文名)'),
        ('data/sources/eastmoney_finance.db', '东方财富(标准化)'),
        ('data/sources/sina_finance.db', '新浪财经(标准化)'),
        ('data/sources/netease_finance.db', '网易财经(标准化)'),
        ('data/sources/ifeng_finance.db', '凤凰财经(标准化)'),
    ]
    
    # 检查是否存在其他数据库文件
    sources_dir = 'data/sources'
    if os.path.exists(sources_dir):
        for filename in os.listdir(sources_dir):
            if filename.endswith('.db'):
                filepath = os.path.join(sources_dir, filename)
                if filepath not in [db[0] for db in databases]:
                    databases.append((filepath, f'{filename}(其他)'))
    
    # 检查所有数据库
    for db_path, db_name in databases:
        check_database(db_path, db_name)
        print()

if __name__ == "__main__":
    main() 