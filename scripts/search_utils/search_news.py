#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import sys

# 设置控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

def search_in_all_dbs(search_title):
    """在所有数据库中搜索包含特定标题的新闻"""
    db_dir = 'data/db'
    results = []
    
    # 确保db_dir存在
    if not os.path.exists(db_dir):
        print(f"数据库目录不存在: {db_dir}")
        return results
    
    # 遍历数据库文件
    for file in os.listdir(db_dir):
        if file.endswith('.db') and not file.endswith('.bak'):
            try:
                db_path = os.path.join(db_dir, file)
                print(f"正在搜索数据库: {db_path}")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 先检查表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                if cursor.fetchone() is None:
                    print(f"数据库 {file} 中没有 news 表")
                    conn.close()
                    continue
                
                # 查询包含特定标题的新闻
                cursor.execute(
                    'SELECT id, title, source, pub_time, url, content FROM news WHERE title LIKE ?', 
                    ('%'+search_title+'%',)
                )
                rows = cursor.fetchall()
                
                for row in rows:
                    results.append((file, row))
                
                conn.close()
            except Exception as e:
                print(f"在 {file} 中查询出错: {str(e)}")
    
    return results

def get_news_by_id(db_path, news_id):
    """根据ID获取完整的新闻内容"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, title, content, source, pub_time, url, author, category FROM news WHERE id = ?', 
            (news_id,)
        )
        news = cursor.fetchone()
        conn.close()
        return news
    except Exception as e:
        print(f"获取新闻详情失败: {str(e)}")
        return None

if __name__ == "__main__":
    search_title = "一支药涨价21倍"
    results = search_in_all_dbs(search_title)
    
    if results:
        print(f"\n找到 {len(results)} 条相关新闻:\n" + "-"*80)
        for db_file, row in results:
            print(f"数据库: {db_file}")
            print(f"ID: {row[0]}")
            print(f"标题: {row[1]}")
            print(f"来源: {row[2]}")
            print(f"发布时间: {row[3]}")
            print(f"URL: {row[4]}")
            
            # 显示内容摘要
            content = row[5] if len(row) > 5 and row[5] else "无内容"
            print(f"内容摘要: {content[:200]}..." if len(content) > 200 else content)
            print("-"*80)
            
            # 获取完整新闻
            if row[0]:  # 如果有ID
                db_path = os.path.join('data/db', db_file)
                full_news = get_news_by_id(db_path, row[0])
                if full_news:
                    print(f"完整新闻内容:")
                    print(f"作者: {full_news[6] or '未知'}")
                    print(f"分类: {full_news[7] or '未知'}")
                    print(f"内容: {full_news[2][:1000]}..." if len(full_news[2] or '') > 1000 else full_news[2])
                    print("="*80)
    else:
        print(f"没有找到包含 '{search_title}' 的新闻") 