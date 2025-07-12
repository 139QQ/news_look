#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 数据谱系 API 接口
提供数据血缘关系查询、影响分析和可视化的REST API
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from .data_lineage_manager import get_lineage_manager
from .lineage_tracker import track_api

logger = logging.getLogger(__name__)

# 创建蓝图
lineage_bp = Blueprint('lineage', __name__, url_prefix='/api/lineage')

@lineage_bp.route('/health', methods=['GET'])
@track_api(endpoint='/api/lineage/health', query_fields=['status'])
def health_check():
    """数据谱系服务健康检查"""
    try:
        lineage_manager = get_lineage_manager()
        return jsonify({
            'status': 'healthy',
            'service': 'data_lineage',
            'timestamp': datetime.now().isoformat(),
            'cache_enabled': bool(lineage_manager.lineage_cache)
        })
    except Exception as e:
        logger.error(f"数据谱系健康检查失败: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@lineage_bp.route('/table/<table_name>', methods=['GET'])
@track_api(endpoint='/api/lineage/table', query_fields=['lineage_relations'])
async def get_table_lineage(table_name: str):
    """
    获取表的血缘关系
    
    Query Parameters:
        direction: upstream/downstream/both (默认: both)
        format: json/graph (默认: json)
    """
    try:
        direction = request.args.get('direction', 'both')
        format_type = request.args.get('format', 'json')
        
        lineage_manager = get_lineage_manager()
        lineage_data = await lineage_manager.get_lineage_by_table(table_name, direction)
        
        if format_type == 'graph':
            # 转换为图形可视化格式
            graph_data = _convert_to_graph_format(lineage_data)
            return jsonify({
                'success': True,
                'data': graph_data,
                'format': 'graph'
            })
        
        return jsonify({
            'success': True,
            'data': lineage_data,
            'format': 'json'
        })
        
    except Exception as e:
        logger.error(f"获取表血缘关系失败 {table_name}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'table_name': table_name
        }), 500

@lineage_bp.route('/impact/<table_name>', methods=['GET'])
@track_api(endpoint='/api/lineage/impact', query_fields=['impact_analysis'])
async def analyze_impact(table_name: str):
    """
    影响分析
    
    Query Parameters:
        field: 字段名（可选）
        max_depth: 最大分析深度（默认: 5）
        format: json/tree (默认: json)
    """
    try:
        field_name = request.args.get('field')
        max_depth = int(request.args.get('max_depth', 5))
        format_type = request.args.get('format', 'json')
        
        lineage_manager = get_lineage_manager()
        impact_data = await lineage_manager.analyze_impact(
            table_name=table_name,
            field_name=field_name,
            max_depth=max_depth
        )
        
        if format_type == 'tree':
            # 转换为树形可视化格式
            tree_data = _convert_to_tree_format(impact_data)
            return jsonify({
                'success': True,
                'data': tree_data,
                'format': 'tree'
            })
        
        return jsonify({
            'success': True,
            'data': impact_data,
            'format': 'json'
        })
        
    except Exception as e:
        logger.error(f"影响分析失败 {table_name}.{field_name}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'table_name': table_name,
            'field_name': field_name
        }), 500

