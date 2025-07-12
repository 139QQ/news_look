"""
PostgreSQL数据库管理器
实现统一的PostgreSQL数据库架构，解决SQLite多库分散问题
"""

import asyncio
import asyncpg
import psycopg2
from psycopg2 import pool
import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """数据库配置类"""
    host: str = "localhost"
    port: int = 5432
    database: str = "newslook"
    username: str = "newslook"
    password: str = "newslook123"
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    def get_dsn(self) -> str:
        """获取数据库连接字符串"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass 
class NewsRecord:
    """新闻记录数据类"""
    title: str
    content: str
    url: str
    source_id: int
    published_at: datetime
    crawled_at: datetime
    category: str = "财经"
    author: Optional[str] = None
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    sentiment_score: Optional[float] = None
    view_count: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if isinstance(self.keywords, str):
            self.keywords = json.loads(self.keywords) if self.keywords else []
        if isinstance(self.metadata, str):
            self.metadata = json.loads(self.metadata) if self.metadata else {}

class PostgreSQLManager:
    """PostgreSQL数据库管理器"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._sync_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        self._async_pool: Optional[asyncpg.Pool] = None
        self._source_mapping: Dict[str, int] = {}
        self._initialized = False
        
    async def initialize(self):
        """初始化数据库连接和表结构"""
        if self._initialized:
            return
            
        try:
            # 初始化异步连接池
            self._async_pool = await asyncpg.create_pool(
                self.config.get_dsn(),
                min_size=5,
                max_size=self.config.pool_size,
                command_timeout=self.config.pool_timeout
            )
            
            # 初始化同步连接池
            self._sync_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=5,
                maxconn=self.config.pool_size,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password
            )
            
            # 创建表结构
            await self._create_schema()
            
            # 加载源映射
            await self._load_source_mapping()
            
            self._initialized = True
            logger.info("PostgreSQL数据库管理器初始化完成")
            
        except Exception as e:
            logger.error(f"PostgreSQL初始化失败: {e}")
            raise
            
    async def _create_schema(self):
        """创建数据库表结构"""
        schema_sql = """
        -- 新闻源表
        CREATE TABLE IF NOT EXISTS news_sources (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            code VARCHAR(50) UNIQUE NOT NULL,
            base_url VARCHAR(255),
            description TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 新闻主表（按source_id分区）
        CREATE TABLE IF NOT EXISTS news (
            id BIGSERIAL,
            title TEXT NOT NULL,
            content TEXT,
            url VARCHAR(512) NOT NULL,
            source_id INTEGER NOT NULL REFERENCES news_sources(id),
            published_at TIMESTAMP WITH TIME ZONE NOT NULL,
            crawled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            category VARCHAR(100) DEFAULT '财经',
            author VARCHAR(200),
            summary TEXT,
            keywords JSONB,
            sentiment_score REAL,
            view_count INTEGER DEFAULT 0,
            metadata JSONB,
            hash_content VARCHAR(64), -- MD5哈希，用于去重
            is_deleted BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, source_id)
        ) PARTITION BY HASH (source_id);
        
        -- 创建分区表（按新闻源分区）
        CREATE TABLE IF NOT EXISTS news_p1 PARTITION OF news 
        FOR VALUES WITH (MODULUS 4, REMAINDER 0);
        
        CREATE TABLE IF NOT EXISTS news_p2 PARTITION OF news 
        FOR VALUES WITH (MODULUS 4, REMAINDER 1);
        
        CREATE TABLE IF NOT EXISTS news_p3 PARTITION OF news 
        FOR VALUES WITH (MODULUS 4, REMAINDER 2);
        
        CREATE TABLE IF NOT EXISTS news_p4 PARTITION OF news 
        FOR VALUES WITH (MODULUS 4, REMAINDER 3);
        
        -- 索引优化
        CREATE INDEX IF NOT EXISTS idx_news_source_published ON news (source_id, published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_news_url_hash ON news (url, hash_content);
        CREATE INDEX IF NOT EXISTS idx_news_category_time ON news (category, published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_news_crawled_at ON news (crawled_at DESC);
        
        -- 全文搜索索引（中文支持）
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE INDEX IF NOT EXISTS idx_news_content_gin ON news USING GIN (to_tsvector('simple', title || ' ' || COALESCE(content, '')));
        CREATE INDEX IF NOT EXISTS idx_news_keywords_gin ON news USING GIN (keywords);
        
        -- 聚合统计表
        CREATE TABLE IF NOT EXISTS news_statistics (
            id SERIAL PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES news_sources(id),
            stat_date DATE NOT NULL,
            total_count INTEGER DEFAULT 0,
            category_counts JSONB,
            avg_sentiment REAL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_id, stat_date)
        );
        
        -- 数据血缘追踪表
        CREATE TABLE IF NOT EXISTS data_lineage (
            id BIGSERIAL PRIMARY KEY,
            entity_type VARCHAR(50) NOT NULL, -- 'news', 'source', etc.
            entity_id BIGINT NOT NULL,
            operation VARCHAR(50) NOT NULL, -- 'create', 'update', 'delete'
            source_system VARCHAR(100), -- 'sqlite_migration', 'crawler_eastmoney'
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 更新触发器
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        CREATE TRIGGER update_news_updated_at 
            BEFORE UPDATE ON news 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            
        CREATE TRIGGER update_news_sources_updated_at 
            BEFORE UPDATE ON news_sources 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
        
        async with self._async_pool.acquire() as conn:
            await conn.execute(schema_sql)
            logger.info("数据库表结构创建完成")
            
    async def _load_source_mapping(self):
        """加载新闻源映射"""
        sources = [
            ("东方财富", "eastmoney", "https://finance.eastmoney.com"),
            ("新浪财经", "sina", "https://finance.sina.com.cn"),
            ("网易财经", "netease", "https://money.163.com"),
            ("凤凰财经", "ifeng", "https://finance.ifeng.com"),
            ("腾讯财经", "tencent", "https://finance.qq.com")
        ]
        
        async with self._async_pool.acquire() as conn:
            for name, code, url in sources:
                source_id = await conn.fetchval(
                    """
                    INSERT INTO news_sources (name, code, base_url) 
                    VALUES ($1, $2, $3) 
                    ON CONFLICT (code) DO UPDATE SET base_url = $3
                    RETURNING id
                    """,
                    name, code, url
                )
                self._source_mapping[code] = source_id
                
        logger.info(f"加载新闻源映射完成: {self._source_mapping}")
        
    def get_source_id(self, source_code: str) -> int:
        """获取新闻源ID"""
        return self._source_mapping.get(source_code, 1)
        
    @asynccontextmanager
    async def async_connection(self):
        """异步连接上下文管理器"""
        async with self._async_pool.acquire() as conn:
            yield conn
            
    @contextmanager
    def sync_connection(self):
        """同步连接上下文管理器"""
        conn = self._sync_pool.getconn()
        try:
            yield conn
        finally:
            self._sync_pool.putconn(conn)
            
    async def insert_news(self, news: NewsRecord) -> int:
        """插入新闻记录"""
        async with self.async_connection() as conn:
            # 计算内容哈希用于去重
            import hashlib
            content_hash = hashlib.md5(f"{news.title}{news.url}".encode()).hexdigest()
            
            # 检查是否已存在
            existing = await conn.fetchval(
                "SELECT id FROM news WHERE url = $1 AND source_id = $2",
                news.url, news.source_id
            )
            
            if existing:
                logger.debug(f"新闻已存在，跳过: {news.url}")
                return existing
                
            # 插入新记录
            news_id = await conn.fetchval(
                """
                INSERT INTO news (
                    title, content, url, source_id, published_at, crawled_at,
                    category, author, summary, keywords, sentiment_score,
                    view_count, metadata, hash_content
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
                ) RETURNING id
                """,
                news.title, news.content, news.url, news.source_id,
                news.published_at, news.crawled_at, news.category,
                news.author, news.summary, json.dumps(news.keywords or []),
                news.sentiment_score, news.view_count,
                json.dumps(news.metadata or {}), content_hash
            )
            
            # 记录数据血缘
            await self._record_lineage("news", news_id, "create", "crawler")
            
            return news_id
            
    async def batch_insert_news(self, news_list: List[NewsRecord]) -> List[int]:
        """批量插入新闻记录"""
        if not news_list:
            return []
            
        async with self.async_connection() as conn:
            async with conn.transaction():
                inserted_ids = []
                
                # 准备批量数据
                values = []
                for news in news_list:
                    import hashlib
                    content_hash = hashlib.md5(f"{news.title}{news.url}".encode()).hexdigest()
                    
                    values.append((
                        news.title, news.content, news.url, news.source_id,
                        news.published_at, news.crawled_at, news.category,
                        news.author, news.summary, json.dumps(news.keywords or []),
                        news.sentiment_score, news.view_count,
                        json.dumps(news.metadata or {}), content_hash
                    ))
                
                # 执行批量插入
                result = await conn.copy_records_to_table(
                    'news',
                    columns=[
                        'title', 'content', 'url', 'source_id', 'published_at',
                        'crawled_at', 'category', 'author', 'summary', 'keywords',
                        'sentiment_score', 'view_count', 'metadata', 'hash_content'
                    ],
                    records=values
                )
                
                logger.info(f"批量插入 {len(news_list)} 条新闻记录")
                return list(range(len(news_list)))  # 简化返回
                
    async def search_news(self, 
                         query: str = None,
                         source_ids: List[int] = None,
                         category: str = None,
                         start_date: datetime = None,
                         end_date: datetime = None,
                         limit: int = 100,
                         offset: int = 0) -> List[Dict]:
        """搜索新闻"""
        conditions = ["is_deleted = false"]
        params = []
        param_idx = 1
        
        if query:
            conditions.append(f"to_tsvector('simple', title || ' ' || COALESCE(content, '')) @@ plainto_tsquery('simple', ${param_idx})")
            params.append(query)
            param_idx += 1
            
        if source_ids:
            conditions.append(f"source_id = ANY(${param_idx})")
            params.append(source_ids)
            param_idx += 1
            
        if category:
            conditions.append(f"category = ${param_idx}")
            params.append(category)
            param_idx += 1
            
        if start_date:
            conditions.append(f"published_at >= ${param_idx}")
            params.append(start_date)
            param_idx += 1
            
        if end_date:
            conditions.append(f"published_at <= ${param_idx}")
            params.append(end_date)
            param_idx += 1
            
        sql = f"""
        SELECT n.*, s.name as source_name, s.code as source_code
        FROM news n
        JOIN news_sources s ON n.source_id = s.id
        WHERE {' AND '.join(conditions)}
        ORDER BY n.published_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        
        params.extend([limit, offset])
        
        async with self.async_connection() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]
            
    async def get_statistics(self, source_ids: List[int] = None, days: int = 7) -> Dict:
        """获取统计信息"""
        conditions = []
        params = []
        param_idx = 1
        
        if source_ids:
            conditions.append(f"source_id = ANY(${param_idx})")
            params.append(source_ids)
            param_idx += 1
            
        conditions.append(f"published_at >= CURRENT_TIMESTAMP - INTERVAL '{days} days'")
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        sql = f"""
        SELECT 
            COUNT(*) as total_count,
            COUNT(DISTINCT source_id) as source_count,
            AVG(sentiment_score) as avg_sentiment,
            DATE_TRUNC('day', published_at) as date,
            source_id,
            s.name as source_name
        FROM news n
        JOIN news_sources s ON n.source_id = s.id
        {where_clause}
        GROUP BY DATE_TRUNC('day', published_at), source_id, s.name
        ORDER BY date DESC
        """
        
        async with self.async_connection() as conn:
            rows = await conn.fetch(sql, *params)
            return {"daily_stats": [dict(row) for row in rows]}
            
    async def _record_lineage(self, entity_type: str, entity_id: int, operation: str, source_system: str, metadata: Dict = None):
        """记录数据血缘"""
        async with self.async_connection() as conn:
            await conn.execute(
                """
                INSERT INTO data_lineage (entity_type, entity_id, operation, source_system, metadata)
                VALUES ($1, $2, $3, $4, $5)
                """,
                entity_type, entity_id, operation, source_system, json.dumps(metadata or {})
            )
            
    async def close(self):
        """关闭连接池"""
        if self._async_pool:
            await self._async_pool.close()
        if self._sync_pool:
            self._sync_pool.closeall()
        logger.info("PostgreSQL连接池已关闭")


# 全局实例
_pg_manager: Optional[PostgreSQLManager] = None

async def get_postgresql_manager(config: DatabaseConfig = None) -> PostgreSQLManager:
    """获取PostgreSQL管理器实例"""
    global _pg_manager
    if _pg_manager is None:
        if config is None:
            config = DatabaseConfig()
        _pg_manager = PostgreSQLManager(config)
        await _pg_manager.initialize()
    return _pg_manager 