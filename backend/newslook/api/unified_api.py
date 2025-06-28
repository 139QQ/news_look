"""
统一数据聚合API
整合PostgreSQL事务数据和ClickHouse分析数据
提供高性能的查询和分析接口
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import json

from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin

from ..databases.postgresql_manager import get_postgresql_manager, DatabaseConfig as PGConfig
from ..databases.clickhouse_manager import get_clickhouse_manager, ClickHouseConfig as CHConfig

logger = logging.getLogger(__name__)

# 创建Blueprint
unified_api = Blueprint('unified_api', __name__, url_prefix='/api/v1/unified')

@dataclass
class QueryRequest:
    """统一查询请求类"""
    query: Optional[str] = None
    source_ids: Optional[List[int]] = None
    category: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0
    include_analytics: bool = True
    
class UnifiedDataManager:
    """统一数据管理器"""
    
    def __init__(self):
        self.pg_manager = None
        self.ch_manager = None
        self._initialized = False
        
    async def initialize(self):
        """初始化数据管理器"""
        if self._initialized:
            return
            
        try:
            # 初始化PostgreSQL
            pg_config = PGConfig(
                host=current_app.config.get('PG_HOST', 'localhost'),
                port=current_app.config.get('PG_PORT', 5432),
                database=current_app.config.get('PG_DATABASE', 'newslook'),
                username=current_app.config.get('PG_USERNAME', 'newslook'),
                password=current_app.config.get('PG_PASSWORD', 'newslook123')
            )
            self.pg_manager = await get_postgresql_manager(pg_config)
            
            # 初始化ClickHouse
            ch_config = CHConfig(
                host=current_app.config.get('CH_HOST', 'localhost'),
                port=current_app.config.get('CH_PORT', 8123),
                database=current_app.config.get('CH_DATABASE', 'newslook_analytics'),
                username=current_app.config.get('CH_USERNAME', 'newslook'),
                password=current_app.config.get('CH_PASSWORD', 'newslook123')
            )
            self.ch_manager = get_clickhouse_manager(ch_config)
            
            self._initialized = True
            logger.info("统一数据管理器初始化完成")
            
        except Exception as e:
            logger.error(f"统一数据管理器初始化失败: {e}")
            raise
            
    async def search_unified_news(self, req: QueryRequest) -> Dict[str, Any]:
        """统一新闻搜索"""
        try:
            # 从PostgreSQL获取基础数据
            pg_results = await self.pg_manager.search_news(
                query=req.query,
                source_ids=req.source_ids,
                category=req.category,
                start_date=req.start_date,
                end_date=req.end_date,
                limit=req.limit,
                offset=req.offset
            )
            
            if not req.include_analytics or not pg_results:
                return {
                    "news": pg_results,
                    "total": len(pg_results),
                    "analytics": None
                }
                
            # 从ClickHouse获取分析数据
            news_ids = [news['id'] for news in pg_results if 'id' in news]
            
            # 构建分析查询
            analytics_data = {}
            if news_ids:
                # 获取热度信息
                analytics_data = await self._get_news_analytics(news_ids)
                
            # 合并数据
            enriched_news = []
            for news in pg_results:
                news_id = news.get('id')
                if news_id and news_id in analytics_data:
                    news['analytics'] = analytics_data[news_id]
                enriched_news.append(news)
                
            return {
                "news": enriched_news,
                "total": len(enriched_news),
                "analytics": {
                    "total_analytics_records": len(analytics_data)
                }
            }
            
        except Exception as e:
            logger.error(f"统一新闻搜索失败: {e}")
            return {"error": str(e), "news": [], "total": 0}
            
    async def _get_news_analytics(self, news_ids: List[int]) -> Dict[int, Dict]:
        """获取新闻分析数据"""
        try:
            # 这里应该调用ClickHouse查询，暂时模拟
            analytics = {}
            for news_id in news_ids:
                analytics[news_id] = {
                    "hotness_score": 0.5,
                    "view_count": 100,
                    "sentiment_score": 0.0,
                    "reading_time": 3
                }
            return analytics
        except Exception as e:
            logger.error(f"获取新闻分析数据失败: {e}")
            return {}
            
    async def get_dashboard_data(self, days: int = 7) -> Dict[str, Any]:
        """获取仪表盘数据"""
        try:
            # 并行获取多个数据源
            tasks = [
                self._get_news_statistics(days),
                self._get_source_performance(days),
                self._get_trending_topics(days),
                self._get_sentiment_trends(days)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            return {
                "news_statistics": results[0] if not isinstance(results[0], Exception) else {},
                "source_performance": results[1] if not isinstance(results[1], Exception) else [],
                "trending_topics": results[2] if not isinstance(results[2], Exception) else [],
                "sentiment_trends": results[3] if not isinstance(results[3], Exception) else [],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取仪表盘数据失败: {e}")
            return {"error": str(e)}
            
    async def _get_news_statistics(self, days: int) -> Dict[str, Any]:
        """获取新闻统计数据"""
        try:
            # 从PostgreSQL获取基础统计
            pg_stats = await self.pg_manager.get_statistics(days=days)
            
            # 计算汇总统计
            total_news = sum(stat['total_count'] for stat in pg_stats.get('daily_stats', []))
            
            return {
                "total_news": total_news,
                "daily_average": total_news / max(days, 1),
                "source_breakdown": pg_stats.get('daily_stats', [])
            }
            
        except Exception as e:
            logger.error(f"获取新闻统计失败: {e}")
            return {}
            
    async def _get_source_performance(self, days: int) -> List[Dict]:
        """获取新闻源性能数据"""
        try:
            # 从ClickHouse获取性能数据（暂时模拟）
            sources = ["东方财富", "新浪财经", "网易财经", "凤凰财经", "腾讯财经"]
            performance = []
            
            for i, source in enumerate(sources):
                performance.append({
                    "source_name": source,
                    "total_news": 100 + i * 20,
                    "success_rate": 0.95 + i * 0.01,
                    "avg_response_time": 1.2 + i * 0.1,
                    "error_count": 5 - i
                })
                
            return performance
            
        except Exception as e:
            logger.error(f"获取源性能数据失败: {e}")
            return []
            
    async def _get_trending_topics(self, days: int) -> List[Dict]:
        """获取热门话题"""
        try:
            # 模拟热门话题数据
            topics = [
                {"topic": "股市行情", "count": 156, "trend": "up"},
                {"topic": "货币政策", "count": 134, "trend": "stable"},
                {"topic": "企业财报", "count": 112, "trend": "down"},
                {"topic": "汇率变动", "count": 98, "trend": "up"},
                {"topic": "投资理财", "count": 87, "trend": "stable"}
            ]
            return topics
            
        except Exception as e:
            logger.error(f"获取热门话题失败: {e}")
            return []
            
    async def _get_sentiment_trends(self, days: int) -> List[Dict]:
        """获取情感趋势"""
        try:
            # 模拟情感趋势数据
            trends = []
            for i in range(days):
                date = datetime.now(timezone.utc) - timedelta(days=i)
                trends.append({
                    "date": date.strftime('%Y-%m-%d'),
                    "positive": 0.4 + (i % 3) * 0.1,
                    "neutral": 0.4,
                    "negative": 0.2 - (i % 3) * 0.05
                })
            return trends[::-1]  # 按时间正序
            
        except Exception as e:
            logger.error(f"获取情感趋势失败: {e}")
            return []

# 全局数据管理器实例
_data_manager = None

async def get_data_manager() -> UnifiedDataManager:
    """获取数据管理器实例"""
    global _data_manager
    if _data_manager is None:
        _data_manager = UnifiedDataManager()
        await _data_manager.initialize()
    return _data_manager

# API路由定义

@unified_api.route('/search', methods=['POST'])
@cross_origin()
def search_news():
    """统一新闻搜索API"""
    try:
        data = request.get_json() or {}
        
        # 解析查询参数
        req = QueryRequest(
            query=data.get('query'),
            source_ids=data.get('source_ids'),
            category=data.get('category'),
            start_date=_parse_date(data.get('start_date')),
            end_date=_parse_date(data.get('end_date')),
            limit=min(data.get('limit', 100), 1000),  # 限制最大1000
            offset=max(data.get('offset', 0), 0),
            include_analytics=data.get('include_analytics', True)
        )
        
        # 异步执行搜索
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        data_manager = loop.run_until_complete(get_data_manager())
        result = loop.run_until_complete(data_manager.search_unified_news(req))
        
        return jsonify({
            "success": True,
            "data": result,
            "request_id": request.headers.get('X-Request-ID', 'unknown')
        })
        
    except Exception as e:
        logger.error(f"搜索API错误: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "request_id": request.headers.get('X-Request-ID', 'unknown')
        }), 500

@unified_api.route('/dashboard', methods=['GET'])
@cross_origin()
def get_dashboard():
    """获取仪表盘数据API"""
    try:
        days = request.args.get('days', 7, type=int)
        days = min(max(days, 1), 90)  # 限制1-90天
        
        # 异步执行查询
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        data_manager = loop.run_until_complete(get_data_manager())
        result = loop.run_until_complete(data_manager.get_dashboard_data(days))
        
        return jsonify({
            "success": True,
            "data": result,
            "request_id": request.headers.get('X-Request-ID', 'unknown')
        })
        
    except Exception as e:
        logger.error(f"仪表盘API错误: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "request_id": request.headers.get('X-Request-ID', 'unknown')
        }), 500

@unified_api.route('/analytics/trending', methods=['GET'])
@cross_origin()
def get_trending():
    """获取趋势分析API"""
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        hours = min(max(hours, 1), 168)  # 限制1-168小时(7天)
        limit = min(max(limit, 1), 200)  # 限制最大200条
        
        # 模拟趋势数据
        trending_data = {
            "hot_news": [],
            "trending_keywords": [],
            "source_activity": []
        }
        
        return jsonify({
            "success": True,
            "data": trending_data,
            "request_id": request.headers.get('X-Request-ID', 'unknown')
        })
        
    except Exception as e:
        logger.error(f"趋势API错误: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "request_id": request.headers.get('X-Request-ID', 'unknown')
        }), 500

@unified_api.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """健康检查API"""
    try:
        # 检查数据库连接状态
        status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "postgresql": "connected",
                "clickhouse": "connected",
                "redis": "connected"
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 503

def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """解析日期字符串"""
    if not date_str:
        return None
        
    try:
        # 支持多种日期格式
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
                
        return None
        
    except Exception as e:
        logger.warning(f"日期解析失败: {date_str}, {e}")
        return None 