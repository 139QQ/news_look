#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 统一数据库模型定义
包含所有核心实体和关系模型
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, 
    ForeignKey, JSON, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

Base = declarative_base()

class DataSource(Base):
    """数据源定义表"""
    __tablename__ = 'data_sources'
    
    source_id = Column(String(50), primary_key=True, comment='数据源ID')
    source_name = Column(String(200), nullable=False, comment='数据源名称')
    source_type = Column(String(50), nullable=False, comment='数据源类型:API/CSV/Stream/Crawler')
    connection_config = Column(JSON, comment='连接配置')
    schema_config = Column(JSON, comment='模式配置')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 关系
    schemas = relationship("DataSchema", back_populates="source")
    news = relationship("NewsUnified", back_populates="source")
    
    def __repr__(self):
        return f"<DataSource(id={self.source_id}, name={self.source_name}, type={self.source_type})>"


class DataSchema(Base):
    """数据源模式表"""
    __tablename__ = 'data_schemas'
    
    schema_id = Column(String(50), primary_key=True, comment='模式ID')
    source_id = Column(String(50), ForeignKey('data_sources.source_id'), nullable=False, comment='数据源ID')
    schema_name = Column(String(200), comment='模式名称')
    schema_definition = Column(JSON, comment='字段定义')
    version = Column(String(20), comment='版本号')
    is_current = Column(Boolean, default=True, comment='是否当前版本')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    # 关系
    source = relationship("DataSource", back_populates="schemas")
    
    def __repr__(self):
        return f"<DataSchema(id={self.schema_id}, source={self.source_id}, version={self.version})>"


class NewsUnified(Base):
    """统一新闻表"""
    __tablename__ = 'news_unified'
    
    global_id = Column(String(100), primary_key=True, comment='全局唯一ID')
    source_id = Column(String(50), ForeignKey('data_sources.source_id'), nullable=False, comment='数据源ID')
    original_id = Column(String(200), comment='原始ID')
    title = Column(Text, nullable=False, comment='标题')
    content = Column(Text, comment='正文内容')
    content_html = Column(Text, comment='HTML内容')
    pub_time = Column(DateTime, comment='发布时间')
    author = Column(String(200), comment='作者')
    url = Column(Text, comment='原文链接')
    category = Column(String(100), comment='分类')
    sentiment_score = Column(Float, comment='情感分数')
    keywords = Column(JSON, comment='关键词列表')
    images = Column(JSON, comment='图片列表')
    related_stocks = Column(JSON, comment='相关股票')
    data_tier = Column(String(20), default='hot', comment='数据层级:hot/warm/cold')
    quality_score = Column(Float, comment='质量分数')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    metadata = Column(JSON, comment='扩展元数据')
    
    # 约束
    __table_args__ = (
        UniqueConstraint('source_id', 'original_id', name='uq_source_original'),
        Index('idx_news_source_time', 'source_id', 'pub_time'),
        Index('idx_news_category', 'category'),
        Index('idx_news_tier', 'data_tier'),
        Index('idx_news_quality', 'quality_score'),
        Index('idx_news_pub_time', 'pub_time'),
    )
    
    # 关系
    source = relationship("DataSource", back_populates="news")
    keyword_relations = relationship("NewsKeywordRelation", back_populates="news")
    stock_relations = relationship("NewsStockRelation", back_populates="news")
    
    def __repr__(self):
        return f"<NewsUnified(id={self.global_id}, title={self.title[:50]}...)>"


class KeywordUnified(Base):
    """统一关键词表"""
    __tablename__ = 'keywords_unified'
    
    keyword_id = Column(String(100), primary_key=True, comment='关键词ID')
    keyword_text = Column(String(200), unique=True, nullable=False, comment='关键词文本')
    category = Column(String(100), comment='关键词分类')
    frequency = Column(Integer, default=1, comment='出现频次')
    importance_score = Column(Float, comment='重要性分数')
    first_seen = Column(DateTime, comment='首次出现')
    last_seen = Column(DateTime, comment='最后出现')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    # 关系
    news_relations = relationship("NewsKeywordRelation", back_populates="keyword")
    
    def __repr__(self):
        return f"<KeywordUnified(id={self.keyword_id}, text={self.keyword_text})>"


