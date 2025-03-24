#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - Web应用模块
"""

import os
from flask import Flask
from datetime import datetime
from app.config import get_settings
try:
    from app.crawlers.manager import CrawlerManager
except ImportError:
    CrawlerManager = None

def create_app(config=None):
    """创建Flask应用
    
    Args:
        config: 配置对象或字典
    
    Returns:
        Flask应用实例
    """
    # 获取全局设置
    settings = get_settings()
    
    # 创建Flask应用
    app = Flask(__name__)
    
    # 加载配置
    app.secret_key = settings.get('secret_key', os.urandom(24).hex())
    app.config['DEBUG'] = settings.get('debug', False)
    app.config['LOG_DIR'] = settings.get('LOG_DIR', os.path.join(os.getcwd(), 'logs'))
    app.config['DB_DIR'] = settings.get('DB_DIR', os.path.join(os.getcwd(), 'data', 'db'))
    
    # 如果提供了额外配置，则更新
    if config:
        if isinstance(config, dict):
            app.config.update(config)
        else:
            app.config.from_object(config)
    
    # 确保目录存在
    os.makedirs(os.path.join(app.root_path, 'static/css'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static/js'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static/img'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'templates'), exist_ok=True)
    os.makedirs(app.config['LOG_DIR'], exist_ok=True)
    os.makedirs(app.config['DB_DIR'], exist_ok=True)
    
    # 初始化爬虫管理器（如果可用）
    if 'CRAWLER_MANAGER' in app.config:
        app.crawler_manager = app.config['CRAWLER_MANAGER']
    elif CrawlerManager is not None:
        try:
            app.crawler_manager = CrawlerManager()
        except Exception as e:
            import traceback
            print(f"初始化爬虫管理器失败: {e}")
            traceback.print_exc()
            app.crawler_manager = None
    
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
    from app.web.routes import register_routes
    register_routes(app)
    
    return app
