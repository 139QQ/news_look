#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复web页面筛选功能问题
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.utils.logger import get_logger
from backend.app.db.SQLiteManager import SQLiteManager
from backend.app.utils.database import NewsDatabase

# 设置日志记录器
logger = get_logger('fix_filtering')

def check_db_paths():
    """检查数据库路径配置情况"""
    print("=" * 80)
    print("检查数据库路径配置".center(80))
    print("=" * 80)
    
    # 获取所有可能的数据库目录
    possible_dirs = [
        os.path.join(project_root, 'data', 'db'),
        os.path.join(project_root, 'db'),
        os.path.join(os.getcwd(), 'data', 'db'),
        os.path.join(os.getcwd(), 'db')
    ]
    
    valid_dirs = []
    for d in possible_dirs:
        if os.path.exists(d):
            valid_dirs.append(d)
            print(f"找到有效的数据库目录: {d}")
    
    # 获取web应用使用的数据库路径
    try:
        from backend.app.web.routes import get_db_path
        main_db_path = get_db_path('finance_news.db')
        print(f"\nWeb应用使用的主数据库路径: {main_db_path}")
        
        if os.path.exists(main_db_path):
            print(f"✅ 主数据库文件存在")
            print(f"文件大小: {os.path.getsize(main_db_path) / 1024:.1f} KB")
        else:
            print(f"❌ 主数据库文件不存在")
    except ImportError:
        print("❌ 无法导入get_db_path函数")
    
    # 检查来源数据库
    print("\n检查来源数据库:")
    source_dbs = []
    db_dir = valid_dirs[0] if valid_dirs else os.path.join(project_root, 'data', 'db')
    
    if os.path.exists(db_dir):
        for file in os.listdir(db_dir):
            if file.endswith('.db') and file != 'finance_news.db' and file != 'user_preferences.db':
                source_path = os.path.join(db_dir, file)
                source_dbs.append(source_path)
                print(f"- {file}: {os.path.getsize(source_path) / 1024:.1f} KB")
    
    return valid_dirs, source_dbs

def check_web_filtering_logic():
    """检查Web筛选逻辑"""
    print("\n" + "=" * 80)
    print("检查Web筛选逻辑".center(80))
    print("=" * 80)
    
    issue_found = False
    
    try:
        # 检查路由函数index中是否使用了NewsDatabase而不是SQLiteManager
        from backend.app.web.routes import index
        source_code = inspect.getsource(index)
        
        if "SQLiteManager(db_path=db_path)" in source_code and "use_all_dbs" not in source_code:
            print("❌ 发现问题: index路由使用了SQLiteManager但没有开启use_all_dbs")
            issue_found = True
        else:
            print("✅ index路由的数据库连接看起来正常")
        
        # 检查是否正确传递了source参数
        if "source=source" in source_code:
            print("✅ 正确传递了source参数")
        else:
            print("❌ 没有正确传递source参数")
            issue_found = True
        
    except (ImportError, AttributeError) as e:
        print(f"❌ 检查路由函数失败: {str(e)}")
        issue_found = True
    
    return issue_found

def test_filtering(source_name):
    """测试指定来源的筛选功能"""
    print("\n" + "=" * 80)
    print(f"测试 '{source_name}' 筛选功能".center(80))
    print("=" * 80)
    
    # 使用SQLiteManager直接查询主数据库
    try:
        from backend.app.web.routes import get_db_path
        main_db_path = get_db_path('finance_news.db')
        
        with SQLiteManager(db_path=main_db_path) as db:
            # 测试直接按来源筛选
            news_list, total = db.get_news_paginated(page=1, per_page=5, source=source_name)
            print(f"\nSQLiteManager直接筛选 '{source_name}' 结果:")
            print(f"找到 {total} 条记录")
            
            # 显示前几条记录标题
            if news_list:
                for i, news in enumerate(news_list[:3], 1):
                    print(f"{i}. {news.get('title', '无标题')} ({news.get('pub_time', '无日期')})")
            else:
                print("未找到记录")
                
    except Exception as e:
        print(f"❌ SQLiteManager测试失败: {str(e)}")
    
    # 使用NewsDatabase测试
    try:
        db = NewsDatabase(use_all_dbs=True)
        results = db.query_news(source=source_name, limit=5)
        
        print(f"\nNewsDatabase筛选 '{source_name}' 结果:")
        print(f"找到 {len(results)} 条记录")
        
        # 显示前几条记录标题
        if results:
            for i, news in enumerate(results[:3], 1):
                print(f"{i}. {news.get('title', '无标题')} ({news.get('pub_time', '无日期')})")
        else:
            print("未找到记录")
            
    except Exception as e:
        print(f"❌ NewsDatabase测试失败: {str(e)}")