class StockUnified(Base):
    """统一股票表"""
    __tablename__ = 'stocks_unified'
    
    stock_id = Column(String(100), primary_key=True, comment='股票ID')
    stock_code = Column(String(20), unique=True, nullable=False, comment='股票代码')
    stock_name = Column(String(200), comment='股票名称')
    market = Column(String(10), comment='交易市场:SH/SZ/HK/US')
    industry = Column(String(100), comment='所属行业')
    market_cap = Column(Integer, comment='市值')
    is_active = Column(Boolean, default=True, comment='是否活跃')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    # 关系
    news_relations = relationship("NewsStockRelation", back_populates="stock")
    
    def __repr__(self):
        return f"<StockUnified(id={self.stock_id}, code={self.stock_code}, name={self.stock_name})>"


class NewsKeywordRelation(Base):
    """新闻-关键词关系表"""
    __tablename__ = 'news_keyword_relations'
    
    news_id = Column(String(100), ForeignKey('news_unified.global_id'), primary_key=True, comment='新闻ID')
    keyword_id = Column(String(100), ForeignKey('keywords_unified.keyword_id'), primary_key=True, comment='关键词ID')
    relevance_score = Column(Float, comment='相关度分数')
    extraction_method = Column(String(50), comment='提取方法')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    # 关系
    news = relationship("NewsUnified", back_populates="keyword_relations")
    keyword = relationship("KeywordUnified", back_populates="news_relations")
    
    def __repr__(self):
        return f"<NewsKeywordRelation(news={self.news_id}, keyword={self.keyword_id})>"


class NewsStockRelation(Base):
    """新闻-股票关系表"""
    __tablename__ = 'news_stock_relations'
    
    news_id = Column(String(100), ForeignKey('news_unified.global_id'), primary_key=True, comment='新闻ID')
    stock_id = Column(String(100), ForeignKey('stocks_unified.stock_id'), primary_key=True, comment='股票ID')
    relevance_score = Column(Float, comment='相关度分数')
    mention_context = Column(Text, comment='提及上下文')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    # 关系
    news = relationship("NewsUnified", back_populates="stock_relations")
    stock = relationship("StockUnified", back_populates="news_relations")
    
    def __repr__(self):
        return f"<NewsStockRelation(news={self.news_id}, stock={self.stock_id})>"


class DataLineage(Base):
    """数据血缘表"""
    __tablename__ = 'data_lineage'
    
    lineage_id = Column(String(50), primary_key=True, comment='血缘ID')
    source_system = Column(String(100), comment='源系统')
    source_table = Column(String(100), comment='源表')
    source_field = Column(String(100), comment='源字段')
    target_system = Column(String(100), comment='目标系统')
    target_table = Column(String(100), comment='目标表')
    target_field = Column(String(100), comment='目标字段')
    transformation_rule = Column(Text, comment='转换规则')
    transformation_type = Column(String(50), comment='转换类型')
    created_by = Column(String(100), comment='创建者')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    def __repr__(self):
        return f"<DataLineage(id={self.lineage_id}, {self.source_table}.{self.source_field} -> {self.target_table}.{self.target_field})>"


