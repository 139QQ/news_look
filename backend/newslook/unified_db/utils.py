#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 统一数据库工具模块
提供全局ID生成、数据分层管理、元数据采集等工具功能
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

def generate_global_id(source_code: str, entity_type: str, content: str) -> str:
    """
    生成全局唯一ID
    格式: <源编码>_<业务实体>_<内容哈希>
    
    Args:
        source_code: 数据源编码 (如: TENCENT, SINA, EASTMONEY)
        entity_type: 业务实体类型 (如: NEWS, KEYWORD, STOCK)
        content: 用于生成哈希的内容 (如: URL, 标题+时间)
    
    Returns:
        全局唯一ID字符串
    
    Examples:
        TENCENT_NEWS_a1b2c3d4e5f6
        SINA_STOCK_f6e5d4c3b2a1
        EASTMONEY_KEYWORD_9876543210ab
    """
    # 标准化参数
    source_code = source_code.upper().replace(' ', '_')
    entity_type = entity_type.upper().replace(' ', '_')
    
    # 生成内容哈希
    content_bytes = content.encode('utf-8')
    content_hash = hashlib.md5(content_bytes).hexdigest()[:12]
    
    return f"{source_code}_{entity_type}_{content_hash}"


def generate_uuid() -> str:
    """生成UUID"""
    return str(uuid.uuid4())


