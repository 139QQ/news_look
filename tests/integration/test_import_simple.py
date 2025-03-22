#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试导入模块 - 简单版本
"""

import os
import sys

# 打印当前工作目录
print(f"当前工作目录: {os.getcwd()}")

# 打印Python路径
print(f"Python路径: {sys.path}")

# 尝试导入模块
try:
    import app
    print("成功导入 app 模块")
    
    import app.crawlers
    print("成功导入 app.crawlers 模块")
    
    from app.crawlers.eastmoney import EastmoneyCrawler
    print("成功导入 EastmoneyCrawler 类")
except ImportError as e:
    print(f"导入失败: {e}") 