#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 统一数据库架构模块
提供多源数据接入、数据治理、分层存储和统一访问功能
"""

from .models import (
    DataSource,
    DataSchema,
    NewsUnified,
    KeywordUnified,
    StockUnified,
    NewsKeywordRelation,
    NewsStockRelation,
    DataLineage,
    QualityRule,
    QualityCheckResult,
    DataChangeLog,
    UserAccount,
    DataAccessPolicy,
    UserDataAccess
)

from .adapters import (
    DataIngestionAdapter,
    APIIngestionAdapter,
    CSVIngestionAdapter,
    StreamIngestionAdapter
)

from .quality import (
    QualityRuleType,
    QualityRule as QualityRuleEngine,
    QualityEngine
)

from .gateway import (
    UnifiedQueryGateway,
    DataAccessController
)

from .utils import (
    generate_global_id,
    DataTierManager,
    MetadataCollector
)

__version__ = "1.0.0"
__author__ = "NewsLook Team"
__description__ = "统一数据库架构 - 多源适配、数据治理、分层存储"

__all__ = [
    # 数据模型
    'DataSource',
    'DataSchema', 
    'NewsUnified',
    'KeywordUnified',
    'StockUnified',
    'NewsKeywordRelation',
    'NewsStockRelation',
    'DataLineage',
    'QualityRule',
    'QualityCheckResult',
    'DataChangeLog',
    'UserAccount',
    'DataAccessPolicy',
    'UserDataAccess',
    
    # 数据接入适配器
    'DataIngestionAdapter',
    'APIIngestionAdapter', 
    'CSVIngestionAdapter',
    'StreamIngestionAdapter',
    
    # 数据质量引擎
    'QualityRuleType',
    'QualityRuleEngine',
    'QualityEngine',
    
    # 统一访问网关
    'UnifiedQueryGateway',
    'DataAccessController',
    
    # 工具类
    'generate_global_id',
    'DataTierManager',
    'MetadataCollector',
] 