def generate_batch_id() -> str:
    """生成数据批次ID"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_suffix = uuid.uuid4().hex[:8]
    return f"BATCH_{timestamp}_{random_suffix}"


class DataTierManager:
    """数据分层管理器"""
    
    def __init__(self, db_configs: Dict[str, str]):
        """
        初始化数据分层管理器
        
        Args:
            db_configs: 数据库配置 {'hot': 'postgresql://...', 'warm': 'clickhouse://...', 'cold': 's3://...'}
        """
        self.db_configs = db_configs
        self.engines = {}
        
        # 初始化数据库引擎
        for tier, config in db_configs.items():
            if tier in ['hot', 'warm']:
                self.engines[tier] = create_engine(config)
    
    def get_data_tier(self, pub_time: datetime) -> str:
        """
        根据发布时间确定数据层级
        
        Args:
            pub_time: 发布时间
            
        Returns:
            数据层级: hot/warm/cold
        """
        now = datetime.now()
        
        if pub_time >= now - timedelta(days=7):
            return 'hot'
        elif pub_time >= now - timedelta(days=90):
            return 'warm'
        else:
            return 'cold'
    
    def should_migrate_to_warm(self, pub_time: datetime) -> bool:
        """判断是否应该迁移到温数据层"""
        return pub_time < datetime.now() - timedelta(days=7)
    
    def should_migrate_to_cold(self, pub_time: datetime) -> bool:
        """判断是否应该迁移到冷数据层"""
        return pub_time < datetime.now() - timedelta(days=90)
    
    async def migrate_data(self, source_tier: str, target_tier: str, records: List[Dict[str, Any]]):
        """
        数据迁移
        
        Args:
            source_tier: 源数据层级
            target_tier: 目标数据层级
            records: 要迁移的记录
        """
        try:
            if target_tier == 'warm':
                await self._migrate_to_warm(records)
            elif target_tier == 'cold':
                await self._migrate_to_cold(records)
            
            # 从源层级删除数据
            await self._delete_from_tier(source_tier, records)
            
            logger.info(f"成功迁移 {len(records)} 条记录从 {source_tier} 到 {target_tier}")
            
        except Exception as e:
            logger.error(f"数据迁移失败: {e}")
            raise
    
    async def _migrate_to_warm(self, records: List[Dict[str, Any]]):
        """迁移到温数据层(ClickHouse)"""
        if 'warm' not in self.engines:
            logger.warning("温数据层引擎未配置")
            return
        
        # 构建ClickHouse插入语句
        insert_sql = """
        INSERT INTO news_warm (
            global_id, source_id, title, content, pub_time, 
            category, sentiment_score, created_at
        ) VALUES
        """
        
        values = []
        for record in records:
            values.append(f"('{record['global_id']}', '{record['source_id']}', "
                         f"'{record['title']}', '{record['content']}', "
                         f"'{record['pub_time']}', '{record['category']}', "
                         f"{record.get('sentiment_score', 0)}, '{record['created_at']}')")
        
        full_sql = insert_sql + ', '.join(values)
        
        with self.engines['warm'].connect() as conn:
            conn.execute(text(full_sql))
            conn.commit()
    
    async def _migrate_to_cold(self, records: List[Dict[str, Any]]):
        """迁移到冷数据层(S3)"""
        # 实现S3存储逻辑
        import boto3
        import gzip
        
        s3_client = boto3.client('s3')
        bucket = self.db_configs.get('cold_bucket', 'newslook-cold-data')
        
        for record in records:
            # 生成S3 key
            pub_date = record['pub_time'].strftime('%Y/%m/%d')
            s3_key = f"news/{pub_date}/{record['global_id']}.json.gz"
            
            # 压缩数据
            data_json = json.dumps(record, ensure_ascii=False, default=str)
            compressed_data = gzip.compress(data_json.encode('utf-8'))
            
            # 上传到S3
            s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=compressed_data,
                ContentType='application/json',
                ContentEncoding='gzip'
            )
            
            # 更新冷数据索引
            await self._update_cold_index(record['global_id'], bucket, s3_key)
    
    async def _update_cold_index(self, global_id: str, bucket: str, s3_key: str):
        """更新冷数据索引"""
        with self.engines['hot'].connect() as conn:
            conn.execute(text("""
                INSERT INTO news_cold_index (
                    global_id, s3_bucket, s3_key, compression_type, archived_at
                ) VALUES (
                    :global_id, :bucket, :s3_key, 'gzip', NOW()
                )
            """), {
                'global_id': global_id,
                'bucket': bucket,
                's3_key': s3_key
            })
            conn.commit()
    
    async def _delete_from_tier(self, tier: str, records: List[Dict[str, Any]]):
        """从指定层级删除数据"""
        if tier not in self.engines:
            return
        
        global_ids = [record['global_id'] for record in records]
        placeholders = ', '.join([f"'{gid}'" for gid in global_ids])
        
        delete_sql = f"DELETE FROM news_unified WHERE global_id IN ({placeholders})"
        
        with self.engines[tier].connect() as conn:
            conn.execute(text(delete_sql))
            conn.commit()


class MetadataCollector:
    """元数据采集器"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def collect_table_metadata(self, table_name: str) -> Dict[str, Any]:
        """
        采集表元数据
        
        Args:
            table_name: 表名
            
        Returns:
            表元数据信息
        """
        metadata = {
            'table_name': table_name,
            'collected_at': datetime.now(),
            'columns': [],
            'indexes': [],
            'constraints': [],
            'row_count': 0,
            'data_size': 0
        }
        
        try:
            # 获取列信息
            columns_query = text(f"""
                SELECT column_name, data_type, is_nullable, column_default, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            
            result = self.db_session.execute(columns_query)
            for row in result:
                metadata['columns'].append({
                    'name': row.column_name,
                    'type': row.data_type,
                    'nullable': row.is_nullable == 'YES',
                    'default': row.column_default,
                    'max_length': row.character_maximum_length
                })
            
            # 获取索引信息
            indexes_query = text(f"""
                SELECT indexname, indexdef
                FROM pg_indexes 
                WHERE tablename = '{table_name}'
            """)
            
            result = self.db_session.execute(indexes_query)
            for row in result:
                metadata['indexes'].append({
                    'name': row.indexname,
                    'definition': row.indexdef
                })
            
            # 获取行数
            count_query = text(f"SELECT COUNT(*) as row_count FROM {table_name}")
            result = self.db_session.execute(count_query)
            metadata['row_count'] = result.scalar()
            
            # 获取表大小
            size_query = text(f"""
                SELECT pg_total_relation_size('{table_name}') as table_size
            """)
            result = self.db_session.execute(size_query)
            metadata['data_size'] = result.scalar()
            
        except Exception as e:
            logger.error(f"采集表 {table_name} 元数据失败: {e}")
            metadata['error'] = str(e)
        
        return metadata
    
    def collect_data_lineage(self, source_table: str, target_table: str, 
                           transformation_rule: str) -> Dict[str, Any]:
        """
        记录数据血缘信息
        
        Args:
            source_table: 源表
            target_table: 目标表
            transformation_rule: 转换规则
            
        Returns:
            血缘信息
        """
        lineage = {
            'lineage_id': generate_uuid(),
            'source_system': 'NewsLook',
            'source_table': source_table,
            'target_system': 'NewsLook',
            'target_table': target_table,
            'transformation_rule': transformation_rule,
            'transformation_type': 'ETL',
            'created_by': 'system',
            'created_at': datetime.now()
        }
        
        return lineage


class DataQualityMonitor:
    """数据质量监控器"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def check_null_values(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """检查空值"""
        query = text(f"""
            SELECT 
                COUNT(*) as total_count,
                COUNT({column_name}) as non_null_count,
                COUNT(*) - COUNT({column_name}) as null_count
            FROM {table_name}
        """)
        
        result = self.db_session.execute(query).fetchone()
        
        return {
            'table_name': table_name,
            'column_name': column_name,
            'total_count': result.total_count,
            'non_null_count': result.non_null_count,
            'null_count': result.null_count,
            'null_rate': result.null_count / result.total_count if result.total_count > 0 else 0
        }
    
    def check_duplicates(self, table_name: str, column_names: List[str]) -> Dict[str, Any]:
        """检查重复值"""
        columns_str = ', '.join(column_names)
        query = text(f"""
            SELECT 
                COUNT(*) as total_count,
                COUNT(DISTINCT ({columns_str})) as unique_count
            FROM {table_name}
        """)
        
        result = self.db_session.execute(query).fetchone()
        duplicate_count = result.total_count - result.unique_count
        
        return {
            'table_name': table_name,
            'columns': column_names,
            'total_count': result.total_count,
            'unique_count': result.unique_count,
            'duplicate_count': duplicate_count,
            'duplicate_rate': duplicate_count / result.total_count if result.total_count > 0 else 0
        }
    
    def check_data_freshness(self, table_name: str, time_column: str, 
                           expected_interval_minutes: int = 60) -> Dict[str, Any]:
        """检查数据新鲜度"""
        query = text(f"""
            SELECT 
                MAX({time_column}) as latest_time,
                NOW() - MAX({time_column}) as time_diff
            FROM {table_name}
        """)
        
        result = self.db_session.execute(query).fetchone()
        
        if result.latest_time:
            time_diff_minutes = result.time_diff.total_seconds() / 60
            is_fresh = time_diff_minutes <= expected_interval_minutes
        else:
            time_diff_minutes = float('inf')
            is_fresh = False
        
        return {
            'table_name': table_name,
            'time_column': time_column,
            'latest_time': result.latest_time,
            'time_diff_minutes': time_diff_minutes,
            'expected_interval_minutes': expected_interval_minutes,
            'is_fresh': is_fresh
        }


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or 'configs/unified_db.yaml'
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        import yaml
        import os
        
        if not os.path.exists(self.config_path):
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'databases': {
                'hot': {
                    'type': 'postgresql',
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'newslook_hot',
                    'username': 'newslook',
                    'password': 'password'
                },
                'warm': {
                    'type': 'clickhouse',
                    'host': 'localhost',
                    'port': 8123,
                    'database': 'newslook_warm',
                    'username': 'default',
                    'password': ''
                },
                'cold': {
                    'type': 's3',
                    'bucket': 'newslook-cold-data',
                    'region': 'us-east-1'
                }
            },
            'data_tiers': {
                'hot_retention_days': 7,
                'warm_retention_days': 90
            },
            'quality_rules': {
                'enable_auto_check': True,
                'check_interval_minutes': 60,
                'alert_threshold': 0.1
            },
            'security': {
                'enable_encryption': True,
                'enable_audit_log': True,
                'session_timeout_minutes': 60
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self):
        """保存配置到文件"""
        import yaml
        import os
        
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True) 