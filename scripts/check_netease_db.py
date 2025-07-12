#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查网易财经数据库和主数据库的同步状态
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def check_db(db_path, name):
    """检查数据库内容"""
    if not os.path.exists(db_path):
        print(f"错误: 数据库不存在 - {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 设置行工厂，返回字典
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute("SELECT COUNT(*) FROM news")
        total_count = cursor.fetchone()[0]
        print(f"\n{name}数据库总记录数: {total_count}")
        
        # 获取最近记录
        print(f"\n{name}数据库最近5条记录:")
        cursor.execute("""
            SELECT id, title, source, pub_time, crawl_time 
            FROM news 
            ORDER BY 
                CASE 
                    WHEN crawl_time IS NULL OR crawl_time = '' THEN pub_time 
                    ELSE crawl_time 
                END DESC 
            LIMIT 5
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f"ID: {row['id']}")
            print(f"标题: {row['title']}")
            print(f"来源: {row['source']}")
            print(f"发布时间: {row['pub_time']}")
            print(f"爬取时间: {row['crawl_time']}")
            print("-" * 50)
        
        # 按日期统计最近7天的记录数
        print(f"\n{name}数据库最近7天记录分布:")
        today = datetime.now().date()
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM news WHERE pub_time LIKE ?", (f"{date_str}%",))
            count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM news WHERE crawl_time LIKE ?", (f"{date_str}%",))
            crawl_count = cursor.fetchone()[0]
            print(f"  {date_str}: 发布日期={count}, 爬取日期={crawl_count}")
        
        # 检查网易财经的新闻
        if "finance_news.db" in db_path:
            print("\n主数据库中的网易财经新闻:")
            cursor.execute("SELECT COUNT(*) FROM news WHERE source='网易财经' OR source='网易财经网' OR source LIKE '%netease%'")
            count = cursor.fetchone()[0]
            print(f"网易财经新闻总数: {count}")
            
            # 最近7天的网易财经新闻
            print("\n主数据库中最近7天的网易财经新闻:")
            week_ago = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(*) FROM news 
                WHERE (source='网易财经' OR source='网易财经网' OR source LIKE '%netease%')
                AND (pub_time >= ? OR crawl_time >= ?)
            """, (week_ago, week_ago))
            count = cursor.fetchone()[0]
            print(f"最近7天的网易财经新闻数: {count}")
            
            # 显示最近的网易财经新闻
            print("\n主数据库中最近的网易财经新闻:")
            cursor.execute("""
                SELECT id, title, pub_time, crawl_time 
                FROM news 
                WHERE (source='网易财经' OR source='网易财经网' OR source LIKE '%netease%')
                ORDER BY 
                    CASE 
                        WHEN crawl_time IS NULL OR crawl_time = '' THEN pub_time 
                        ELSE crawl_time 
                    END DESC 
                LIMIT 5
            """)
            rows = cursor.fetchall()
            for row in rows:
                print(f"ID: {row['id']}")
                print(f"标题: {row['title']}")
                print(f"发布时间: {row['pub_time']}")
                print(f"爬取时间: {row['crawl_time']}")
                print("-" * 50)
        
        conn.close()
    
    except Exception as e:
        print(f"检查数据库出错: {str(e)}")

def main():
    """主函数"""
    # 检测数据库目录
    db_dir = os.path.join(project_root, 'data', 'db')
    if not os.path.exists(db_dir):
        print(f"错误: 数据库目录不存在 - {db_dir}")
        return
    
    print("=" * 80)
    print("网易财经数据库与主数据库同步状态检查".center(80))
    print("=" * 80)
    
    # 检查网易财经数据库
    netease_db_path = os.path.join(db_dir, '网易财经.db')
    check_db(netease_db_path, "网易财经")
    
    # 检查主数据库
    main_db_path = os.path.join(db_dir, 'finance_news.db')
    check_db(main_db_path, "主")
    
    print("\n" + "=" * 80)
    print("检查完成".center(80))
    print("=" * 80)

if __name__ == "__main__":
    main() 