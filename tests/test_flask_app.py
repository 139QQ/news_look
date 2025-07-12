#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Flask应用测试脚本
"""

import os
import sys
import traceback

# 设置环境变量
os.environ['LOG_LEVEL'] = 'DEBUG'

# 导入我们的日志模块
from backend.newslook.utils.logger import get_logger
logger = get_logger("test_flask")

try:
    logger.info("尝试导入newslook.web模块...")
    from backend.newslook.web import create_app
    
    logger.info("创建应用实例...")
    app = create_app()
    
    logger.info("应用实例创建成功!")
    logger.info(f"应用路由: {app.url_map}")
    
    logger.info("尝试运行应用...")
    app.run(debug=True, use_reloader=False)
    
except Exception as e:
    logger.error(f"发生错误: {str(e)}")
    traceback.print_exc()
    sys.exit(1) 