class QualityRule(Base):
    """质量规则表"""
    __tablename__ = 'quality_rules'
    
    rule_id = Column(String(50), primary_key=True, comment='规则ID')
    rule_name = Column(String(200), comment='规则名称')
    rule_type = Column(String(50), comment='规则类型:NotNull/Unique/Range/Pattern/Custom')
    target_table = Column(String(100), comment='目标表')
    target_field = Column(String(100), comment='目标字段')
    rule_config = Column(JSON, comment='规则配置')
    severity = Column(String(20), comment='严重程度:ERROR/WARNING/INFO')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    # 关系
    check_results = relationship("QualityCheckResult", back_populates="rule")
    
    def __repr__(self):
        return f"<QualityRule(id={self.rule_id}, name={self.rule_name}, type={self.rule_type})>"


class QualityCheckResult(Base):
    """质量检查结果表"""
    __tablename__ = 'quality_check_results'
    
    check_id = Column(String(50), primary_key=True, comment='检查ID')
    rule_id = Column(String(50), ForeignKey('quality_rules.rule_id'), nullable=False, comment='规则ID')
    data_batch_id = Column(String(100), comment='数据批次ID')
    table_name = Column(String(100), comment='表名')
    total_records = Column(Integer, comment='总记录数')
    passed_records = Column(Integer, comment='通过记录数')
    failed_records = Column(Integer, comment='失败记录数')
    pass_rate = Column(Float, comment='通过率')
    error_details = Column(JSON, comment='错误详情')
    checked_at = Column(DateTime, default=func.now(), comment='检查时间')
    
    # 关系
    rule = relationship("QualityRule", back_populates="check_results")
    
    def __repr__(self):
        return f"<QualityCheckResult(id={self.check_id}, rule={self.rule_id}, pass_rate={self.pass_rate})>"


class DataChangeLog(Base):
    """数据变更日志表"""
    __tablename__ = 'data_change_logs'
    
    change_id = Column(String(50), primary_key=True, comment='变更ID')
    table_name = Column(String(100), comment='表名')
    record_id = Column(String(200), comment='记录ID')
    operation = Column(String(20), comment='操作:INSERT/UPDATE/DELETE')
    old_values = Column(JSON, comment='变更前值')
    new_values = Column(JSON, comment='变更后值')
    changed_by = Column(String(100), comment='变更者')
    change_source = Column(String(100), comment='变更来源')
    changed_at = Column(DateTime, default=func.now(), comment='变更时间')
    
    # 索引
    __table_args__ = (
        Index('idx_change_table_time', 'table_name', 'changed_at'),
        Index('idx_change_record', 'table_name', 'record_id'),
    )
    
    def __repr__(self):
        return f"<DataChangeLog(id={self.change_id}, table={self.table_name}, operation={self.operation})>"


class UserAccount(Base):
    """用户账户表"""
    __tablename__ = 'user_accounts'
    
    user_id = Column(String(50), primary_key=True, comment='用户ID')
    username = Column(String(100), unique=True, nullable=False, comment='用户名')
    email = Column(String(200), unique=True, comment='邮箱')
    password_hash = Column(String(200), comment='密码哈希')
    role = Column(String(50), comment='角色')
    permissions = Column(JSON, comment='权限列表')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    last_login = Column(DateTime, comment='最后登录时间')
    
    # 关系
    data_access = relationship("UserDataAccess", back_populates="user")
    
    def __repr__(self):
        return f"<UserAccount(id={self.user_id}, username={self.username}, role={self.role})>"


class DataAccessPolicy(Base):
    """数据访问策略表"""
    __tablename__ = 'data_access_policies'
    
    policy_id = Column(String(50), primary_key=True, comment='策略ID')
    policy_name = Column(String(200), comment='策略名称')
    resource_pattern = Column(String(500), comment='资源模式')
    permission_type = Column(String(50), comment='权限类型:read/write/delete')
    conditions = Column(JSON, comment='访问条件')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')
    
    # 关系
    user_access = relationship("UserDataAccess", back_populates="policy")
    
    def __repr__(self):
        return f"<DataAccessPolicy(id={self.policy_id}, name={self.policy_name})>"


