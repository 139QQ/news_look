#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - Web应用模块
"""

# 导入日志模块前先禁用所有默认日志处理器
import logging
if not hasattr(logging.root, '_initialized'):
    # 移除所有默认处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # 禁用第三方库日志
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("chardet").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    
    # 设置Flask的日志级别为WARNING，减少路由日志输出
    logging.getLogger("flask").setLevel(logging.WARNING)
    
    # 标记root logger已初始化
    logging.root._initialized = True

import os
import glob
from flask import Flask
from datetime import datetime
from newslook.config import get_settings
try:
    from newslook.crawlers.manager import CrawlerManager
except ImportError:
    CrawlerManager = None

from newslook.utils.logger import get_logger, configure_logger
from newslook.utils.database import NewsDatabase

# 获取日志记录器
logger = get_logger("web")

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
    
    # 配置Jinja2模板引擎
    app.jinja_options = {
        'extensions': ['jinja2.ext.do', 'jinja2.ext.loopcontrols'],
        'autoescape': True,
    }
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['JSON_AS_ASCII'] = False  # 确保JSON响应支持非ASCII字符
    
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
    logger.info(f"Web应用使用数据库目录: {db_dir}")
    logger.info(f"找到 {len(db_files)} 个数据库文件")
    for db_file in sorted(db_files, key=os.path.getmtime, reverse=True)[:5]:  # 只显示最新的5个
        file_size = os.path.getsize(db_file) / 1024  # KB
        logger.info(f"  - {os.path.basename(db_file)} ({file_size:.1f} KB)")
    if len(db_files) > 5:
        logger.info(f"  - ... 以及其他 {len(db_files) - 5} 个数据库文件")
    
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
        logger.info("使用配置中提供的爬虫管理器")
    elif CrawlerManager is not None:
        try:
            app.crawler_manager = CrawlerManager()
            logger.info("成功初始化爬虫管理器")
        except Exception as e:
            logger.error(f"初始化爬虫管理器失败: {e}")
            app.crawler_manager = None
    else:
        logger.warning("CrawlerManager模块不可用，爬虫功能将不可用")
        app.crawler_manager = None
    
    # 初始化数据库连接
    app.db = NewsDatabase(use_all_dbs=True)
    app.config['DB'] = app.db
    
    # 注册上下文处理器、路由和错误处理
    register_context_processors(app)
    register_template_filters(app)
    register_routes(app)
    register_error_handlers(app)
    
    # 添加响应头处理，确保正确的编码
    @app.after_request
    def add_header(response):
        """确保响应使用正确的编码"""
        if response.headers.get('Content-Type', '').startswith('text/html'):
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
    
    logger.info(f"Web应用初始化完成")
    return app

def register_routes(app):
    """注册路由"""
    from newslook.web.routes import register_routes as _register_routes
    _register_routes(app)
    logger.info(f"Web路由注册完成")

def register_error_handlers(app):
    """注册错误处理"""
    from flask import render_template
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"服务器错误: {str(e)}")
        return render_template('500.html'), 500

def register_context_processors(app):
    """注册上下文处理器"""
    @app.context_processor
    def inject_now():
        """注入当前时间到模板"""
        return {'now': datetime.now()}
    
    @app.context_processor
    def inject_utility_functions():
        """注入工具函数到模板"""
        return {
            'max': max,
            'min': min
        }

def register_template_filters(app):
    """注册模板过滤器"""
    @app.template_filter('datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M'):
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(value)
        elif isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        elif isinstance(value, datetime):
            dt = value
        else:
            return value
        return dt.strftime(format)
