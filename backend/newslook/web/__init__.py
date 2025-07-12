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
from backend.newslook.config import get_settings

# 尝试导入CORS支持
try:
    from flask_cors import CORS
    cors_available = True
except ImportError:
    cors_available = False
try:
    from backend.newslook.crawlers.manager import CrawlerManager
except ImportError:
    CrawlerManager = None

from backend.newslook.utils.logger import get_logger, configure_logger
from backend.newslook.utils.database import NewsDatabase

# 导入WebSocket支持
from backend.newslook.web.socketio_integration import init_websocket

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
    
    # 启用CORS（如果可用）
    if cors_available:
        CORS(app, resources={
            r"/api/*": {
                "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
                "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        })
        logger.info("CORS支持已启用")
    
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
    
    # 使用统一的数据库路径管理器
    try:
        from backend.newslook.core.database_path_manager import get_database_path_manager
        
        db_path_manager = get_database_path_manager()
        
        # 获取标准数据库目录
        db_dir = str(db_path_manager.db_dir)
        
        # 尝试迁移旧数据库文件
        migrated_files = db_path_manager.migrate_old_databases()
        if migrated_files:
            logger.info(f"Web应用启动时迁移了 {len(migrated_files)} 个数据库文件到标准位置")
        
        logger.info(f"使用统一数据库路径管理器，数据库目录: {db_dir}")
        
    except Exception as e:
        logger.warning(f"统一数据库路径管理器初始化失败，使用备用方案: {e}")
        
        # 备用方案：传统的路径查找逻辑
        if config and 'DB_DIR' in config:
            db_dir = config['DB_DIR']
        else:
            db_dir = os.environ.get('DB_DIR')
            
            if not db_dir:
                possible_dirs = [
                    os.path.join(os.getcwd(), 'data', 'db'),
                    os.path.join(os.getcwd(), 'db'),
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'db'),
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'db')
                ]
                
                for possible_dir in possible_dirs:
                    if os.path.exists(possible_dir):
                        db_files = glob.glob(os.path.join(possible_dir, '*.db'))
                        if db_files:
                            db_dir = possible_dir
                            break
                
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
    
    # 初始化WebSocket支持
    try:
        socketio = init_websocket(app)
        if socketio:
            logger.info("WebSocket支持已启用")
            app.socketio = socketio
        else:
            logger.warning("WebSocket支持未启用")
    except Exception as e:
        logger.error(f"初始化WebSocket支持失败: {e}")
        app.socketio = None
    
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
    from backend.newslook.web.routes import register_routes as _register_routes
    from backend.newslook.web.enhanced_api_routes import register_enhanced_api_routes
    
    # 注册传统路由
    _register_routes(app)
    
    # 注册增强API路由
    register_enhanced_api_routes(app)
    
    logger.info("所有路由已注册完成")
    
    # 注册增强路由（新的API）
    try:
        from backend.newslook.web.enhanced_routes import register_enhanced_routes
        register_enhanced_routes(app)
        logger.info("增强路由注册完成")
    except ImportError as e:
        logger.warning(f"增强路由模块导入失败: {e}")
    except Exception as e:
        logger.error(f"增强路由注册失败: {e}")
    
    logger.info(f"Web路由注册完成")

def register_error_handlers(app):
    """注册错误处理"""
    # 通用错误处理
    def handle_generic_error(e):
        """通用错误处理"""
        logger.error(f"发生错误: {str(e)}")
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500
    
    # 注册错误处理
    for code in [400, 401, 403, 404, 405, 500, 502, 503]:
        @app.errorhandler(code)
        def handle_error(e):
            """处理HTTP错误"""
            logger.error(f"HTTP错误 {code}: {str(e)}")
            
            # 根据错误代码返回不同的消息
            error_messages = {
                400: '请求参数错误',
                401: '未授权访问',
                403: '禁止访问',
                404: '请求的资源不存在',
                405: '请求方法不被允许',
                500: '服务器内部错误',
                502: '网关错误',
                503: '服务不可用'
            }
            
            error_response = {
                'error': error_messages.get(code, '未知错误'),
                'error_code': code,
                'timestamp': datetime.now().isoformat(),
                'path': getattr(e, 'original_exception', {}).get('path', 'unknown')
            }
            
            # 如果有WebSocket管理器，广播错误信息
            if hasattr(app, 'websocket_manager') and app.websocket_manager:
                app.websocket_manager.broadcast_system_alert(
                    'http_error',
                    f"HTTP {code} 错误: {error_messages.get(code, '未知错误')}",
                    'error' if code >= 500 else 'warning'
                )
            
            return error_response, code
    
    # 注册未捕获异常处理
    @app.errorhandler(Exception)
    def handle_uncaught_exception(e):
        """处理未捕获的异常"""
        logger.error(f"未捕获的异常: {str(e)}", exc_info=True)
        
        # 如果有WebSocket管理器，广播错误信息
        if hasattr(app, 'websocket_manager') and app.websocket_manager:
            app.websocket_manager.broadcast_system_alert(
                'uncaught_exception',
                f"未捕获的异常: {str(e)}",
                'critical'
            )
        
        return {
            'error': '服务器内部错误',
            'error_code': 500,
            'timestamp': datetime.now().isoformat()
        }, 500

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
