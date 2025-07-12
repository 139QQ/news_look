#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库健康检查API
提供数据库状态监控和健康检查端点
"""

from flask import Blueprint, jsonify, request
from typing import Dict, Any
import logging
from datetime import datetime

from ..core.db_client import get_db_manager
from ..core.config_manager import get_config

logger = logging.getLogger(__name__)

# 创建健康检查蓝图
health_bp = Blueprint('health', __name__, url_prefix='/db')


@health_bp.route('/health', methods=['GET'])
def database_health():
    """
    数据库健康检查端点
    
    Returns:
        JSON: 包含所有数据库健康状态的响应
    """
    try:
        db_manager = get_db_manager()
        config = get_config()
        
        # 获取所有数据库的健康状态
        health_status = db_manager.get_all_health_status()
        
        # 计算总体健康状态
        total_healthy = 0
        total_databases = len(health_status)
        response_times = []
        
        for db_name, status in health_status.items():
            if status['health_status']['is_healthy']:
                total_healthy += 1
            response_times.append(status['health_status']['response_time_ms'])
        
        # 计算平均响应时间
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # 判断总体健康状态
        overall_healthy = total_healthy == total_databases
        
        # 构建响应
        response = {
            "code": 0,
            "data": {
                "overall_status": "healthy" if overall_healthy else "unhealthy",
                "healthy_databases": total_healthy,
                "total_databases": total_databases,
                "health_percentage": (total_healthy / total_databases * 100) if total_databases > 0 else 0,
                "average_response_time_ms": round(avg_response_time, 2),
                "check_timestamp": datetime.now().isoformat(),
                "database_details": health_status
            },
            "msg": "数据库健康检查完成"
        }
        
        # 如果不是全部健康，返回警告状态码
        if not overall_healthy:
            response["code"] = 1
            response["msg"] = f"部分数据库不健康 ({total_healthy}/{total_databases})"
        
        return jsonify(response), 200 if overall_healthy else 503
        
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return jsonify({
            "code": 500,
            "data": None,
            "msg": f"健康检查失败: {str(e)}"
        }), 500


@health_bp.route('/health/<db_name>', methods=['GET'])
def single_database_health(db_name: str):
    """
    单个数据库健康检查
    
    Args:
        db_name: 数据库名称
        
    Returns:
        JSON: 指定数据库的健康状态
    """
    try:
        db_manager = get_db_manager()
        client = db_manager.get_client(db_name)
        
        if not client:
            return jsonify({
                "code": 404,
                "data": None,
                "msg": f"数据库 {db_name} 不存在"
            }), 404
        
        # 获取单个数据库的健康状态
        health_status = client.get_connection_stats()
        
        response = {
            "code": 0,
            "data": {
                "database_name": db_name,
                "status": "healthy" if health_status['health_status']['is_healthy'] else "unhealthy",
                "details": health_status,
                "check_timestamp": datetime.now().isoformat()
            },
            "msg": f"数据库 {db_name} 健康检查完成"
        }
        
        if not health_status['health_status']['is_healthy']:
            response["code"] = 1
            response["msg"] = f"数据库 {db_name} 不健康"
        
        return jsonify(response), 200 if health_status['health_status']['is_healthy'] else 503
        
    except Exception as e:
        logger.error(f"数据库 {db_name} 健康检查失败: {e}")
        return jsonify({
            "code": 500,
            "data": None,
            "msg": f"健康检查失败: {str(e)}"
        }), 500


@health_bp.route('/connections', methods=['GET'])
def connection_pool_status():
    """
    连接池状态查询
    
    Returns:
        JSON: 所有数据库连接池的状态信息
    """
    try:
        db_manager = get_db_manager()
        
        # 获取所有连接池状态
        pool_status = {}
        for name, client in db_manager.clients.items():
            pool_status[name] = client.pool.get_status()
        
        # 计算总体连接池利用率
        total_connections = sum(status['total_connections'] for status in pool_status.values())
        total_busy = sum(status['busy_connections'] for status in pool_status.values())
        total_available = sum(status['available_connections'] for status in pool_status.values())
        
        overall_utilization = (total_busy / total_connections * 100) if total_connections > 0 else 0
        
        response = {
            "code": 0,
            "data": {
                "overall_stats": {
                    "total_connections": total_connections,
                    "busy_connections": total_busy,
                    "available_connections": total_available,
                    "utilization_percentage": round(overall_utilization, 2)
                },
                "database_pools": pool_status,
                "check_timestamp": datetime.now().isoformat()
            },
            "msg": "连接池状态查询完成"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"连接池状态查询失败: {e}")
        return jsonify({
            "code": 500,
            "data": None,
            "msg": f"连接池状态查询失败: {str(e)}"
        }), 500


@health_bp.route('/metrics', methods=['GET'])
def database_metrics():
    """
    数据库性能指标
    
    Returns:
        JSON: 数据库性能指标和统计信息
    """
    try:
        db_manager = get_db_manager()
        
        # 收集性能指标
        metrics = {
            "database_count": len(db_manager.clients),
            "healthy_databases": 0,
            "unhealthy_databases": 0,
            "average_response_time_ms": 0,
            "max_response_time_ms": 0,
            "min_response_time_ms": float('inf'),
            "total_connections": 0,
            "busy_connections": 0,
            "connection_utilization": 0
        }
        
        response_times = []
        
        for name, client in db_manager.clients.items():
            stats = client.get_connection_stats()
            health = stats['health_status']
            pool = stats['pool_status']
            
            # 健康状态统计
            if health['is_healthy']:
                metrics["healthy_databases"] += 1
            else:
                metrics["unhealthy_databases"] += 1
            
            # 响应时间统计
            response_time = health['response_time_ms']
            response_times.append(response_time)
            
            if response_time > metrics["max_response_time_ms"]:
                metrics["max_response_time_ms"] = response_time
            if response_time < metrics["min_response_time_ms"]:
                metrics["min_response_time_ms"] = response_time
            
            # 连接池统计
            metrics["total_connections"] += pool['total_connections']
            metrics["busy_connections"] += pool['busy_connections']
        
        # 计算平均响应时间
        if response_times:
            metrics["average_response_time_ms"] = round(sum(response_times) / len(response_times), 2)
            if metrics["min_response_time_ms"] == float('inf'):
                metrics["min_response_time_ms"] = 0
        
        # 计算连接利用率
        if metrics["total_connections"] > 0:
            metrics["connection_utilization"] = round(
                metrics["busy_connections"] / metrics["total_connections"] * 100, 2
            )
        
        response = {
            "code": 0,
            "data": {
                "metrics": metrics,
                "check_timestamp": datetime.now().isoformat()
            },
            "msg": "数据库性能指标收集完成"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"数据库指标收集失败: {e}")
        return jsonify({
            "code": 500,
            "data": None,
            "msg": f"指标收集失败: {str(e)}"
        }), 500


@health_bp.route('/ping', methods=['GET'])
def ping_databases():
    """
    Ping所有数据库
    
    Returns:
        JSON: 数据库连接测试结果
    """
    try:
        db_manager = get_db_manager()
        
        ping_results = {}
        
        for name, client in db_manager.clients.items():
            try:
                # 执行简单的ping查询
                start_time = datetime.now()
                result = client.execute("SELECT 1 as ping")
                end_time = datetime.now()
                
                ping_results[name] = {
                    "status": "success",
                    "response_time_ms": (end_time - start_time).total_seconds() * 1000,
                    "result": result
                }
            except Exception as e:
                ping_results[name] = {
                    "status": "failed",
                    "error": str(e),
                    "response_time_ms": 0
                }
        
        # 统计成功和失败的数量
        success_count = sum(1 for result in ping_results.values() if result["status"] == "success")
        total_count = len(ping_results)
        
        response = {
            "code": 0,
            "data": {
                "ping_results": ping_results,
                "success_count": success_count,
                "total_count": total_count,
                "success_rate": round(success_count / total_count * 100, 2) if total_count > 0 else 0,
                "check_timestamp": datetime.now().isoformat()
            },
            "msg": f"数据库Ping完成，成功率: {success_count}/{total_count}"
        }
        
        # 如果有失败的，返回警告状态码
        if success_count < total_count:
            response["code"] = 1
        
        return jsonify(response), 200 if success_count == total_count else 503
        
    except Exception as e:
        logger.error(f"数据库Ping失败: {e}")
        return jsonify({
            "code": 500,
            "data": None,
            "msg": f"Ping失败: {str(e)}"
        }), 500


# 注册健康检查路由的辅助函数
def register_health_routes(app):
    """
    注册健康检查路由到Flask应用
    
    Args:
        app: Flask应用实例
    """
    app.register_blueprint(health_bp)
    logger.info("数据库健康检查API已注册") 