#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 后端启动脚本
简化的后端API服务器启动入口，支持前端集成启动
"""

import os
import sys
import subprocess
import threading
import time
import platform
from flask import Flask
from flask_cors import CORS

# 添加项目路径到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 导入新的配置管理器和日志系统
    try:
        from backend.newslook.core.config_manager import get_config
        from backend.newslook.core.logger_manager import get_web_logger
        from backend.newslook.core.error_handler import init_error_handler
        from backend.newslook.core.health_monitor import get_health_monitor
        
        config = get_config()
        web_config = config.web
        logger = get_web_logger()
        
        # 使用新配置管理器的配置
        app.config['SECRET_KEY'] = web_config.secret_key
        app.config['JSON_AS_ASCII'] = False
        app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
        app.config['DEBUG'] = web_config.debug
        
        # 初始化错误处理器
        error_handler = init_error_handler(app)
        logger.info("Error handler initialized")
        
        # 初始化健康监控
        health_monitor = get_health_monitor()
        if hasattr(config, 'monitoring') and config.monitoring.health_check.enabled:
            health_monitor.start_monitoring(config.monitoring.health_check.interval)
            logger.info(f"Health monitoring started with {config.monitoring.health_check.interval}s interval")
        
        # 启用CORS
        if web_config.cors_enabled:
            CORS(app, supports_credentials=True, origins=web_config.cors_origins or "*")
        else:
            CORS(app, supports_credentials=True, origins="*")
            
        logger.info(f"Web应用配置成功: Host={web_config.host}:{web_config.port}, Debug={web_config.debug}")
        print(f"✅ 使用新配置管理器和日志系统: Host={web_config.host}:{web_config.port}")
        
    except ImportError as e:
        print(f"⚠️  新配置管理器/日志系统加载失败，使用默认配置: {e}")
        # 回退到默认配置
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'newslook-dev-key')
        app.config['JSON_AS_ASCII'] = False
        app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
        
        # 启用CORS
        CORS(app, supports_credentials=True, origins="*")
        web_config = None
        logger = None
    
    # 基础健康检查路由
    @app.route('/api/health')
    def health_check():
        """健康检查接口"""
        return {
            'status': 'healthy',
            'timestamp': str(__import__('datetime').datetime.now()),
            'service': 'NewsLook Backend API'
        }
    
    # 系统监控端点
    @app.route('/api/health/detailed')
    def detailed_health_check():
        """详细健康检查接口"""
        try:
            if 'health_monitor' in locals():
                return health_monitor.get_health_status()
            else:
                return {
                    'overall_status': 'unknown',
                    'message': 'Health monitor not available'
                }
        except Exception as e:
            return {
                'overall_status': 'error',
                'error': str(e)
            }
    
    @app.route('/api/system/metrics')
    def system_metrics():
        """系统指标接口"""
        try:
            if 'health_monitor' in locals():
                return health_monitor.get_system_metrics()
            else:
                return {
                    'error': 'Health monitor not available'
                }
        except Exception as e:
            return {
                'error': str(e)
            }
    
    @app.route('/api/system/info')  
    def system_info():
        """系统信息接口"""
        try:
            if 'health_monitor' in locals():
                return health_monitor.get_system_info()
            else:
                return {
                    'error': 'Health monitor not available'
                }
        except Exception as e:
            return {
                'error': str(e)
            }
    
    @app.route('/api/errors/stats')
    def error_stats():
        """错误统计接口"""
        try:
            if 'error_handler' in locals():
                return error_handler.get_error_stats()
            else:
                return {
                    'error': 'Error handler not available'
                }
        except Exception as e:
            return {
                'error': str(e)
            }
    
    # 尝试注册完整API路由
    routes_loaded = False
    routes_error = None
    
    # 多种方式尝试加载路由
    route_import_attempts = [
        ('backend.newslook.web.routes', 'register_routes'),
        ('backend.app.web.routes', 'register_routes'),
        ('routes', 'register_routes')
    ]
    
    for module_path, function_name in route_import_attempts:
        try:
            print(f"🔄 尝试加载路由: {module_path}.{function_name}")
            module = __import__(module_path, fromlist=[function_name])
            register_routes = getattr(module, function_name)
            
            # 直接注册路由，不使用app_context
            register_routes(app)
            
            routes_loaded = True
            print(f"✅ 成功加载完整API路由: {module_path}")
            break
            
        except ImportError as e:
            print(f"⚠️  无法导入 {module_path}: {e}")
            routes_error = e
            continue
        except AssertionError as e:
            if "overwriting an existing endpoint function" in str(e):
                print(f"⚠️  路由冲突，尝试重新加载: {e}")
                # 清除可能的冲突路由
                app.url_map._rules_by_endpoint.clear()
                app.view_functions.clear()
                # 重新注册健康检查路由
                @app.route('/api/health')
                def health_check_reload():
                    return {
                        'status': 'healthy',
                        'timestamp': str(__import__('datetime').datetime.now()),
                        'service': 'NewsLook Backend API'
                    }
                # 重新尝试注册完整路由
                try:
                    register_routes(app)
                    routes_loaded = True
                    print(f"✅ 解决冲突后成功加载路由: {module_path}")
                    break
                except Exception as retry_e:
                    print(f"⚠️  重试失败: {retry_e}")
                    continue
            else:
                print(f"⚠️  加载路由 {module_path} 时出错: {e}")
                routes_error = e
                continue
        except Exception as e:
            print(f"⚠️  加载路由 {module_path} 时出错: {e}")
            routes_error = e
            continue
    
    # 如果所有尝试都失败，注册基础API路由
    if not routes_loaded:
        print("🔄 注册基础API路由...")
        register_basic_routes(app)
        print("⚠️  使用基础模式运行，功能受限")
    
    return app

def register_basic_routes(app):
    """注册基础API路由 - 当完整路由加载失败时使用"""
    
    @app.route('/api/stats')
    def basic_stats():
        """基础统计API"""
        return {
            'total_news': 0,
            'today_news': 0,
            'active_sources': 0,
            'crawl_success_rate': 0.0,
            'message': '基础模式：完整功能需要完整的后端模块',
            'available_features': ['基础API', '健康检查'],
            'status': 'limited'
        }
    
    @app.route('/api/news')
    def basic_news_list():
        """基础新闻列表API"""
        return {
            'data': [],
            'total': 0,
            'page': 1,
            'pages': 0,
            'message': '基础模式：无新闻数据'
        }
    
    @app.route('/api/crawler/status')
    def basic_crawler_status():
        """基础爬虫状态API"""
        return {
            'success': False,
            'data': [],
            'message': '基础模式：爬虫功能不可用',
            'is_running': False,
            'current_source': None,
            'progress': 0,
            'errors': ['基础模式：爬虫功能不可用']
        }
    
    @app.route('/api/sources')
    def basic_sources():
        """基础数据源API"""
        return {'data': []}
    
    @app.route('/api/stats/sources')
    def basic_stats_sources():
        """基础来源统计API"""
        return {'sources': {}}
    
    @app.route('/api/stats/daily')
    def basic_stats_daily():
        """基础每日统计API"""
        return {'daily_stats': []}
    
    # 重定向路由
    @app.route('/')
    def basic_index():
        """首页重定向"""
        from flask import redirect
        return redirect('http://localhost:3000')
    
    print("📝 基础API路由注册完成")

def check_frontend_dependencies():
    """检查前端依赖是否已安装"""
    frontend_path = os.path.join(project_root, 'frontend')
    node_modules_path = os.path.join(frontend_path, 'node_modules')
    
    if not os.path.exists(node_modules_path):
        print("⚠️  前端依赖未安装，正在安装...")
        try:
            # Windows兼容性处理
            shell_needed = platform.system() == 'Windows'
            npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
            
            try:
                subprocess.run([npm_cmd, 'install'], cwd=frontend_path, check=True, shell=shell_needed)
            except FileNotFoundError:
                npm_cmd = 'npm'
                subprocess.run([npm_cmd, 'install'], cwd=frontend_path, check=True, shell=shell_needed)
            
            print("✅ 前端依赖安装成功")
            return True
        except subprocess.CalledProcessError:
            print("❌ 前端依赖安装失败")
            return False
    return True

def start_frontend(port=3000):
    """启动前端开发服务器"""
    frontend_path = os.path.join(project_root, 'frontend')
    
    if not os.path.exists(frontend_path):
        print("❌ 前端目录不存在")
        return None
    
    if not check_frontend_dependencies():
        return None
    
    try:
        print(f"🚀 启动前端开发服务器 (端口: {port})...")
        env = os.environ.copy()
        env['PORT'] = str(port)
        
        # Windows兼容性处理
        shell_needed = platform.system() == 'Windows'
        npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
        
        try:
            process = subprocess.Popen(
                [npm_cmd, 'run', 'dev'],
                cwd=frontend_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                shell=shell_needed
            )
        except FileNotFoundError:
            npm_cmd = 'npm'
            process = subprocess.Popen(
                [npm_cmd, 'run', 'dev'],
                cwd=frontend_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                shell=shell_needed
            )
        
        # 启动线程监控前端输出
        def monitor_frontend():
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        # 确保正确处理编码
                        try:
                            print(f"[前端] {line.rstrip()}")
                        except UnicodeDecodeError:
                            print(f"[前端] {line.rstrip().encode('utf-8', errors='ignore').decode('utf-8')}")
                process.stdout.close()
            except Exception as e:
                print(f"[前端监控] 错误: {e}")
        
        monitor_thread = threading.Thread(target=monitor_frontend, daemon=True)
        monitor_thread.start()
        
        return process
    except Exception as e:
        print(f"❌ 启动前端失败: {e}")
        return None

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NewsLook 后端API服务器')
    parser.add_argument('--host', default='127.0.0.1', help='监听地址 (默认: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='监听端口 (默认: 5000)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--with-frontend', action='store_true', help='同时启动前端开发服务器')
    parser.add_argument('--frontend-port', type=int, default=3000, help='前端端口 (默认: 3000)')
    parser.add_argument('--quiet', action='store_true', help='减少输出信息')
    
    args = parser.parse_args()
    
    # 创建应用
    app = create_app()
    
    frontend_process = None
    
    # 启动前端 (如果需要)
    if args.with_frontend:
        frontend_process = start_frontend(args.frontend_port)
        if frontend_process:
            if not args.quiet:
                print(f"✅ 前端服务器启动成功 (PID: {frontend_process.pid})")
            time.sleep(2)  # 等待前端启动
        else:
            print("⚠️  前端启动失败，仅启动后端服务器")
    
    if not args.quiet:
        print("🚀 启动 NewsLook 后端API服务器")
        print(f"📍 后端地址: http://{args.host}:{args.port}")
        print(f"🔗 API地址: http://{args.host}:{args.port}/api/health")
        
        if frontend_process:
            print(f"🎨 前端地址: http://localhost:{args.frontend_port}")
        
        print("="*50)
    
    # 启动服务器
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=args.debug
        )
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n👋 正在停止服务器...")
        if frontend_process:
            if not args.quiet:
                print("📴 停止前端服务器...")
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
        if not args.quiet:
            print("✅ 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        if frontend_process:
            frontend_process.terminate()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 