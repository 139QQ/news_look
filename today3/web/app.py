#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - Web应用
"""

import os
from flask import Flask
from datetime import datetime

def create_app():
    """创建Flask应用"""
    # 创建Flask应用
    app = Flask(__name__)
    app.secret_key = 'finance_news_crawler_secret_key'
    
    # 确保目录存在
    os.makedirs(os.path.join(app.root_path, 'static/css'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static/js'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static/img'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'templates'), exist_ok=True)
    
    # 注册上下文处理器
    @app.context_processor
    def inject_now():
        """注入当前时间到模板"""
        return {'now': datetime.now()}
    
    # 添加max和min函数到模板上下文
    @app.context_processor
    def inject_utility_functions():
        """注入工具函数到模板"""
        return {
            'max': max,
            'min': min
        }
    
    # 注册路由
    from web.routes import register_routes
    register_routes(app)
    
    return app 