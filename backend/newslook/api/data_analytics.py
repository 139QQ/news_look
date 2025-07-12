#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据分析API - ECharts仪表盘、报表生成器、导出引擎
支持实时数据分析、多维度统计、数据导出
"""

import json
import csv
import io
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from flask import Blueprint, request, jsonify, Response
from dataclasses import dataclass, asdict
from collections import defaultdict
import tempfile
import os

from backend.newslook.config import get_settings
from backend.newslook.utils.logger import get_logger

# 创建蓝图
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/v1/analytics')

logger = get_logger(__name__)
config = get_settings()

def get_database_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    try:
        from backend.newslook.config import get_unified_db_path
        db_path = get_unified_db_path()
        
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        return conn
    except Exception as e:
        logger.error(f"获取数据库连接失败: {str(e)}")
        raise

def safe_query(query: str, params: Tuple = ()) -> List[Dict]:
    """安全查询数据库"""
    try:
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"数据库查询失败: {query}, 错误: {str(e)}")
        return []

@analytics_bp.route('/overview', methods=['GET'])
def get_analytics_overview():
    """获取分析概览"""
    try:
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # 基础统计
        total_news_query = "SELECT COUNT(*) as count FROM news WHERE pub_time BETWEEN ? AND ?"
        total_result = safe_query(total_news_query, (start_date, end_date))
        total_news = total_result[0]['count'] if total_result else 0
        
        # 今日新闻
        today = datetime.now().strftime('%Y-%m-%d')
        today_news_query = "SELECT COUNT(*) as count FROM news WHERE DATE(pub_time) = ?"
        today_result = safe_query(today_news_query, (today,))
        today_news = today_result[0]['count'] if today_result else 0
        
        # 来源统计
        sources_query = "SELECT COUNT(DISTINCT source) as count FROM news WHERE pub_time BETWEEN ? AND ?"
        sources_result = safe_query(sources_query, (start_date, end_date))
        sources_count = sources_result[0]['count'] if sources_result else 0
        
        # 趋势数据
        trend_query = """
            SELECT 
                DATE(pub_time) as date,
                COUNT(*) as count
            FROM news 
            WHERE pub_time >= DATE('now', '-7 days')
            GROUP BY DATE(pub_time)
            ORDER BY date
        """
        trend_data = safe_query(trend_query)
        
        # 来源分布
        source_query = """
            SELECT 
                source,
                COUNT(*) as count
            FROM news 
            WHERE pub_time BETWEEN ? AND ?
            GROUP BY source
            ORDER BY count DESC
            LIMIT 10
        """
        source_distribution = safe_query(source_query, (start_date, end_date))
        
        return {
            'success': True,
            'data': {
                'summary': {
                    'total_news': total_news,
                    'today_news': today_news,
                    'sources_count': sources_count
                },
                'charts': {
                    'trend': trend_data,
                    'source_distribution': source_distribution
                }
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取分析概览失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@analytics_bp.route('/echarts/data', methods=['GET'])
def get_echarts_data():
    """获取ECharts图表数据"""
    try:
        chart_type = request.args.get('type', 'overview')
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        chart_data = {}
        
        if chart_type == 'trend':
            # 趋势图数据
            trend_query = """
                SELECT 
                    DATE(pub_time) as date,
                    COUNT(*) as count,
                    source
                FROM news 
                WHERE pub_time BETWEEN ? AND ?
                GROUP BY DATE(pub_time), source
                ORDER BY date, source
            """
            trend_data = safe_query(trend_query, (start_date, end_date))
            
            # 转换为ECharts格式
            dates = sorted(list(set([item['date'] for item in trend_data])))
            sources = sorted(list(set([item['source'] for item in trend_data])))
            
            series_data = {}
            for source in sources:
                series_data[source] = []
                for date in dates:
                    count = next((item['count'] for item in trend_data 
                                if item['date'] == date and item['source'] == source), 0)
                    series_data[source].append(count)
            
            chart_data = {
                'title': '新闻发布趋势',
                'xAxis': dates,
                'series': [
                    {
                        'name': source,
                        'type': 'line',
                        'data': data,
                        'smooth': True
                    }
                    for source, data in series_data.items()
                ]
            }
        
        elif chart_type == 'source':
            # 来源分布饼图
            source_query = """
                SELECT 
                    source as name,
                    COUNT(*) as value
                FROM news 
                WHERE pub_time BETWEEN ? AND ?
                GROUP BY source
                ORDER BY value DESC
            """
            source_data = safe_query(source_query, (start_date, end_date))
            
            chart_data = {
                'title': '新闻来源分布',
                'series': [{
                    'name': '新闻数量',
                    'type': 'pie',
                    'radius': ['50%', '70%'],
                    'data': source_data
                }]
            }
        
        return {
            'success': True,
            'data': chart_data,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取ECharts数据失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@analytics_bp.route('/export', methods=['POST'])
def export_data():
    """数据导出接口"""
    try:
        data = request.get_json() or {}
        
        export_type = data.get('type', 'news')
        format_type = data.get('format', 'csv')
        filters = data.get('filters', {})
        
        start_date = filters.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        end_date = filters.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        limit = min(filters.get('limit', 1000), 10000)
        
        # 构建查询
        if export_type == 'news':
            query = "SELECT * FROM news WHERE pub_time BETWEEN ? AND ? ORDER BY pub_time DESC LIMIT ?"
            params = (start_date, end_date, limit)
        else:
            return {'error': f'不支持的导出类型: {export_type}', 'success': False}, 400
        
        # 查询数据
        export_data = safe_query(query, params)
        
        if not export_data:
            return {'error': '没有找到符合条件的数据', 'success': False}, 404
        
        # 根据格式导出
        if format_type == 'json':
            return {
                'success': True,
                'data': export_data,
                'count': len(export_data),
                'timestamp': datetime.now().isoformat()
            }
            
        elif format_type == 'csv':
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
            writer.writeheader()
            writer.writerows(export_data)
            
            output.seek(0)
            
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=newsLook_{export_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                }
            )
            
        else:
            return {'error': f'不支持的导出格式: {format_type}', 'success': False}, 400
            
    except Exception as e:
        logger.error(f"数据导出失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

# 注册蓝图的函数
def register_analytics_routes(app):
    """注册数据分析路由"""
    app.register_blueprint(analytics_bp)
    logger.info("数据分析API路由已注册") 