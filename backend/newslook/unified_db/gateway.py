#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 统一访问网关模块
提供统一的数据查询和访问控制功能
"""

import jwt
import fnmatch
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class UnifiedQueryGateway:
    """统一查询网关"""
    
    def __init__(self, db_configs: Dict[str, str]):
        """
        初始化查询网关
        
        Args:
            db_configs: 数据库配置 {'hot': 'postgresql://...', 'warm': 'clickhouse://...'}
        """
        self.db_configs = db_configs
        self.engines = {}
        
        # 初始化数据库引擎
        for tier, config in db_configs.items():
            if tier in ['hot', 'warm']:
                try:
                    self.engines[tier] = create_engine(config)
                    logger.info(f"初始化 {tier} 数据库引擎成功")
                except Exception as e:
                    logger.error(f"初始化 {tier} 数据库引擎失败: {e}")
        
        # 查询缓存
        self.query_cache = {}
        self.cache_ttl = 300  # 5分钟
    
    async def execute_query(self, query: str, params: Dict[str, Any] = None, 
                           target_tier: str = None) -> List[Dict[str, Any]]:
        """
        执行统一查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            target_tier: 目标数据层级，如果不指定则自动分析
            
        Returns:
            查询结果列表
        """
        try:
            # 确定查询目标层级
            if not target_tier:
                target_tier = self._analyze_query_tier(query)
            
            # 检查缓存
            cache_key = self._get_cache_key(query, params, target_tier)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.debug(f"从缓存返回查询结果: {cache_key}")
                return cached_result
            
            # 执行查询
            if target_tier in ['hot', 'warm']:
                result = await self._execute_db_query(target_tier, query, params)
            elif target_tier == 'cold':
                result = await self._query_cold_data(query, params)
            else:
                # 跨层查询，需要联邦查询
                result = await self._federated_query(query, params)
            
            # 缓存结果
            self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise HTTPException(status_code=500, detail=f"查询执行失败: {str(e)}")
    
    def _analyze_query_tier(self, query: str) -> str:
        """
        分析查询应该在哪个存储层执行
        
        Args:
            query: SQL查询语句
            
        Returns:
            数据层级: hot/warm/cold/federated
        """
        query_lower = query.lower()
        
        # 简单的启发式规则
        if 'news_unified' in query_lower:
            # 分析时间条件
            if 'pub_time' in query_lower:
                if '7 day' in query_lower or 'interval \'7 day\'' in query_lower:
                    return 'hot'
                elif '90 day' in query_lower or 'interval \'90 day\'' in query_lower:
                    return 'warm'
                elif 'where' in query_lower and ('>' in query_lower or '<' in query_lower):
                    # 有具体的时间条件，需要进一步分析
                    return 'hot'  # 默认使用热数据
            else:
                # 没有时间条件的查询，使用热数据
                return 'hot'
        
        # 分析聚合查询
        if any(keyword in query_lower for keyword in ['count(', 'sum(', 'avg(', 'group by']):
            return 'warm'  # 聚合查询使用温数据层
        
        # 默认使用热数据
        return 'hot'
    
    async def _execute_db_query(self, tier: str, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行数据库查询"""
        if tier not in self.engines:
            raise ValueError(f"数据库层级 {tier} 未配置")
        
        engine = self.engines[tier]
        params = params or {}
        
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            return [dict(row) for row in result]
    
    async def _query_cold_data(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查询冷数据"""
        # 实现S3查询逻辑
        # 这里是简化实现，实际应该解析查询条件，从S3获取对应数据
        logger.warning("冷数据查询功能尚未完全实现")
        return []
    
    async def _federated_query(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """联邦查询"""
        # 使用Trino/Presto进行跨存储查询
        # 这里是简化实现，实际需要配置联邦查询引擎
        logger.warning("联邦查询功能尚未完全实现")
        
        # 简单实现：尝试从热数据查询
        try:
            return await self._execute_db_query('hot', query, params)
        except Exception as e:
            logger.error(f"联邦查询失败: {e}")
            return []
    
    def _get_cache_key(self, query: str, params: Dict[str, Any], tier: str) -> str:
        """生成缓存键"""
        import hashlib
        cache_content = f"{query}_{str(params)}_{tier}"
        return hashlib.md5(cache_content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """从缓存获取结果"""
        if cache_key in self.query_cache:
            cached_item = self.query_cache[cache_key]
            if datetime.now() - cached_item['timestamp'] < timedelta(seconds=self.cache_ttl):
                return cached_item['data']
            else:
                # 缓存过期，删除
                del self.query_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: List[Dict[str, Any]]):
        """缓存查询结果"""
        self.query_cache[cache_key] = {
            'data': result,
            'timestamp': datetime.now()
        }
        
        # 简单的缓存清理：如果缓存项太多，清理最老的
        if len(self.query_cache) > 1000:
            oldest_key = min(self.query_cache.keys(), 
                           key=lambda k: self.query_cache[k]['timestamp'])
            del self.query_cache[oldest_key]
    
    def clear_cache(self):
        """清理缓存"""
        self.query_cache.clear()
        logger.info("查询缓存已清理")
    
    async def get_table_schema(self, table_name: str, tier: str = 'hot') -> Dict[str, Any]:
        """
        获取表结构信息
        
        Args:
            table_name: 表名
            tier: 数据层级
            
        Returns:
            表结构信息
        """
        try:
            schema_query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = :table_name
                ORDER BY ordinal_position
            """
            
            result = await self._execute_db_query(tier, schema_query, {'table_name': table_name})
            
            return {
                'table_name': table_name,
                'tier': tier,
                'columns': result,
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取表结构失败: {e}")
            raise HTTPException(status_code=500, detail=f"获取表结构失败: {str(e)}")
    
    async def execute_aggregation_query(self, table: str, aggregations: List[Dict[str, Any]], 
                                      filters: List[Dict[str, Any]] = None,
                                      group_by: List[str] = None) -> List[Dict[str, Any]]:
        """
        执行聚合查询
        
        Args:
            table: 表名
            aggregations: 聚合函数列表 [{'function': 'count', 'field': '*', 'alias': 'total'}]
            filters: 过滤条件列表 [{'field': 'category', 'operator': '=', 'value': 'finance'}]
            group_by: 分组字段列表
            
        Returns:
            聚合查询结果
        """
        try:
            # 构建SELECT子句
            select_parts = []
            for agg in aggregations:
                func = agg.get('function', 'count').upper()
                field = agg.get('field', '*')
                alias = agg.get('alias', f"{func.lower()}_{field}")
                select_parts.append(f"{func}({field}) AS {alias}")
            
            if group_by:
                select_parts.extend(group_by)
            
            select_clause = ', '.join(select_parts)
            
            # 构建WHERE子句
            where_clause = ""
            params = {}
            if filters:
                where_conditions = []
                for i, filter_item in enumerate(filters):
                    field = filter_item['field']
                    operator = filter_item.get('operator', '=')
                    value = filter_item['value']
                    param_name = f"param_{i}"
                    
                    where_conditions.append(f"{field} {operator} :{param_name}")
                    params[param_name] = value
                
                where_clause = f"WHERE {' AND '.join(where_conditions)}"
            
            # 构建GROUP BY子句
            group_clause = ""
            if group_by:
                group_clause = f"GROUP BY {', '.join(group_by)}"
            
            # 组合完整查询
            query = f"SELECT {select_clause} FROM {table} {where_clause} {group_clause}"
            
            # 聚合查询通常使用温数据层
            return await self.execute_query(query, params, 'warm')
            
        except Exception as e:
            logger.error(f"聚合查询失败: {e}")
            raise HTTPException(status_code=500, detail=f"聚合查询失败: {str(e)}")


class DataAccessController:
    """数据访问控制器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.jwt_secret = "your-secret-key"  # 实际应该从配置文件读取
        self.jwt_algorithm = "HS256"
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            认证结果和用户信息
        """
        try:
            from .models import UserAccount
            import hashlib
            
            # 查询用户
            user = self.db.query(UserAccount).filter(
                UserAccount.username == username,
                UserAccount.is_active == True
            ).first()
            
            if not user:
                raise HTTPException(status_code=401, detail="用户不存在或已禁用")
            
            # 验证密码（实际应该使用更安全的密码哈希算法）
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if user.password_hash != password_hash:
                raise HTTPException(status_code=401, detail="密码错误")
            
            # 更新最后登录时间
            user.last_login = datetime.now()
            self.db.commit()
            
            # 生成JWT令牌
            token_payload = {
                'user_id': user.user_id,
                'username': user.username,
                'role': user.role,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }
            
            token = jwt.encode(token_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            return {
                'user_id': user.user_id,
                'username': user.username,
                'role': user.role,
                'permissions': user.permissions,
                'token': token
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            raise HTTPException(status_code=500, detail="认证服务异常")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            解码后的用户信息
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="令牌已过期")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="无效令牌")
    
    def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """
        检查用户权限
        
        Args:
            user_id: 用户ID
            resource: 资源标识
            action: 操作类型
            
        Returns:
            是否有权限
        """
        try:
            from .models import UserDataAccess, DataAccessPolicy
            
            # 查询用户权限策略
            user_policies = self.db.query(UserDataAccess).join(DataAccessPolicy).filter(
                UserDataAccess.user_id == user_id,
                DataAccessPolicy.is_active == True
            ).all()
            
            for access in user_policies:
                policy = access.policy
                
                # 检查资源模式匹配
                if self._match_resource_pattern(policy.resource_pattern, resource):
                    # 检查权限类型
                    if action in policy.permission_type.split(','):
                        # 检查访问条件
                        if self._check_access_conditions(policy.conditions, user_id):
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"权限检查失败: {e}")
            return False
    
    def _match_resource_pattern(self, pattern: str, resource: str) -> bool:
        """匹配资源模式"""
        return fnmatch.fnmatch(resource, pattern)
    
    def _check_access_conditions(self, conditions: Dict[str, Any], user_id: str) -> bool:
        """检查访问条件"""
        if not conditions:
            return True
        
        # 检查时间条件
        if 'time_range' in conditions:
            time_range = conditions['time_range']
            current_hour = datetime.now().hour
            
            start_hour = time_range.get('start_hour', 0)
            end_hour = time_range.get('end_hour', 23)
            
            if not (start_hour <= current_hour <= end_hour):
                return False
        
        # 检查IP条件
        if 'allowed_ips' in conditions:
            # 这里需要从请求中获取IP地址
            # 简化实现，实际应该从FastAPI的Request对象获取
            pass
        
        return True
    
    def filter_by_permission(self, query_params: Dict[str, Any], user_id: str, 
                           table_name: str) -> Dict[str, Any]:
        """
        根据权限过滤查询参数
        
        Args:
            query_params: 原始查询参数
            user_id: 用户ID
            table_name: 表名
            
        Returns:
            过滤后的查询参数
        """
        try:
            from .models import UserDataAccess, DataAccessPolicy
            
            # 获取用户的数据访问条件
            access_conditions = self._get_user_access_conditions(user_id, table_name)
            
            filtered_params = query_params.copy()
            
            # 应用时间范围限制
            for condition in access_conditions:
                if condition['type'] == 'time_range':
                    start_date = condition.get('start_date')
                    end_date = condition.get('end_date')
                    
                    if start_date:
                        filtered_params['pub_time_gte'] = start_date
                    if end_date:
                        filtered_params['pub_time_lte'] = end_date
                
                elif condition['type'] == 'source_filter':
                    allowed_sources = condition.get('allowed_sources', [])
                    if allowed_sources:
                        filtered_params['source_id_in'] = allowed_sources
                
                elif condition['type'] == 'category_filter':
                    allowed_categories = condition.get('allowed_categories', [])
                    if allowed_categories:
                        filtered_params['category_in'] = allowed_categories
            
            return filtered_params
            
        except Exception as e:
            logger.error(f"权限过滤失败: {e}")
            return query_params
    
    def _get_user_access_conditions(self, user_id: str, table_name: str) -> List[Dict[str, Any]]:
        """获取用户的数据访问条件"""
        try:
            from .models import UserDataAccess, DataAccessPolicy
            import json
            
            conditions = []
            
            user_policies = self.db.query(UserDataAccess).join(DataAccessPolicy).filter(
                UserDataAccess.user_id == user_id,
                DataAccessPolicy.resource_pattern.like(f'%{table_name}%')
            ).all()
            
            for access in user_policies:
                policy_conditions = access.policy.conditions
                if policy_conditions:
                    if isinstance(policy_conditions, str):
                        policy_conditions = json.loads(policy_conditions)
                    conditions.extend(policy_conditions)
            
            return conditions
            
        except Exception as e:
            logger.error(f"获取用户访问条件失败: {e}")
            return []


def require_permission(resource: str, action: str):
    """权限装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从请求中获取用户信息
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="未认证")
            
            user_id = current_user.get('user_id')
            if not user_id:
                raise HTTPException(status_code=401, detail="无效用户信息")
            
            # 这里需要获取数据库会话
            db_session = kwargs.get('db_session')
            if not db_session:
                raise HTTPException(status_code=500, detail="数据库会话不可用")
            
            # 检查权限
            access_controller = DataAccessController(db_session)
            if not access_controller.check_permission(user_id, resource, action):
                raise HTTPException(status_code=403, detail="权限不足")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user(token: str, db_session: Session) -> Dict[str, Any]:
    """获取当前用户信息"""
    access_controller = DataAccessController(db_session)
    return access_controller.verify_token(token)


class QueryBuilder:
    """查询构建器"""
    
    def __init__(self, table: str):
        self.table = table
        self.select_fields = []
        self.where_conditions = []
        self.join_clauses = []
        self.order_by_fields = []
        self.group_by_fields = []
        self.having_conditions = []
        self.limit_count = None
        self.offset_count = 0
        self.params = {}
    
    def select(self, *fields: str):
        """选择字段"""
        self.select_fields.extend(fields)
        return self
    
    def where(self, condition: str, **params):
        """添加WHERE条件"""
        self.where_conditions.append(condition)
        self.params.update(params)
        return self
    
    def join(self, table: str, on_condition: str, join_type: str = 'INNER'):
        """添加JOIN"""
        self.join_clauses.append(f"{join_type} JOIN {table} ON {on_condition}")
        return self
    
    def order_by(self, field: str, direction: str = 'ASC'):
        """添加排序"""
        self.order_by_fields.append(f"{field} {direction}")
        return self
    
    def group_by(self, *fields: str):
        """添加分组"""
        self.group_by_fields.extend(fields)
        return self
    
    def having(self, condition: str):
        """添加HAVING条件"""
        self.having_conditions.append(condition)
        return self
    
    def limit(self, count: int):
        """设置LIMIT"""
        self.limit_count = count
        return self
    
    def offset(self, count: int):
        """设置OFFSET"""
        self.offset_count = count
        return self
    
    def build(self) -> tuple[str, Dict[str, Any]]:
        """构建SQL查询"""
        # SELECT子句
        if self.select_fields:
            select_clause = f"SELECT {', '.join(self.select_fields)}"
        else:
            select_clause = "SELECT *"
        
        # FROM子句
        from_clause = f"FROM {self.table}"
        
        # JOIN子句
        join_clause = ' '.join(self.join_clauses) if self.join_clauses else ""
        
        # WHERE子句
        where_clause = ""
        if self.where_conditions:
            where_clause = f"WHERE {' AND '.join(self.where_conditions)}"
        
        # GROUP BY子句
        group_clause = ""
        if self.group_by_fields:
            group_clause = f"GROUP BY {', '.join(self.group_by_fields)}"
        
        # HAVING子句
        having_clause = ""
        if self.having_conditions:
            having_clause = f"HAVING {' AND '.join(self.having_conditions)}"
        
        # ORDER BY子句
        order_clause = ""
        if self.order_by_fields:
            order_clause = f"ORDER BY {', '.join(self.order_by_fields)}"
        
        # LIMIT和OFFSET子句
        limit_clause = ""
        if self.limit_count is not None:
            limit_clause = f"LIMIT {self.limit_count}"
            if self.offset_count > 0:
                limit_clause += f" OFFSET {self.offset_count}"
        
        # 组合完整查询
        query_parts = [
            select_clause,
            from_clause,
            join_clause,
            where_clause,
            group_clause,
            having_clause,
            order_clause,
            limit_clause
        ]
        
        query = ' '.join(part for part in query_parts if part)
        
        return query, self.params 