class UserDataAccess(Base):
    """用户数据访问授权表"""
    __tablename__ = 'user_data_access'
    
    user_id = Column(String(50), ForeignKey('user_accounts.user_id'), primary_key=True, comment='用户ID')
    policy_id = Column(String(50), ForeignKey('data_access_policies.policy_id'), primary_key=True, comment='策略ID')
    granted_by = Column(String(50), comment='授权者')
    granted_at = Column(DateTime, default=func.now(), comment='授权时间')
    expires_at = Column(DateTime, comment='过期时间')
    
    # 关系
    user = relationship("UserAccount", back_populates="data_access")
    policy = relationship("DataAccessPolicy", back_populates="user_access")
    
    def __repr__(self):
        return f"<UserDataAccess(user={self.user_id}, policy={self.policy_id})>"


# 分区表基类
class PartitionedTable:
    """分区表基类"""
    
    @classmethod
    def create_partition(cls, year: int, month: int):
        """创建分区表"""
        partition_name = f"{cls.__tablename__}_{year:04d}{month:02d}"
        start_date = f"{year:04d}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1:04d}-01-01"
        else:
            end_date = f"{year:04d}-{month+1:02d}-01"
        
        return f"""
        CREATE TABLE {partition_name} PARTITION OF {cls.__tablename__}
        FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """


# 为分区表添加混入
class NewsUnifiedPartitioned(NewsUnified, PartitionedTable):
    """分区版本的统一新闻表"""
    pass


# 创建所有表的函数
def create_all_tables(engine):
    """创建所有表"""
    Base.metadata.create_all(engine)
    
    # 创建当前月份和下个月的分区
    from datetime import datetime
    now = datetime.now()
    current_partition = NewsUnifiedPartitioned.create_partition(now.year, now.month)
    
    next_month = now.month + 1 if now.month < 12 else 1
    next_year = now.year if now.month < 12 else now.year + 1
    next_partition = NewsUnifiedPartitioned.create_partition(next_year, next_month)
    
    # 执行分区创建语句
    with engine.connect() as conn:
        try:
            conn.execute(current_partition)
            conn.execute(next_partition)
            conn.commit()
        except Exception as e:
            print(f"创建分区表时出错: {e}")
            conn.rollback()


# 数据模型工厂类
class ModelFactory:
    """数据模型工厂"""
    
    @staticmethod
    def create_news_unified(data: Dict[str, Any], source_id: str) -> NewsUnified:
        """创建统一新闻实例"""
        from .utils import generate_global_id
        
        global_id = generate_global_id(source_id, "NEWS", data.get('url', ''))
        
        return NewsUnified(
            global_id=global_id,
            source_id=source_id,
            original_id=data.get('id'),
            title=data.get('title'),
            content=data.get('content'),
            content_html=data.get('content_html'),
            pub_time=data.get('pub_time'),
            author=data.get('author'),
            url=data.get('url'),
            category=data.get('category'),
            sentiment_score=data.get('sentiment_score'),
            keywords=data.get('keywords'),
            images=data.get('images'),
            related_stocks=data.get('related_stocks'),
            metadata=data.get('metadata', {})
        )
    
    @staticmethod
    def create_keyword_unified(keyword_text: str, category: str = None) -> KeywordUnified:
        """创建统一关键词实例"""
        from .utils import generate_global_id
        
        keyword_id = generate_global_id("SYSTEM", "KEYWORD", keyword_text)
        
        return KeywordUnified(
            keyword_id=keyword_id,
            keyword_text=keyword_text,
            category=category,
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )
    
    @staticmethod
    def create_stock_unified(stock_code: str, stock_name: str, market: str) -> StockUnified:
        """创建统一股票实例"""
        from .utils import generate_global_id
        
        stock_id = generate_global_id("SYSTEM", "STOCK", stock_code)
        
        return StockUnified(
            stock_id=stock_id,
            stock_code=stock_code,
            stock_name=stock_name,
            market=market
        ) 