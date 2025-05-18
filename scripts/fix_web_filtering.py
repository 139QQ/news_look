#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复Web页面筛选功能 - 将index路由中的SQLiteManager替换为NewsDatabase
"""

import os
import sys
import re
from datetime import datetime

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 获取routes.py的路径
routes_path = os.path.join(project_root, 'app', 'web', 'routes.py')

def backup_file(file_path):
    """备份文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{file_path}.{timestamp}.bak"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as src:
            content = src.read()
        
        with open(backup_path, 'w', encoding='utf-8') as dest:
            dest.write(content)
        
        print(f"✅ 文件已备份到: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ 备份文件失败: {str(e)}")
        return False

def fix_index_route():
    """修复index路由使用SQLiteManager的问题"""
    if not os.path.exists(routes_path):
        print(f"❌ 找不到路由文件: {routes_path}")
        return False
    
    # 读取文件内容
    try:
        with open(routes_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 读取文件失败: {str(e)}")
        return False
    
    # 检查是否已经使用NewsDatabase
    if "NewsDatabase(use_all_dbs=True)" in content:
        print("✅ index路由已经使用NewsDatabase，无需修改")
        return True
    
    # 创建备份
    if not backup_file(routes_path):
        return False
    
    # 1. 添加NewsDatabase导入
    if "from app.utils.database import NewsDatabase" not in content:
        content = content.replace(
            "from app.db.sqlite_manager import SQLiteManager",
            "from app.db.sqlite_manager import SQLiteManager\nfrom app.utils.database import NewsDatabase"
        )
        print("✅ 已添加NewsDatabase导入")
    
    # 2. 替换SQLiteManager为NewsDatabase
    content = content.replace(
        "with SQLiteManager(db_path=db_path) as db:",
        "# 使用NewsDatabase支持多数据库查询\ndb = NewsDatabase(use_all_dbs=True)"
    )
    
    # 3. 修复查询后的缩进问题（移除一级缩进，因为不再使用with语句）
    # 找到NewsDatabase声明后的内容块，减少缩进
    pattern = r"# 使用NewsDatabase支持多数据库查询\ndb = NewsDatabase\(use_all_dbs=True\)((\n\s+.*)+?)(\n\s+# 计算总页数)"
    matches = re.search(pattern, content)
    
    if matches:
        indented_code = matches.group(1)
        # 减少一级缩进(4个空格)
        unindented_code = re.sub(r"\n\s{4}", "\n", indented_code)
        content = content.replace(indented_code, unindented_code)
        print("✅ 已修复代码缩进")
    
    # 4. 修复查询方法调用
    content = content.replace(
        "news_list, total = db.get_news_paginated(",
        "# 使用NewsDatabase的query_news方法\nnews_list = db.query_news("
    )
    
    # 5. 手动计算总数
    content = content.replace(
        "# 计算总页数\n                total_pages = (total + per_page - 1) // per_page if total > 0 else 1",
        "# 计算总数和总页数\ntotal = len(db.query_news(category=category, source=source, keyword=keyword, days=days))\ntotal_pages = (total + per_page - 1) // per_page if total > 0 else 1"
    )
    
    # 6. 其他调整
    content = content.replace(
        "# 获取分类和来源列表用于筛选\n                categories = db.get_categories()\n                sources = db.get_sources()",
        "# 获取分类和来源列表用于筛选\ncategories = db.get_categories()\nsources = db.get_sources()"
    )
    
    # 将修改后的内容写回文件
    try:
        with open(routes_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ 已成功修改routes.py文件")
        return True
    except Exception as e:
        print(f"❌ 写入文件失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("=" * 80)
    print("Web页面筛选功能修复工具".center(80))
    print("=" * 80)
    
    print("\n此工具将修复index路由中的数据库连接，从SQLiteManager改为NewsDatabase")
    print("这将解决无法筛选特定来源新闻的问题")
    
    print("\n是否继续? [y/N]", end=" ")
    choice = input().strip().lower()
    
    if choice == 'y':
        success = fix_index_route()
        
        if success:
            print("\n✅ 修复完成!")
            print("\n请重新启动Web应用以使更改生效")
            print("您可以使用以下命令启动Web应用:")
            print("  python run.py web")
        else:
            print("\n❌ 修复失败")
    else:
        print("\n已取消操作")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main() 