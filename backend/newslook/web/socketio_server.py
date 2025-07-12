#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask-SocketIO服务器启动脚本
支持WebSocket实时通信和传统HTTP API
"""

import os
import sys
import logging
import signal
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.newslook.web import create_app
from backend.newslook.utils.logger import get_logger
from backend.newslook.config import get_settings

logger = get_logger(__name__)

def signal_handler(sig, frame):
    """信号处理器"""
    logger.info(f"接收到信号 {sig}，正在关闭服务器...")
    
    # 如果有WebSocket管理器，优雅关闭
    try:
        from backend.newslook.web.socketio_integration import get_websocket_manager
        ws_manager = get_websocket_manager()
        if ws_manager:
            ws_manager.shutdown()
            logger.info("WebSocket管理器已关闭")
    except:
        pass
    
    logger.info("服务器已关闭")
    sys.exit(0)

def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 获取配置
    settings = get_settings()
    
    # 创建应用
    app = create_app()
    
    # 获取WebSocket支持
    socketio = getattr(app, 'socketio', None)
    
    # 服务器配置
    host = settings.get('web.host', '127.0.0.1')
    port = settings.get('web.port', 5000)
    debug = settings.get('web.debug', False)
    
    logger.info(f"NewsLook WebSocket服务器启动中...")
    logger.info(f"监听地址: {host}:{port}")
    logger.info(f"调试模式: {debug}")
    logger.info(f"WebSocket支持: {'启用' if socketio else '禁用'}")
    
    try:
        if socketio:
            # 使用SocketIO服务器
            socketio.run(
                app,
                host=host,
                port=port,
                debug=debug,
                use_reloader=False,  # 避免重载问题
                log_output=True
            )
        else:
            # fallback到标准Flask服务器
            logger.warning("WebSocket不可用，使用标准Flask服务器")
            app.run(
                host=host,
                port=port,
                debug=debug,
                use_reloader=False
            )
            
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 