def check_db_content(db_path):
    """检查数据库内容"""
    if not os.path.exists(db_path):
        print(f"❌ 数据库不存在: {db_path}")
        return
    
    db_name = os.path.basename(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查news表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
        if not cursor.fetchone():
            print(f"❌ {db_name} 中不存在news表")
            conn.close()
            return
        
        # 获取总记录数
        cursor.execute("SELECT COUNT(*) FROM news")
        total = cursor.fetchone()[0]
        
        # 获取来源分布
        cursor.execute("SELECT source, COUNT(*) FROM news GROUP BY source")
        sources = cursor.fetchall()
        
        print(f"\n{db_name} 内容概览:")
        print(f"- 总记录数: {total}")
        print(f"- 来源分布:")
        for source, count in sources:
            print(f"  • {source or '未知'}: {count}条")
        
        conn.close()
    except Exception as e:
        print(f"❌ 检查 {db_name} 内容失败: {str(e)}")

def fix_filtering_issue():
    """尝试修复筛选问题"""
    print("\n" + "=" * 80)
    print("修复筛选问题".center(80))
    print("=" * 80)
    
    # 查找web/routes.py文件
    routes_path = os.path.join(project_root, 'app', 'web', 'routes.py')
    
    if not os.path.exists(routes_path):
        print(f"❌ 找不到routes.py文件: {routes_path}")
        return
    
    # 读取文件内容
    with open(routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否需要修改
    needs_fix = False
    
    # 修改1: 替换SQLiteManager为NewsDatabase
    if "with SQLiteManager(db_path=db_path) as db:" in content and "use_all_dbs" not in content:
        print("修改点1: 替换SQLiteManager为NewsDatabase(use_all_dbs=True)")
        content = content.replace(
            "with SQLiteManager(db_path=db_path) as db:",
            "# 使用NewsDatabase支持多数据库查询\ndb = NewsDatabase(use_all_dbs=True)"
        )
        needs_fix = True
    
    # 修改2: 确保导入了NewsDatabase
    if "from backend.app.utils.database import NewsDatabase" not in content:
        import_line = "from backend.app.db.sqlite_manager import SQLiteManager"
        new_import = "from backend.app.db.sqlite_manager import SQLiteManager\nfrom backend.app.utils.database import NewsDatabase"
        content = content.replace(import_line, new_import)
        needs_fix = True
        print("修改点2: 添加NewsDatabase导入")
    
    # 是否应用修改
    if needs_fix:
        print("\n是否应用这些修改? (y/n)", end=" ")
        choice = input().strip().lower()
        
        if choice == 'y':
            # 备份原文件
            backup_path = routes_path + '.bak'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已备份原文件到: {backup_path}")
            
            # 更新文件
            with open(routes_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已更新文件: {routes_path}")
            
            print("\n请重新启动Web应用以应用更改")
        else:
            print("未应用修改")
    else:
        print("✅ 未发现需要修复的问题")

def main():
    """主函数"""
    import inspect  # 导入放在这里避免全局导入错误
    
    print("=" * 80)
    print("Web页面筛选问题诊断工具".center(80))
    print("=" * 80)
    
    # 检查数据库路径
    valid_dirs, source_dbs = check_db_paths()
    
    # 检查主数据库内容
    main_db_path = None
    for d in valid_dirs:
        path = os.path.join(d, 'finance_news.db')
        if os.path.exists(path):
            main_db_path = path
            break
    
    if main_db_path:
        check_db_content(main_db_path)
    
    # 检查来源数据库内容
    for source_db in source_dbs:
        check_db_content(source_db)
    
    # 检查Web筛选逻辑
    issue_found = check_web_filtering_logic()
    
    # 测试筛选功能
    source_names = [os.path.splitext(os.path.basename(db))[0] for db in source_dbs]
    for source in source_names[:2]:  # 只测试前两个来源
        test_filtering(source)
    
    # 尝试修复问题
    if issue_found:
        fix_filtering_issue()
    
    print("\n" + "=" * 80)
    print("诊断完成".center(80))
    print("=" * 80)
    
    print("\n建议操作:")
    print("1. 确保使用NewsDatabase(use_all_dbs=True)来查询数据")
    print("2. 确保正确传递source参数进行筛选")
    print("3. 检查模板中的筛选链接是否正确")
    print("4. 运行脚本/sync_db.py确保所有数据已同步到主数据库")

if __name__ == "__main__":
    main() 