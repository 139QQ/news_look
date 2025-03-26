#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

# 连接数据库
conn = sqlite3.connect('data/db/finance_news.db')
cursor = conn.cursor()

# 查询新闻
cursor.execute('SELECT id, title, content, source, pub_time, url FROM news WHERE title LIKE ?', 
               ('%一支药涨价21倍%',))
news = cursor.fetchone()

# 打印新闻内容
if news:
    print(f"标题: {news[1]}")
    print(f"来源: {news[3]}")
    print(f"发布时间: {news[4]}")
    print(f"URL: {news[5]}")
    print("\n内容:")
    # 打印全部内容
    content = news[2] if news[2] else "无内容"
    print(content)
else:
    print("未找到相关新闻")

# 关闭连接
conn.close() 