"""
财经新闻爬虫系统 - 应用包初始化
"""

def create_app():
    """创建Flask应用实例"""
    from flask import Flask
    
    # 创建Flask应用
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static',
                instance_relative_config=True)
    
    # 注册蓝图 - 只在这里注册一次
    from app.routes.monitor import monitor_bp
    app.register_blueprint(monitor_bp)
    
    # 注册路由，但不包括注册蓝图的代码
    from app.web.routes import register_routes
    register_routes(app)
    
    return app
