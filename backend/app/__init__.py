#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 应用初始化
"""

import os
import sys
import logging
from flask import Flask

# 添加项目根目录到系统路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def create_app(config=None):
    """
    创建Flask应用
    
    Args:
        config: 配置对象
        
    Returns:
        Flask: Flask应用实例
    """
    app = Flask(__name__, 
                template_folder=os.path.join(project_root, 'templates'),
                static_folder=os.path.join(project_root, 'static'))
    
    # 配置应用
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DEBUG=os.environ.get('FLASK_ENV', 'development') == 'development',
    )
    
    # 加载配置
    if config:
        app.config.from_mapping(config)
    
    # 初始化日志
    init_logger(app)
    
    # 注册路由
    with app.app_context():
        # 导入并注册Web路由
        from backend.app.web.routes import register_routes
        register_routes(app)

        # 导入并注册API蓝图
        try:
            from backend.api.stats_api import stats_api
            app.register_blueprint(stats_api, url_prefix='/api/stats', name='stats_api_blueprint')
            app.logger.info("成功注册统计API蓝图")
        except ImportError as e:
            app.logger.error(f"导入统计API蓝图失败: {str(e)}")
        except ValueError as e:
            app.logger.error(f"注册统计API蓝图失败: {str(e)}")
        
        # 导入并注册用户API蓝图
        try:
            from backend.api.user_api import user_api
            app.register_blueprint(user_api)
            app.logger.info("成功注册用户API蓝图")
        except ImportError as e:
            app.logger.error(f"导入用户API蓝图失败: {str(e)}")
    
    return app

def init_logger(app):
    """
    初始化日志
    
    Args:
        app: Flask应用实例
    """
    if not app.debug:
        # 生产环境使用更严格的日志级别
        app.logger.setLevel(logging.INFO)
        
        # 添加文件处理器
        log_dir = os.path.join(os.getcwd(), 'logs', 'web')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'app.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s')
        file_handler.setFormatter(formatter)
        
        app.logger.addHandler(file_handler)
        
        app.logger.info(f"日志初始化完成，日志文件: {log_file}")
