#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import sys
import json
import re

# 设置控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

def get_full_news(search_title):
    """获取完整的新闻内容"""
    db_path = 'data/db/finance_news.db'
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询特定新闻
        cursor.execute(
            "SELECT id, title, source, pub_time, url, content, author, content_html FROM news WHERE title LIKE ?", 
            (f'%{search_title}%',)
        )
        row = cursor.fetchone()
        
        if row:
            # 打印完整新闻信息
            print("=" * 80)
            print(f"标题: {row[1]}")
            print(f"来源: {row[2]}")
            print(f"作者: {row[6] or '未知'}")
            print(f"发布时间: {row[3]}")
            print(f"URL: {row[4]}")
            print("-" * 80)
            print("新闻正文:")
            print(row[5] or "无内容")
            print("=" * 80)
            
            # 将内容导出到文件
            output_dir = "data/output"
            os.makedirs(output_dir, exist_ok=True)
            
            # 创建安全的文件名
            title_for_filename = re.sub(r'[\\/*?:"<>|]', '_', row[1])
            title_for_filename = title_for_filename[:40]  # 限制长度
            safe_filename = f"news_{title_for_filename}"
            
            # 保存纯文本版本
            output_file = os.path.join(output_dir, f"{safe_filename}.txt")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"标题: {row[1]}\n")
                f.write(f"来源: {row[2]}\n")
                f.write(f"作者: {row[6] or '未知'}\n")
                f.write(f"发布时间: {row[3]}\n")
                f.write(f"URL: {row[4]}\n")
                f.write("-" * 80 + "\n")
                f.write("新闻正文:\n")
                f.write(row[5] or "无内容")
            
            print(f"新闻内容已保存到: {output_file}")
            
            # 如果有HTML内容，也保存为HTML文件
            if row[7]:  # content_html
                html_file = os.path.join(output_dir, f"{safe_filename}.html")
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{row[1]}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        h1 {{ color: #333; }}
        .meta {{ color: #666; margin-bottom: 20px; }}
        .content {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>{row[1]}</h1>
    <div class="meta">
        <p>来源: {row[2]} | 作者: {row[6] or '未知'} | 发布时间: {row[3]}</p>
        <p>原文链接: <a href="{row[4]}" target="_blank">{row[4]}</a></p>
    </div>
    <hr>
    <div class="content">
    {row[7]}
    </div>
</body>
</html>""")
                print(f"新闻HTML内容已保存到: {html_file}")
            
        else:
            print(f"没有找到包含 '{search_title}' 的新闻")
        
        conn.close()
        
    except Exception as e:
        print(f"获取新闻内容出错: {str(e)}")

if __name__ == "__main__":
    # 可以从命令行传入搜索词
    search_term = "一支药涨价21倍" if len(sys.argv) < 2 else sys.argv[1]
    get_full_news(search_term) 