#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版路由注册 - 整合所有优化的API
包含爬虫控制、系统监控、数据分析等高级功能
"""

from flask import Flask
from backend.newslook.utils.logger import get_logger

logger = get_logger(__name__)

def register_enhanced_routes(app: Flask):
    """注册所有增强版API路由"""
    try:
        # 注册爬虫控制API
        try:
            from backend.newslook.api.crawler_control import register_crawler_control_routes
            register_crawler_control_routes(app)
            logger.info("✅ 爬虫控制API已注册")
        except Exception as e:
            logger.error(f"❌ 爬虫控制API注册失败: {str(e)}")
        
        # 注册系统监控API
        try:
            from backend.newslook.api.system_monitor import register_system_monitor_routes
            register_system_monitor_routes(app)
            logger.info("✅ 系统监控API已注册")
        except Exception as e:
            logger.error(f"❌ 系统监控API注册失败: {str(e)}")
        
        # 注册数据分析API
        try:
            from backend.newslook.api.data_analytics import register_analytics_routes
            register_analytics_routes(app)
            logger.info("✅ 数据分析API已注册")
        except Exception as e:
            logger.error(f"❌ 数据分析API注册失败: {str(e)}")
        
        # 注册基础API（保持兼容性）
        # 统一API暂时未实现，跳过此步骤
        logger.info("⚠️ 统一API暂未实现，跳过注册")
        
        # 添加API根路由
        @app.route('/api/v1/status')
        def api_status():
            """API状态检查"""
            return {
                'status': 'online',
                'version': '3.1',
                'apis': {
                    'crawler_control': '/api/v1/crawlers',
                    'system_monitor': '/api/v1/system',
                    'data_analytics': '/api/v1/analytics',
                    'health_check': '/api/health'
                }
            }
        
        logger.info("🚀 所有增强版API路由注册完成")
        
    except Exception as e:
        logger.error(f"❌ 增强版路由注册失败: {str(e)}")
        raise 