@lineage_bp.route('/report', methods=['GET'])
@track_api(endpoint='/api/lineage/report', query_fields=['lineage_report'])
async def generate_report():
    """
    生成数据谱系报告
    
    Query Parameters:
        tables: 表名过滤器（逗号分隔）
        systems: 系统过滤器（逗号分隔）
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    """
    try:
        # 解析过滤器
        tables = request.args.get('tables')
        table_filter = tables.split(',') if tables else None
        
        systems = request.args.get('systems')
        system_filter = systems.split(',') if systems else None
        
        # 解析日期范围
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        date_range = None
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            date_range = (start_date, end_date)
        
        lineage_manager = get_lineage_manager()
        report_data = await lineage_manager.generate_lineage_report(
            table_filter=table_filter,
            system_filter=system_filter,
            date_range=date_range
        )
        
        return jsonify({
            'success': True,
            'data': report_data
        })
        
    except Exception as e:
        logger.error(f"生成谱系报告失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@lineage_bp.route('/search', methods=['GET'])
@track_api(endpoint='/api/lineage/search', query_fields=['search_results'])
async def search_lineage():
    """
    搜索数据血缘关系
    
    Query Parameters:
        q: 搜索关键词
        type: 搜索类型 (table/field/system/all)
        limit: 结果限制数量 (默认: 20)
    """
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')
        limit = int(request.args.get('limit', 20))
        
        if not query:
            return jsonify({
                'success': False,
                'error': '搜索关键词不能为空'
            }), 400
        
        lineage_manager = get_lineage_manager()
        
        async with lineage_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            
            search_results = {
                'query': query,
                'search_type': search_type,
                'results': [],
                'total_count': 0
            }
            
            # 构建搜索条件
            if search_type in ['table', 'all']:
                await cursor.execute("""
                    SELECT DISTINCT source_table as table_name, 'source' as role, COUNT(*) as relation_count
                    FROM data_lineage
                    WHERE source_table LIKE ?
                    GROUP BY source_table
                    UNION
                    SELECT DISTINCT target_table as table_name, 'target' as role, COUNT(*) as relation_count
                    FROM data_lineage
                    WHERE target_table LIKE ?
                    GROUP BY target_table
                    LIMIT ?
                """, (f'%{query}%', f'%{query}%', limit))
                
                table_results = await cursor.fetchall()
                for row in table_results:
                    search_results['results'].append({
                        'type': 'table',
                        'name': row[0],
                        'role': row[1],
                        'relation_count': row[2]
                    })
            
            if search_type in ['field', 'all']:
                await cursor.execute("""
                    SELECT DISTINCT source_field as field_name, source_table as table_name, 'source' as role
                    FROM data_lineage
                    WHERE source_field LIKE ? AND source_field IS NOT NULL
                    UNION
                    SELECT DISTINCT target_field as field_name, target_table as table_name, 'target' as role
                    FROM data_lineage
                    WHERE target_field LIKE ? AND target_field IS NOT NULL
                    LIMIT ?
                """, (f'%{query}%', f'%{query}%', limit))
                
                field_results = await cursor.fetchall()
                for row in field_results:
                    search_results['results'].append({
                        'type': 'field',
                        'name': row[0],
                        'table_name': row[1],
                        'role': row[2]
                    })
            
            search_results['total_count'] = len(search_results['results'])
        
        return jsonify({
            'success': True,
            'data': search_results
        })
        
    except Exception as e:
        logger.error(f"搜索血缘关系失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@lineage_bp.route('/stats', methods=['GET'])
@track_api(endpoint='/api/lineage/stats', query_fields=['lineage_stats'])
async def get_lineage_stats():
    """获取数据谱系统计信息"""
    try:
        lineage_manager = get_lineage_manager()
        
        async with lineage_manager.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 基础统计
            await cursor.execute("""
                SELECT 
                    COUNT(*) as total_relations,
                    COUNT(DISTINCT source_table) as source_tables,
                    COUNT(DISTINCT target_table) as target_tables,
                    COUNT(DISTINCT source_system) as source_systems,
                    COUNT(DISTINCT target_system) as target_systems
                FROM data_lineage
            """)
            
            basic_stats = await cursor.fetchone()
            
            # 按类型统计
            await cursor.execute("""
                SELECT transformation_type, COUNT(*) as count
                FROM data_lineage
                GROUP BY transformation_type
                ORDER BY count DESC
            """)
            
            type_stats = {}
            async for row in cursor:
                type_stats[row[0]] = row[1]
            
            # 最近7天的活动
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            await cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM data_lineage
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date
            """, (week_ago,))
            
            daily_activity = []
            async for row in cursor:
                daily_activity.append({
                    'date': row[0],
                    'count': row[1]
                })
            
            stats_data = {
                'basic_statistics': {
                    'total_relations': basic_stats[0],
                    'source_tables': basic_stats[1],
                    'target_tables': basic_stats[2],
                    'source_systems': basic_stats[3],
                    'target_systems': basic_stats[4]
                },
                'transformation_types': type_stats,
                'daily_activity': daily_activity,
                'generated_at': datetime.now().isoformat()
            }
        
        return jsonify({
            'success': True,
            'data': stats_data
        })
        
    except Exception as e:
        logger.error(f"获取谱系统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def _convert_to_graph_format(lineage_data: Dict[str, Any]) -> Dict[str, Any]:
    """转换为图形可视化格式"""
    nodes = []
    edges = []
    node_ids = set()
    
    table_name = lineage_data.get('table_name')
    
    # 添加中心节点（目标表）
    center_node_id = f"table_{table_name}"
    nodes.append({
        'id': center_node_id,
        'label': table_name,
        'type': 'center_table',
        'size': 30,
        'color': '#1890ff'
    })
    node_ids.add(center_node_id)
    
    # 处理上游节点
    for upstream in lineage_data.get('upstream', []):
        source_id = f"table_{upstream['source_table']}"
        if source_id not in node_ids:
            nodes.append({
                'id': source_id,
                'label': upstream['source_table'],
                'type': 'source_table',
                'size': 20,
                'color': '#52c41a'
            })
            node_ids.add(source_id)
        
        edges.append({
            'source': source_id,
            'target': center_node_id,
            'label': upstream['transformation_type'],
            'type': 'upstream'
        })
    
    # 处理下游节点
    for downstream in lineage_data.get('downstream', []):
        target_id = f"table_{downstream['target_table']}"
        if target_id not in node_ids:
            nodes.append({
                'id': target_id,
                'label': downstream['target_table'],
                'type': 'target_table',
                'size': 20,
                'color': '#ff7a45'
            })
            node_ids.add(target_id)
        
        edges.append({
            'source': center_node_id,
            'target': target_id,
            'label': downstream['transformation_type'],
            'type': 'downstream'
        })
    
    return {
        'nodes': nodes,
        'edges': edges,
        'center_table': table_name
    }

def _convert_to_tree_format(impact_data: Dict[str, Any]) -> Dict[str, Any]:
    """转换为树形可视化格式"""
    
    def build_tree_node(item, depth=0):
        return {
            'id': f"{item.get('target_table', 'unknown')}_{depth}",
            'name': item.get('target_table', 'unknown'),
            'field': item.get('target_field'),
            'system': item.get('target_system'),
            'transformation': item.get('transformation_type'),
            'rule': item.get('transformation_rule'),
            'depth': depth,
            'children': [build_tree_node(child, depth + 1) for child in item.get('children', [])]
        }
    
    root_node = {
        'id': 'root',
        'name': impact_data.get('source_table'),
        'field': impact_data.get('source_field'),
        'system': 'newslook',
        'type': 'root',
        'depth': 0,
        'children': [build_tree_node(item, 1) for item in impact_data.get('impact_tree', [])]
    }
    
    return {
        'tree': root_node,
        'summary': {
            'total_affected': impact_data.get('total_affected_count', 0),
            'affected_systems': impact_data.get('affected_systems', []),
            'affected_tables': impact_data.get('affected_tables', []),
            'max_depth': impact_data.get('max_depth', 0)
        }
    } 