#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库同步脚本 - 将所有源数据库中的数据同步到主数据库
"""

import os
import sys
import argparse

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库同步工具 - 将所有爬虫数据库同步到主数据库")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细日志")
    args = parser.parse_args()
    
    # 设置环境变量
    if args.verbose:
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    # 导入同步工具
    try:
        from app.utils.sync_databases import sync_all_databases
        
        # 运行同步
        print("开始同步数据库...")
        success, skip, total = sync_all_databases()
        print(f"同步完成: 总共 {total} 条新闻, 成功同步 {success} 条, 跳过 {skip} 条")
        
    except ImportError as e:
        print(f"导入同步工具失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"同步过程出错: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 