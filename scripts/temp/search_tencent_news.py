#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import sys

# 设置控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

def search_tencent_news(search_title=None):
    """查询腾讯财经数据库中的新闻"""
    db_path = 'data/db/腾讯财经.db'
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
        if cursor.fetchone() is None:
            print(f"数据库中没有news表")
            conn.close()
            return
        
        # 查询记录总数
        cursor.execute("SELECT COUNT(*) FROM news")
        count = cursor.fetchone()[0]
        print(f"数据库中共有 {count} 条新闻记录")
        
        # 查询最新记录
        print("\n最新5条新闻:")
        cursor.execute("SELECT id, title, pub_time, url FROM news ORDER BY pub_time DESC LIMIT 5")
        rows = cursor.fetchall()
        for idx, row in enumerate(rows, 1):
            print(f"{idx}. 标题: {row[1]}")
            print(f"   发布时间: {row[2]}")
            print(f"   URL: {row[3]}")
            print("-" * 50)
        
        # 搜索特定标题
        if search_title:
            print(f"\n搜索 '{search_title}' 的结果:")
            cursor.execute(
                "SELECT id, title, pub_time, url, content FROM news WHERE title LIKE ?", 
                (f'%{search_title}%',)
            )
            rows = cursor.fetchall()
            
            if rows:
                for idx, row in enumerate(rows, 1):
                    print(f"{idx}. 标题: {row[1]}")
                    print(f"   发布时间: {row[2]}")
                    print(f"   URL: {row[3]}")
                    content = row[4] if row[4] else "无内容"
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"   内容预览: {content_preview}")
                    print("=" * 50)
            else:
                print(f"没有找到包含 '{search_title}' 的新闻")
        
        conn.close()
        
    except Exception as e:
        print(f"查询数据库出错: {str(e)}")

if __name__ == "__main__":
    # 可以从命令行传入搜索词
    search_term = "一支药涨价21倍" if len(sys.argv) < 2 else sys.argv[1]
    search_tencent_news(search_term) 