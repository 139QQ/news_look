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
from flask import Blueprint, request, jsonify, Response, send_file
from dataclasses import dataclass, asdict
import pandas as pd
import xlsxwriter
from collections import defaultdict
import base64
import tempfile
import os

from backend.newslook.core.config_manager import get_config
from backend.newslook.core.logger_manager import get_logger

# 创建蓝图
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/v1/analytics')

logger = get_logger(__name__)
config = get_config()

@dataclass
class NewsAnalytics:
    """新闻分析数据类"""
    total_news: int
    today_news: int
    sources_count: int
    avg_daily_news: float
    trend_data: List[Dict]
    source_distribution: List[Dict]
    hourly_distribution: List[Dict]
    keyword_trends: List[Dict]
    category_stats: List[Dict]

@dataclass
class PerformanceAnalytics:
    """性能分析数据类"""
    crawl_success_rate: float
    avg_response_time: float
    total_errors: int
    error_rate: float
    crawler_performance: List[Dict]
    daily_performance: List[Dict]
    error_distribution: List[Dict]

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

def get_date_range_filter(request_args) -> Tuple[str, str]:
    """获取日期范围过滤器"""
    end_date = request_args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date = request_args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    return start_date, end_date

@analytics_bp.route('/overview', methods=['GET'])
def get_analytics_overview():
    """获取分析概览 - Dashboard核心数据"""
    try:
        start_date, end_date = get_date_range_filter(request.args)
        
        # 基础统计
        total_news_query = """
            SELECT COUNT(*) as count FROM news 
            WHERE publish_time BETWEEN ? AND ?
        """
        total_result = safe_query(total_news_query, (start_date, end_date))
        total_news = total_result[0]['count'] if total_result else 0
        
        # 今日新闻
        today = datetime.now().strftime('%Y-%m-%d')
        today_news_query = """
            SELECT COUNT(*) as count FROM news 
            WHERE DATE(publish_time) = ?
        """
        today_result = safe_query(today_news_query, (today,))
        today_news = today_result[0]['count'] if today_result else 0
        
        # 来源统计
        sources_query = """
            SELECT COUNT(DISTINCT source) as count FROM news
            WHERE publish_time BETWEEN ? AND ?
        """
        sources_result = safe_query(sources_query, (start_date, end_date))
        sources_count = sources_result[0]['count'] if sources_result else 0
        
        # 平均每日新闻数
        days_diff = (datetime.strptime(end_date, '%Y-%m-%d') - 
                    datetime.strptime(start_date, '%Y-%m-%d')).days + 1
        avg_daily_news = round(total_news / days_diff, 2) if days_diff > 0 else 0
        
        # 趋势数据 - 最近7天
        trend_query = """
            SELECT 
                DATE(publish_time) as date,
                COUNT(*) as count
            FROM news 
            WHERE publish_time >= DATE('now', '-7 days')
            GROUP BY DATE(publish_time)
            ORDER BY date
        """
        trend_data = safe_query(trend_query)
        
        # 来源分布
        source_query = """
            SELECT 
                source,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM news WHERE publish_time BETWEEN ? AND ?), 2) as percentage
            FROM news 
            WHERE publish_time BETWEEN ? AND ?
            GROUP BY source
            ORDER BY count DESC
            LIMIT 10
        """
        source_distribution = safe_query(source_query, (start_date, end_date, start_date, end_date))
        
        # 小时分布
        hourly_query = """
            SELECT 
                strftime('%H', publish_time) as hour,
                COUNT(*) as count
            FROM news 
            WHERE publish_time BETWEEN ? AND ?
            GROUP BY strftime('%H', publish_time)
            ORDER BY hour
        """
        hourly_distribution = safe_query(hourly_query, (start_date, end_date))
        
        return {
            'success': True,
            'data': {
                'summary': {
                    'total_news': total_news,
                    'today_news': today_news,
                    'sources_count': sources_count,
                    'avg_daily_news': avg_daily_news
                },
                'charts': {
                    'trend': trend_data,
                    'source_distribution': source_distribution,
                    'hourly_distribution': hourly_distribution
                }
            },
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取分析概览失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@analytics_bp.route('/echarts/data', methods=['GET'])
def get_echarts_data():
    """获取ECharts图表专用数据"""
    try:
        chart_type = request.args.get('type', 'overview')
        start_date, end_date = get_date_range_filter(request.args)
        
        chart_data = {}
        
        if chart_type == 'overview' or chart_type == 'all':
            # 趋势图数据
            trend_query = """
                SELECT 
                    DATE(publish_time) as date,
                    COUNT(*) as count,
                    source
                FROM news 
                WHERE publish_time BETWEEN ? AND ?
                GROUP BY DATE(publish_time), source
                ORDER BY date, source
            """
            trend_data = safe_query(trend_query, (start_date, end_date))
            
            # 转换为ECharts格式
            dates = sorted(list(set([item['date'] for item in trend_data])))
            sources = sorted(list(set([item['source'] for item in trend_data])))
            
            # 构建系列数据
            series_data = {}
            for source in sources:
                series_data[source] = []
                for date in dates:
                    count = next((item['count'] for item in trend_data 
                                if item['date'] == date and item['source'] == source), 0)
                    series_data[source].append(count)
            
            chart_data['trend'] = {
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
        
        if chart_type == 'source' or chart_type == 'all':
            # 来源分布饼图
            source_query = """
                SELECT 
                    source as name,
                    COUNT(*) as value
                FROM news 
                WHERE publish_time BETWEEN ? AND ?
                GROUP BY source
                ORDER BY value DESC
            """
            source_data = safe_query(source_query, (start_date, end_date))
            
            chart_data['source_pie'] = {
                'title': '新闻来源分布',
                'series': [{
                    'name': '新闻数量',
                    'type': 'pie',
                    'radius': ['50%', '70%'],
                    'data': source_data,
                    'label': {
                        'show': True,
                        'formatter': '{b}: {c} ({d}%)'
                    }
                }]
            }
        
        if chart_type == 'hourly' or chart_type == 'all':
            # 小时分布柱状图
            hourly_query = """
                SELECT 
                    strftime('%H', publish_time) as hour,
                    COUNT(*) as count
                FROM news 
                WHERE publish_time BETWEEN ? AND ?
                GROUP BY strftime('%H', publish_time)
                ORDER BY hour
            """
            hourly_data = safe_query(hourly_query, (start_date, end_date))
            
            # 补充缺失的小时
            hours = [f"{i:02d}" for i in range(24)]
            hour_counts = {item['hour']: item['count'] for item in hourly_data}
            complete_hourly = [hour_counts.get(hour, 0) for hour in hours]
            
            chart_data['hourly_bar'] = {
                'title': '24小时发布分布',
                'xAxis': hours,
                'series': [{
                    'name': '新闻数量',
                    'type': 'bar',
                    'data': complete_hourly,
                    'itemStyle': {
                        'color': '#409EFF'
                    }
                }]
            }
        
        if chart_type == 'keyword' or chart_type == 'all':
            # 关键词云图 (简化版)
            keyword_query = """
                SELECT 
                    title,
                    source,
                    publish_time
                FROM news 
                WHERE publish_time BETWEEN ? AND ?
                ORDER BY publish_time DESC
                LIMIT 1000
            """
            keyword_data = safe_query(keyword_query, (start_date, end_date))
            
            # 简单的关键词提取 (可以后续集成jieba等工具)
            word_freq = defaultdict(int)
            for item in keyword_data:
                title = item['title'] or ''
                words = title.split()
                for word in words:
                    if len(word) > 1:
                        word_freq[word] += 1
            
            # 取前20个高频词
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
            
            chart_data['wordcloud'] = {
                'title': '热门关键词',
                'series': [{
                    'type': 'wordCloud',
                    'data': [{'name': word, 'value': count} for word, count in top_words],
                    'gridSize': 20,
                    'sizeRange': [12, 50]
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

@analytics_bp.route('/performance', methods=['GET'])
def get_performance_analytics():
    """获取性能分析数据"""
    try:
        start_date, end_date = get_date_range_filter(request.args)
        
        # 爬取成功率
        total_attempts_query = """
            SELECT COUNT(*) as total FROM crawler_logs 
            WHERE date BETWEEN ? AND ?
        """
        total_attempts = safe_query(total_attempts_query, (start_date, end_date))
        total_count = total_attempts[0]['total'] if total_attempts else 0
        
        success_attempts_query = """
            SELECT COUNT(*) as success FROM crawler_logs 
            WHERE date BETWEEN ? AND ? AND status = 'success'
        """
        success_attempts = safe_query(success_attempts_query, (start_date, end_date))
        success_count = success_attempts[0]['success'] if success_attempts else 0
        
        success_rate = round((success_count / total_count) * 100, 2) if total_count > 0 else 0
        
        # 平均响应时间
        avg_response_query = """
            SELECT AVG(response_time) as avg_time FROM crawler_logs 
            WHERE date BETWEEN ? AND ? AND response_time IS NOT NULL
        """
        avg_response = safe_query(avg_response_query, (start_date, end_date))
        avg_response_time = round(avg_response[0]['avg_time'], 2) if avg_response and avg_response[0]['avg_time'] else 0
        
        # 错误统计
        error_query = """
            SELECT COUNT(*) as errors FROM crawler_logs 
            WHERE date BETWEEN ? AND ? AND status = 'error'
        """
        error_result = safe_query(error_query, (start_date, end_date))
        total_errors = error_result[0]['errors'] if error_result else 0
        
        error_rate = round((total_errors / total_count) * 100, 2) if total_count > 0 else 0
        
        # 爬虫性能对比
        crawler_performance_query = """
            SELECT 
                crawler_name,
                COUNT(*) as total_runs,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs,
                AVG(response_time) as avg_response_time,
                AVG(items_scraped) as avg_items
            FROM crawler_logs 
            WHERE date BETWEEN ? AND ?
            GROUP BY crawler_name
            ORDER BY successful_runs DESC
        """
        crawler_performance = safe_query(crawler_performance_query, (start_date, end_date))
        
        # 计算每个爬虫的成功率
        for perf in crawler_performance:
            perf['success_rate'] = round((perf['successful_runs'] / perf['total_runs']) * 100, 2) if perf['total_runs'] > 0 else 0
            perf['avg_response_time'] = round(perf['avg_response_time'], 2) if perf['avg_response_time'] else 0
            perf['avg_items'] = round(perf['avg_items'], 2) if perf['avg_items'] else 0
        
        # 每日性能趋势
        daily_performance_query = """
            SELECT 
                date,
                COUNT(*) as total_runs,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs,
                AVG(response_time) as avg_response_time
            FROM crawler_logs 
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        """
        daily_performance = safe_query(daily_performance_query, (start_date, end_date))
        
        for daily in daily_performance:
            daily['success_rate'] = round((daily['successful_runs'] / daily['total_runs']) * 100, 2) if daily['total_runs'] > 0 else 0
            daily['avg_response_time'] = round(daily['avg_response_time'], 2) if daily['avg_response_time'] else 0
        
        # 错误分布
        error_distribution_query = """
            SELECT 
                error_type,
                COUNT(*) as count
            FROM crawler_logs 
            WHERE date BETWEEN ? AND ? AND status = 'error'
            GROUP BY error_type
            ORDER BY count DESC
            LIMIT 10
        """
        error_distribution = safe_query(error_distribution_query, (start_date, end_date))
        
        return {
            'success': True,
            'data': {
                'summary': {
                    'crawl_success_rate': success_rate,
                    'avg_response_time': avg_response_time,
                    'total_errors': total_errors,
                    'error_rate': error_rate,
                    'total_attempts': total_count
                },
                'charts': {
                    'crawler_performance': crawler_performance,
                    'daily_performance': daily_performance,
                    'error_distribution': error_distribution
                }
            },
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取性能分析失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

@analytics_bp.route('/reports/generate', methods=['POST'])
def generate_report():
    """生成报表"""
    try:
        data = request.get_json() or {}
        report_type = data.get('type', 'overview')  # overview, performance, detailed
        format_type = data.get('format', 'json')    # json, csv, excel
        start_date = data.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # 生成报表数据
        if report_type == 'overview':
            report_data = generate_overview_report(start_date, end_date)
        elif report_type == 'performance':
            report_data = generate_performance_report(start_date, end_date)
        elif report_type == 'detailed':
            report_data = generate_detailed_report(start_date, end_date)
        else:
            return {'error': f'不支持的报表类型: {report_type}', 'success': False}, 400
        
        # 根据格式返回数据
        if format_type == 'json':
            return {
                'success': True,
                'data': report_data,
                'metadata': {
                    'report_type': report_type,
                    'date_range': f"{start_date} 至 {end_date}",
                    'generated_at': datetime.now().isoformat()
                }
            }
        elif format_type == 'csv':
            return export_csv_report(report_data, report_type)
        elif format_type == 'excel':
            return export_excel_report(report_data, report_type, start_date, end_date)
        else:
            return {'error': f'不支持的格式: {format_type}', 'success': False}, 400
            
    except Exception as e:
        logger.error(f"生成报表失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

def generate_overview_report(start_date: str, end_date: str) -> Dict:
    """生成概览报表"""
    # 重用overview API的逻辑
    total_news_query = "SELECT COUNT(*) as count FROM news WHERE publish_time BETWEEN ? AND ?"
    total_result = safe_query(total_news_query, (start_date, end_date))
    
    source_query = """
        SELECT 
            source,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM news WHERE publish_time BETWEEN ? AND ?), 2) as percentage
        FROM news 
        WHERE publish_time BETWEEN ? AND ?
        GROUP BY source
        ORDER BY count DESC
    """
    source_data = safe_query(source_query, (start_date, end_date, start_date, end_date))
    
    daily_trend_query = """
        SELECT 
            DATE(publish_time) as date,
            COUNT(*) as count
        FROM news 
        WHERE publish_time BETWEEN ? AND ?
        GROUP BY DATE(publish_time)
        ORDER BY date
    """
    daily_trend = safe_query(daily_trend_query, (start_date, end_date))
    
    return {
        'summary': {
            'total_news': total_result[0]['count'] if total_result else 0,
            'date_range': f"{start_date} 至 {end_date}",
            'sources_count': len(source_data)
        },
        'source_distribution': source_data,
        'daily_trend': daily_trend
    }

def generate_performance_report(start_date: str, end_date: str) -> Dict:
    """生成性能报表"""
    # 爬虫性能数据
    crawler_stats_query = """
        SELECT 
            crawler_name,
            COUNT(*) as total_runs,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs,
            AVG(response_time) as avg_response_time,
            MIN(response_time) as min_response_time,
            MAX(response_time) as max_response_time
        FROM crawler_logs 
        WHERE date BETWEEN ? AND ?
        GROUP BY crawler_name
    """
    crawler_stats = safe_query(crawler_stats_query, (start_date, end_date))
    
    for stat in crawler_stats:
        stat['success_rate'] = round((stat['successful_runs'] / stat['total_runs']) * 100, 2) if stat['total_runs'] > 0 else 0
        for key in ['avg_response_time', 'min_response_time', 'max_response_time']:
            stat[key] = round(stat[key], 2) if stat[key] else 0
    
    return {
        'summary': {
            'total_crawlers': len(crawler_stats),
            'date_range': f"{start_date} 至 {end_date}"
        },
        'crawler_performance': crawler_stats
    }

def generate_detailed_report(start_date: str, end_date: str) -> Dict:
    """生成详细报表"""
    # 综合概览和性能数据
    overview = generate_overview_report(start_date, end_date)
    performance = generate_performance_report(start_date, end_date)
    
    # 添加错误分析
    error_analysis_query = """
        SELECT 
            date,
            crawler_name,
            error_type,
            error_message,
            COUNT(*) as error_count
        FROM crawler_logs 
        WHERE date BETWEEN ? AND ? AND status = 'error'
        GROUP BY date, crawler_name, error_type
        ORDER BY date DESC, error_count DESC
    """
    error_analysis = safe_query(error_analysis_query, (start_date, end_date))
    
    return {
        'overview': overview,
        'performance': performance,
        'error_analysis': error_analysis
    }

def export_csv_report(report_data: Dict, report_type: str) -> Response:
    """导出CSV格式报表"""
    try:
        output = io.StringIO()
        
        if report_type == 'overview':
            # 导出来源分布数据
            if 'source_distribution' in report_data:
                writer = csv.DictWriter(output, fieldnames=['source', 'count', 'percentage'])
                writer.writeheader()
                writer.writerows(report_data['source_distribution'])
        
        elif report_type == 'performance':
            # 导出爬虫性能数据
            if 'crawler_performance' in report_data:
                writer = csv.DictWriter(output, fieldnames=[
                    'crawler_name', 'total_runs', 'successful_runs', 'success_rate',
                    'avg_response_time', 'min_response_time', 'max_response_time'
                ])
                writer.writeheader()
                writer.writerows(report_data['crawler_performance'])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=newsLook_{report_type}_report_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
        
    except Exception as e:
        logger.error(f"导出CSV失败: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

def export_excel_report(report_data: Dict, report_type: str, start_date: str, end_date: str) -> Response:
    """导出Excel格式报表"""
    try:
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        temp_file.close()
        
        # 创建Excel工作簿
        workbook = xlsxwriter.Workbook(temp_file.name)
        
        # 添加格式
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center'
        })
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D7E4BC',
            'border': 1
        })
        data_format = workbook.add_format({
            'border': 1
        })
        
        if report_type == 'overview':
            worksheet = workbook.add_worksheet('概览报表')
            
            # 标题
            worksheet.merge_range('A1:D1', f'NewsLook 概览报表 ({start_date} 至 {end_date})', title_format)
            
            # 来源分布
            if 'source_distribution' in report_data:
                worksheet.write('A3', '来源分布', header_format)
                headers = ['来源', '数量', '占比(%)']
                for col, header in enumerate(headers):
                    worksheet.write(3, col, header, header_format)
                
                for row, item in enumerate(report_data['source_distribution'], start=4):
                    worksheet.write(row, 0, item['source'], data_format)
                    worksheet.write(row, 1, item['count'], data_format)
                    worksheet.write(row, 2, item['percentage'], data_format)
        
        elif report_type == 'performance':
            worksheet = workbook.add_worksheet('性能报表')
            
            # 标题
            worksheet.merge_range('A1:G1', f'NewsLook 性能报表 ({start_date} 至 {end_date})', title_format)
            
            # 爬虫性能
            if 'crawler_performance' in report_data:
                worksheet.write('A3', '爬虫性能统计', header_format)
                headers = ['爬虫名称', '总运行次数', '成功次数', '成功率(%)', '平均响应时间', '最小响应时间', '最大响应时间']
                for col, header in enumerate(headers):
                    worksheet.write(3, col, header, header_format)
                
                for row, item in enumerate(report_data['crawler_performance'], start=4):
                    worksheet.write(row, 0, item['crawler_name'], data_format)
                    worksheet.write(row, 1, item['total_runs'], data_format)
                    worksheet.write(row, 2, item['successful_runs'], data_format)
                    worksheet.write(row, 3, item['success_rate'], data_format)
                    worksheet.write(row, 4, item['avg_response_time'], data_format)
                    worksheet.write(row, 5, item['min_response_time'], data_format)
                    worksheet.write(row, 6, item['max_response_time'], data_format)
        
        workbook.close()
        
        # 返回文件
        def remove_file(response):
            try:
                os.unlink(temp_file.name)
            except Exception:
                pass
            return response
        
        return Response(
            open(temp_file.name, 'rb').read(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename=newsLook_{report_type}_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            }
        )
        
    except Exception as e:
        logger.error(f"导出Excel失败: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@analytics_bp.route('/export', methods=['POST'])
def export_data():
    """数据导出接口"""
    try:
        data = request.get_json() or {}
        
        export_type = data.get('type', 'news')  # news, logs, analytics
        format_type = data.get('format', 'csv')  # csv, excel, json
        filters = data.get('filters', {})
        
        start_date = filters.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        end_date = filters.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        source = filters.get('source')
        limit = min(filters.get('limit', 10000), 50000)  # 最大5万条
        
        # 构建查询
        if export_type == 'news':
            query = "SELECT * FROM news WHERE publish_time BETWEEN ? AND ?"
            params = [start_date, end_date]
            
            if source:
                query += " AND source = ?"
                params.append(source)
            
            query += f" ORDER BY publish_time DESC LIMIT {limit}"
            
        elif export_type == 'logs':
            query = "SELECT * FROM crawler_logs WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
            query += f" ORDER BY date DESC LIMIT {limit}"
            
        else:
            return {'error': f'不支持的导出类型: {export_type}', 'success': False}, 400
        
        # 查询数据
        export_data = safe_query(query, tuple(params))
        
        if not export_data:
            return {'error': '没有找到符合条件的数据', 'success': False}, 404
        
        # 根据格式导出
        if format_type == 'json':
            return {
                'success': True,
                'data': export_data,
                'count': len(export_data),
                'filters': filters,
                'timestamp': datetime.now().isoformat()
            }
            
        elif format_type == 'csv':
            if not export_data:
                return {'error': '没有数据可导出', 'success': False}, 400
            
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

@analytics_bp.route('/dashboard/config', methods=['GET'])
def get_dashboard_config():
    """获取仪表盘配置"""
    try:
        # 默认仪表盘配置
        dashboard_config = {
            'layout': [
                {
                    'id': 'overview_cards',
                    'type': 'cards',
                    'title': '总览统计',
                    'position': {'x': 0, 'y': 0, 'w': 12, 'h': 2},
                    'config': {
                        'cards': [
                            {'title': '总新闻数', 'key': 'total_news', 'color': '#409EFF'},
                            {'title': '今日新闻', 'key': 'today_news', 'color': '#67C23A'},
                            {'title': '新闻源数', 'key': 'sources_count', 'color': '#E6A23C'},
                            {'title': '日均新闻', 'key': 'avg_daily_news', 'color': '#F56C6C'}
                        ]
                    }
                },
                {
                    'id': 'trend_chart',
                    'type': 'line',
                    'title': '发布趋势',
                    'position': {'x': 0, 'y': 2, 'w': 8, 'h': 4},
                    'config': {
                        'api': '/api/v1/analytics/echarts/data?type=overview',
                        'chart_key': 'trend',
                        'refresh_interval': 300
                    }
                },
                {
                    'id': 'source_pie',
                    'type': 'pie',
                    'title': '来源分布',
                    'position': {'x': 8, 'y': 2, 'w': 4, 'h': 4},
                    'config': {
                        'api': '/api/v1/analytics/echarts/data?type=source',
                        'chart_key': 'source_pie',
                        'refresh_interval': 600
                    }
                },
                {
                    'id': 'hourly_bar',
                    'type': 'bar',
                    'title': '小时分布',
                    'position': {'x': 0, 'y': 6, 'w': 6, 'h': 3},
                    'config': {
                        'api': '/api/v1/analytics/echarts/data?type=hourly',
                        'chart_key': 'hourly_bar',
                        'refresh_interval': 900
                    }
                },
                {
                    'id': 'performance_table',
                    'type': 'table',
                    'title': '爬虫性能',
                    'position': {'x': 6, 'y': 6, 'w': 6, 'h': 3},
                    'config': {
                        'api': '/api/v1/analytics/performance',
                        'data_key': 'charts.crawler_performance',
                        'columns': [
                            {'key': 'crawler_name', 'title': '爬虫名称'},
                            {'key': 'success_rate', 'title': '成功率(%)'},
                            {'key': 'avg_response_time', 'title': '响应时间(s)'}
                        ]
                    }
                }
            ],
            'settings': {
                'auto_refresh': True,
                'refresh_interval': 300,
                'theme': 'light'
            }
        }
        
        return {
            'success': True,
            'data': dashboard_config,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取仪表盘配置失败: {str(e)}")
        return {'error': str(e), 'success': False}, 500

# 注册蓝图的函数
def register_analytics_routes(app):
    """注册数据分析路由"""
    app.register_blueprint(analytics_bp)
    logger.info("数据分析API路由已注册") 