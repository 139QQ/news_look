#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - Web应用模块
"""

import os
import glob
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
    
    # 确保日志目录存在
    log_dir = settings.get('LOG_DIR', os.path.join(os.getcwd(), 'logs'))
    app.config['LOG_DIR'] = log_dir
    os.makedirs(log_dir, exist_ok=True)
    
    # 确定数据库目录
    if config and 'DB_DIR' in config:
        # 使用传入的DB_DIR配置
        db_dir = config['DB_DIR']
    else:
        # 尝试从环境变量获取
        db_dir = os.environ.get('DB_DIR')
        
        # 如果环境变量中没有，则尝试自动查找
        if not db_dir:
            # 尝试查找数据库目录
            possible_dirs = [
                os.path.join(os.getcwd(), 'data', 'db'),
                os.path.join(os.getcwd(), 'db'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'db'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'db')
            ]
            
            # 查找包含数据库文件的目录
            for possible_dir in possible_dirs:
                if os.path.exists(possible_dir):
                    db_files = glob.glob(os.path.join(possible_dir, '*.db'))
                    if db_files:
                        db_dir = possible_dir
                        break
            
            # 如果没找到含数据库文件的目录，使用默认目录
            if not db_dir:
                db_dir = os.path.join(os.getcwd(), 'data', 'db')
    
    # 确保数据库目录存在
    app.config['DB_DIR'] = db_dir
    os.makedirs(db_dir, exist_ok=True)
    
    # 查找并输出数据库文件情况
    db_files = glob.glob(os.path.join(db_dir, '*.db'))
    print(f"Web应用使用数据库目录: {db_dir}")
    print(f"找到 {len(db_files)} 个数据库文件:")
    for db_file in sorted(db_files, key=os.path.getmtime, reverse=True)[:5]:  # 只显示最新的5个
        file_size = os.path.getsize(db_file) / 1024  # KB
        print(f"  - {os.path.basename(db_file)} ({file_size:.1f} KB)")
    if len(db_files) > 5:
        print(f"  - ... 以及其他 {len(db_files) - 5} 个数据库文件")
    
    # 设置环境变量，以便其他模块访问
    os.environ['DB_DIR'] = db_dir
    
    # 如果提供了额外配置，则更新
    if config:
        if isinstance(config, dict):
            app.config.update(config)
        else:
            app.config.from_object(config)
    
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
