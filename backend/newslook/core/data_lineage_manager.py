#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 数据谱系管理器
实现数据血缘关系的自动追踪、记录和影响分析功能
"""

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from .unified_database_manager import UnifiedDatabaseManager
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)

class LineageType(Enum):
    """数据谱系类型"""
    CRAWLER_SOURCE = "crawler_source"      # 爬虫数据源
    DATA_TRANSFORMATION = "data_transformation"  # 数据转换
    API_ACCESS = "api_access"              # API访问
    DATA_VALIDATION = "data_validation"    # 数据验证
    DATA_EXPORT = "data_export"           # 数据导出


@dataclass
class LineageNode:
    """数据谱系节点"""
    node_id: str
    node_type: str  # source/process/target
    system_name: str
    table_name: str
    field_name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LineageRelation:
    """数据谱系关系"""
    relation_id: str
    source_node: LineageNode
    target_node: LineageNode
    lineage_type: LineageType
    transformation_rule: Optional[str] = None
    created_at: datetime = None
    created_by: str = "system"
    metadata: Optional[Dict[str, Any]] = None


class DataLineageManager:
    """数据谱系管理器"""
    
    def __init__(self, config_manager: ConfigManager = None):
        """
        初始化数据谱系管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.db_manager = UnifiedDatabaseManager()
        self.lineage_cache = {}  # 谱系缓存
        self.impact_cache = {}   # 影响分析缓存
        
        # 配置参数
        self.cache_ttl = self.config_manager.get('lineage.cache_ttl', 3600)  # 缓存1小时
        self.auto_discover = self.config_manager.get('lineage.auto_discover', True)
        
        logger.info("数据谱系管理器初始化完成")
    
    def get_db_connection(self):
        """获取数据库连接"""
        import sqlite3
        from .database_path_manager import DatabasePathManager
        path_manager = DatabasePathManager()
        db_path = path_manager.get_main_db_path()
        return sqlite3.connect(db_path)
    
    def generate_node_id(self, system: str, table: str, field: str = None) -> str:
        """生成节点ID"""
        if field:
            return f"{system}.{table}.{field}"
        return f"{system}.{table}"
    
    def generate_relation_id(self, source_id: str, target_id: str) -> str:
        """生成关系ID"""
        return f"{source_id}→{target_id}_{uuid.uuid4().hex[:8]}"
    
    async def record_crawler_lineage(self, 
                                   source_name: str,
                                   source_url: str,
                                   target_table: str,
                                   field_mapping: Dict[str, str],
                                   crawler_type: str = "web_crawler") -> str:
        """
        记录爬虫数据血缘
        
        Args:
            source_name: 数据源名称（如"新浪财经"）
            source_url: 源URL
            target_table: 目标表名
            field_mapping: 字段映射关系 {"source_field": "target_field"}
            crawler_type: 爬虫类型
            
        Returns:
            血缘记录ID
        """
        try:
            # 创建源节点
            source_node = LineageNode(
                node_id=self.generate_node_id("external", source_name),
                node_type="source",
                system_name="external",
                table_name=source_name,
                description=f"外部数据源: {source_name}",
                metadata={
                    "source_url": source_url,
                    "crawler_type": crawler_type,
                    "discovery_time": datetime.now().isoformat()
                }
            )
            
            # 为每个字段映射创建血缘关系
            lineage_ids = []
            for source_field, target_field in field_mapping.items():
                # 创建目标节点
                target_node = LineageNode(
                    node_id=self.generate_node_id("newslook", target_table, target_field),
                    node_type="target",
                    system_name="newslook",
                    table_name=target_table,
                    field_name=target_field,
                    description=f"NewsLook数据库字段: {target_table}.{target_field}"
                )
                
                # 创建血缘关系
                relation = LineageRelation(
                    relation_id=self.generate_relation_id(source_node.node_id, target_node.node_id),
                    source_node=source_node,
                    target_node=target_node,
                    lineage_type=LineageType.CRAWLER_SOURCE,
                    transformation_rule=f"爬虫提取: {source_field} → {target_field}",
                    created_at=datetime.now(),
                    metadata={
                        "source_field": source_field,
                        "extraction_method": "web_scraping",
                        "data_quality_check": True
                    }
                )
                
                # 保存到数据库
                lineage_id = await self._save_lineage_relation(relation)
                lineage_ids.append(lineage_id)
            
            logger.info(f"记录爬虫血缘成功: {source_name} → {target_table}, 创建了{len(lineage_ids)}个血缘关系")
            return lineage_ids[0] if lineage_ids else None
            
        except Exception as e:
            logger.error(f"记录爬虫血缘失败: {str(e)}")
            raise
    
    async def record_transformation_lineage(self,
                                          source_table: str,
                                          target_table: str,
                                          transformation_type: str,
                                          transformation_rule: str,
                                          field_mappings: List[Dict[str, str]]) -> str:
        """
        记录数据转换血缘
        
        Args:
            source_table: 源表
            target_table: 目标表
            transformation_type: 转换类型（清洗/标准化/聚合等）
            transformation_rule: 转换规则描述
            field_mappings: 字段映射列表
            
        Returns:
            血缘记录ID
        """
        try:
            lineage_ids = []
            
            for mapping in field_mappings:
                source_field = mapping.get("source_field")
                target_field = mapping.get("target_field")
                transform_logic = mapping.get("transform_logic", "直接映射")
                
                # 创建源节点
                source_node = LineageNode(
                    node_id=self.generate_node_id("newslook", source_table, source_field),
                    node_type="source",
                    system_name="newslook",
                    table_name=source_table,
                    field_name=source_field
                )
                
                # 创建目标节点
                target_node = LineageNode(
                    node_id=self.generate_node_id("newslook", target_table, target_field),
                    node_type="target",
                    system_name="newslook",
                    table_name=target_table,
                    field_name=target_field
                )
                
                # 创建转换关系
                relation = LineageRelation(
                    relation_id=self.generate_relation_id(source_node.node_id, target_node.node_id),
                    source_node=source_node,
                    target_node=target_node,
                    lineage_type=LineageType.DATA_TRANSFORMATION,
                    transformation_rule=f"{transformation_type}: {transform_logic}",
                    created_at=datetime.now(),
                    metadata={
                        "transformation_type": transformation_type,
                        "transform_logic": transform_logic,
                        "overall_rule": transformation_rule
                    }
                )
                
                lineage_id = await self._save_lineage_relation(relation)
                lineage_ids.append(lineage_id)
            
            logger.info(f"记录转换血缘成功: {source_table} → {target_table}")
            return lineage_ids[0] if lineage_ids else None
            
        except Exception as e:
            logger.error(f"记录转换血缘失败: {str(e)}")
            raise
    
    async def record_api_access_lineage(self,
                                       api_endpoint: str,
                                       source_table: str,
                                       query_fields: List[str],
                                       client_info: Dict[str, Any]) -> str:
        """
        记录API访问血缘
        
        Args:
            api_endpoint: API端点
            source_table: 数据源表
            query_fields: 查询字段列表
            client_info: 客户端信息
            
        Returns:
            血缘记录ID
        """
        try:
            # 创建API节点
            api_node = LineageNode(
                node_id=self.generate_node_id("api", api_endpoint.replace("/", "_")),
                node_type="target",
                system_name="api",
                table_name=api_endpoint,
                description=f"API端点: {api_endpoint}",
                metadata={
                    "endpoint": api_endpoint,
                    "client_ip": client_info.get("client_ip"),
                    "user_agent": client_info.get("user_agent"),
                    "access_time": datetime.now().isoformat()
                }
            )
            
            lineage_ids = []
            for field in query_fields:
                # 创建数据源节点
                source_node = LineageNode(
                    node_id=self.generate_node_id("newslook", source_table, field),
                    node_type="source",
                    system_name="newslook",
                    table_name=source_table,
                    field_name=field
                )
                
                # 创建访问关系
                relation = LineageRelation(
                    relation_id=self.generate_relation_id(source_node.node_id, api_node.node_id),
                    source_node=source_node,
                    target_node=api_node,
                    lineage_type=LineageType.API_ACCESS,
                    transformation_rule=f"API数据访问: {field}",
                    created_at=datetime.now(),
                    metadata=client_info
                )
                
                lineage_id = await self._save_lineage_relation(relation)
                lineage_ids.append(lineage_id)
            
            logger.info(f"记录API访问血缘成功: {api_endpoint}")
            return lineage_ids[0] if lineage_ids else None
            
        except Exception as e:
            logger.error(f"记录API访问血缘失败: {str(e)}")
            raise
    
    async def _save_lineage_relation(self, relation: LineageRelation) -> str:
        """保存血缘关系到数据库"""
        try:
            # 使用同步数据库操作（SQLite）
            import sqlite3
            from .database_path_manager import DatabasePathManager
            path_manager = DatabasePathManager()
            db_path = path_manager.get_main_db_path()
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 保存血缘关系
                cursor.execute("""
                    INSERT OR REPLACE INTO data_lineage (
                        lineage_id, source_system, source_table, source_field,
                        target_system, target_table, target_field,
                        transformation_rule, transformation_type,
                        created_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    relation.relation_id,
                    relation.source_node.system_name,
                    relation.source_node.table_name,
                    relation.source_node.field_name,
                    relation.target_node.system_name,
                    relation.target_node.table_name,
                    relation.target_node.field_name,
                    relation.transformation_rule,
                    relation.lineage_type.value,
                    relation.created_by,
                    relation.created_at.isoformat()
                ))
                
                conn.commit()
                return relation.relation_id
                
        except Exception as e:
            logger.error(f"保存血缘关系失败: {str(e)}")
            raise
    
    async def get_lineage_by_table(self, table_name: str, direction: str = "both") -> Dict[str, Any]:
        """
        获取表的血缘关系
        
        Args:
            table_name: 表名
            direction: 方向 upstream/downstream/both
            
        Returns:
            血缘关系图
        """
        cache_key = f"lineage_{table_name}_{direction}"
        
        # 检查缓存
        if cache_key in self.lineage_cache:
            cache_data = self.lineage_cache[cache_key]
            if datetime.now() - cache_data["timestamp"] < timedelta(seconds=self.cache_ttl):
                return cache_data["data"]
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                lineage_graph = {
                    "table_name": table_name,
                    "direction": direction,
                    "upstream": [],
                    "downstream": [],
                    "generated_at": datetime.now().isoformat()
                }
                
                # 获取上游血缘（作为目标）
                if direction in ["upstream", "both"]:
                    cursor.execute("""
                        SELECT lineage_id, source_system, source_table, source_field,
                               transformation_rule, transformation_type, created_at
                        FROM data_lineage
                        WHERE target_table = ?
                        ORDER BY created_at DESC
                    """, (table_name,))
                    
                    upstream_rows = cursor.fetchall()
                    for row in upstream_rows:
                        lineage_graph["upstream"].append({
                            "lineage_id": row[0],
                            "source_system": row[1],
                            "source_table": row[2],
                            "source_field": row[3],
                            "transformation_rule": row[4],
                            "transformation_type": row[5],
                            "created_at": row[6]
                        })
                
                # 获取下游血缘（作为源）
                if direction in ["downstream", "both"]:
                    cursor.execute("""
                        SELECT lineage_id, target_system, target_table, target_field,
                               transformation_rule, transformation_type, created_at
                        FROM data_lineage
                        WHERE source_table = ?
                        ORDER BY created_at DESC
                    """, (table_name,))
                    
                    downstream_rows = cursor.fetchall()
                    for row in downstream_rows:
                        lineage_graph["downstream"].append({
                            "lineage_id": row[0],
                            "target_system": row[1],
                            "target_table": row[2],
                            "target_field": row[3],
                            "transformation_rule": row[4],
                            "transformation_type": row[5],
                            "created_at": row[6]
                        })
                
                # 更新缓存
                self.lineage_cache[cache_key] = {
                    "data": lineage_graph,
                    "timestamp": datetime.now()
                }
                
                return lineage_graph
                
        except Exception as e:
            logger.error(f"获取表血缘关系失败 {table_name}: {str(e)}")
            raise
    
    async def analyze_impact(self, 
                           table_name: str, 
                           field_name: str = None,
                           max_depth: int = 5) -> Dict[str, Any]:
        """
        影响分析：分析字段/表变更的下游影响
        
        Args:
            table_name: 表名
            field_name: 字段名（可选）
            max_depth: 最大分析深度
            
        Returns:
            影响分析结果
        """
        cache_key = f"impact_{table_name}_{field_name}_{max_depth}"
        
        # 检查缓存
        if cache_key in self.impact_cache:
            cache_data = self.impact_cache[cache_key]
            if datetime.now() - cache_data["timestamp"] < timedelta(seconds=self.cache_ttl):
                return cache_data["data"]
        
        try:
            impact_result = {
                "source_table": table_name,
                "source_field": field_name,
                "max_depth": max_depth,
                "impact_tree": [],
                "affected_systems": set(),
                "affected_tables": set(),
                "total_affected_count": 0,
                "analysis_time": datetime.now().isoformat()
            }
            
            # 递归分析下游影响
            visited = set()
            await self._analyze_downstream_impact(
                table_name, field_name, 0, max_depth, 
                impact_result, visited
            )
            
            # 转换set为list（JSON序列化）
            impact_result["affected_systems"] = list(impact_result["affected_systems"])
            impact_result["affected_tables"] = list(impact_result["affected_tables"])
            
            # 更新缓存
            self.impact_cache[cache_key] = {
                "data": impact_result,
                "timestamp": datetime.now()
            }
            
            logger.info(f"影响分析完成: {table_name}.{field_name}, 影响{impact_result['total_affected_count']}个对象")
            return impact_result
            
        except Exception as e:
            logger.error(f"影响分析失败 {table_name}.{field_name}: {str(e)}")
            raise
    
    async def _analyze_downstream_impact(self,
                                       table_name: str,
                                       field_name: str,
                                       current_depth: int,
                                       max_depth: int,
                                       result: Dict[str, Any],
                                       visited: Set[str]):
        """递归分析下游影响"""
        if current_depth >= max_depth:
            return
        
        node_key = f"{table_name}.{field_name}" if field_name else table_name
        if node_key in visited:
            return
        visited.add(node_key)
        
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 查询下游影响
            if field_name:
                cursor.execute("""
                    SELECT target_system, target_table, target_field,
                           transformation_rule, transformation_type, lineage_id
                    FROM data_lineage
                    WHERE source_table = ? AND source_field = ?
                """, (table_name, field_name))
            else:
                cursor.execute("""
                    SELECT target_system, target_table, target_field,
                           transformation_rule, transformation_type, lineage_id
                    FROM data_lineage
                    WHERE source_table = ?
                """, (table_name,))
            
            downstream_rows = cursor.fetchall()
            
            for row in downstream_rows:
                target_system, target_table, target_field, transform_rule, transform_type, lineage_id = row
                
                # 添加到影响树
                impact_node = {
                    "depth": current_depth + 1,
                    "lineage_id": lineage_id,
                    "target_system": target_system,
                    "target_table": target_table,
                    "target_field": target_field,
                    "transformation_rule": transform_rule,
                    "transformation_type": transform_type,
                    "children": []
                }
                
                result["impact_tree"].append(impact_node)
                result["affected_systems"].add(target_system)
                result["affected_tables"].add(target_table)
                result["total_affected_count"] += 1
                
                # 递归分析下游
                await self._analyze_downstream_impact(
                    target_table, target_field, current_depth + 1, max_depth,
                    result, visited
                )
    
    async def generate_lineage_report(self, 
                                    table_filter: List[str] = None,
                                    system_filter: List[str] = None,
                                    date_range: Tuple[datetime, datetime] = None) -> Dict[str, Any]:
        """
        生成数据谱系报告
        
        Args:
            table_filter: 表名过滤器
            system_filter: 系统过滤器
            date_range: 日期范围过滤器
            
        Returns:
            谱系报告
        """
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 构建查询条件
                where_conditions = []
                params = []
                
                if table_filter:
                    placeholders = ','.join('?' * len(table_filter))
                    where_conditions.append(f"(source_table IN ({placeholders}) OR target_table IN ({placeholders}))")
                    params.extend(table_filter * 2)
                
                if system_filter:
                    placeholders = ','.join('?' * len(system_filter))
                    where_conditions.append(f"(source_system IN ({placeholders}) OR target_system IN ({placeholders}))")
                    params.extend(system_filter * 2)
                
                if date_range:
                    where_conditions.append("created_at BETWEEN ? AND ?")
                    params.extend([date_range[0].isoformat(), date_range[1].isoformat()])
                
                where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
                
                # 获取血缘统计
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_lineage,
                        COUNT(DISTINCT source_system) as source_systems,
                        COUNT(DISTINCT target_system) as target_systems,
                        COUNT(DISTINCT source_table) as source_tables,
                        COUNT(DISTINCT target_table) as target_tables,
                        COUNT(DISTINCT transformation_type) as transformation_types
                    FROM data_lineage
                    {where_clause}
                """, params)
                
                stats_row = cursor.fetchone()
                statistics = {
                    "total_lineage_relations": stats_row[0],
                    "unique_source_systems": stats_row[1],
                    "unique_target_systems": stats_row[2],
                    "unique_source_tables": stats_row[3],
                    "unique_target_tables": stats_row[4],
                    "transformation_types_count": stats_row[5]
                }
                
                # 获取系统级别统计
                cursor.execute(f"""
                    SELECT transformation_type, COUNT(*) as count
                    FROM data_lineage
                    {where_clause}
                    GROUP BY transformation_type
                    ORDER BY count DESC
                """, params)
                
                transformation_stats = {}
                for row in cursor:
                    transformation_stats[row[0]] = row[1]
                
                # 获取最活跃的表
                cursor.execute(f"""
                    SELECT table_name, relation_count
                    FROM (
                        SELECT source_table as table_name, COUNT(*) as relation_count
                        FROM data_lineage {where_clause}
                        GROUP BY source_table
                        UNION ALL
                        SELECT target_table as table_name, COUNT(*) as relation_count
                        FROM data_lineage {where_clause}
                        GROUP BY target_table
                    )
                    GROUP BY table_name
                    ORDER BY SUM(relation_count) DESC
                    LIMIT 10
                """, params * 2 if params else [])
                
                active_tables = []
                for row in cursor:
                    active_tables.append({
                        "table_name": row[0],
                        "total_relations": row[1]
                    })
                
                report = {
                    "report_metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "filters": {
                            "tables": table_filter,
                            "systems": system_filter,
                            "date_range": [d.isoformat() for d in date_range] if date_range else None
                        }
                    },
                    "statistics": statistics,
                    "transformation_analysis": transformation_stats,
                    "most_active_tables": active_tables
                }
                
                logger.info(f"生成血缘报告成功: {statistics['total_lineage_relations']}个血缘关系")
                return report
                
        except Exception as e:
            logger.error(f"生成血缘报告失败: {str(e)}")
            raise
    
    async def cleanup_old_lineage(self, retention_days: int = 365):
        """清理旧的血缘记录"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM data_lineage
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"清理旧血缘记录完成: 删除了{deleted_count}条记录")
                
                # 清理缓存
                self.lineage_cache.clear()
                self.impact_cache.clear()
                
        except Exception as e:
            logger.error(f"清理旧血缘记录失败: {str(e)}")
            raise
    
    def clear_cache(self):
        """清理缓存"""
        self.lineage_cache.clear()
        self.impact_cache.clear()
        logger.info("数据谱系缓存已清理")


# 全局实例
_lineage_manager_instance = None

def get_lineage_manager() -> DataLineageManager:
    """获取数据谱系管理器单例"""
    global _lineage_manager_instance
    if _lineage_manager_instance is None:
        _lineage_manager_instance = DataLineageManager()
    return _lineage_manager_instance 