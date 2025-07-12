# NewsLook 统一数据库架构设计

## 1. 架构概述

### 1.1 设计目标
- **多源适配**：支持API、CSV、流式数据等多种数据接入方式
- **数据治理**：实现元数据自动采集、数据质量管控、血缘关系追踪
- **统一访问**：提供标准SQL接口和统一数据目录
- **存储分层**：热温冷数据分层存储，优化性能和成本
- **权限控制**：细粒度的列级权限控制

### 1.2 核心设计原则
1. **源数据隔离**：原始数据 → 清洗区 → 整合区
2. **全局ID系统**：`<来源编码>_<业务实体>_<哈希>`
3. **变更捕获**：CDC日志同步所有源变更
4. **数据谱系**：自动记录源字段→目标字段映射

## 2. 技术栈选型

### 2.1 核心组件
```yaml
# 数据接入层
ingestion:
  stream_processing: Apache Flink
  message_queue: Apache Kafka
  api_gateway: Kong/Nginx
  
# 数据存储层
storage:
  lakehouse: Delta Lake
  oltp: PostgreSQL (热数据)
  olap: ClickHouse (温数据)  
  archive: MinIO/S3 (冷数据)
  
# 数据治理层
governance:
  metadata: Apache Atlas
  quality: Great Expectations
  lineage: DataHub
  security: Apache Ranger
  
# 查询引擎
query:
  federation: Trino/Presto
  cache: Redis
  search: Elasticsearch
```

### 2.2 开发技术栈
```yaml
backend:
  language: Python 3.9+
  framework: FastAPI
  async: asyncio + aiohttp
  orm: SQLAlchemy 2.0
  migration: Alembic
  
data_processing:
  batch: Apache Spark
  stream: Apache Flink
  ml: PyTorch + HuggingFace
  
monitoring:
  metrics: Prometheus + Grafana
  logging: ELK Stack
  tracing: Jaeger
```

## 3. 数据模型设计

### 3.1 全局ID生成规则
```python
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
    import hashlib
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
    return f"{source_code}_{entity_type}_{content_hash}"
```

### 3.2 核心实体模型

#### 3.2.1 数据源管理
```sql
-- 数据源定义表
CREATE TABLE data_sources (
    source_id VARCHAR(50) PRIMARY KEY,
    source_name VARCHAR(200) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- API/CSV/Stream/Crawler
    connection_config JSONB,
    schema_config JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 数据源模式表
CREATE TABLE data_schemas (
    schema_id VARCHAR(50) PRIMARY KEY,
    source_id VARCHAR(50) REFERENCES data_sources(source_id),
    schema_name VARCHAR(200),
    schema_definition JSONB, -- 字段定义
    version VARCHAR(20),
    is_current BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.2 统一新闻实体
```sql
-- 统一新闻表
CREATE TABLE news_unified (
    global_id VARCHAR(100) PRIMARY KEY,
    source_id VARCHAR(50) REFERENCES data_sources(source_id),
    original_id VARCHAR(200),
    title TEXT NOT NULL,
    content TEXT,
    content_html TEXT,
    pub_time TIMESTAMP,
    author VARCHAR(200),
    url TEXT,
    category VARCHAR(100),
    sentiment_score FLOAT,
    keywords JSONB,
    images JSONB,
    related_stocks JSONB,
    data_tier VARCHAR(20) DEFAULT 'hot', -- hot/warm/cold
    quality_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB, -- 扩展元数据
    
    -- 索引
    CONSTRAINT unique_source_original UNIQUE(source_id, original_id),
    INDEX idx_news_source_time (source_id, pub_time),
    INDEX idx_news_category (category),
    INDEX idx_news_tier (data_tier),
    INDEX idx_news_quality (quality_score)
);

-- 分区策略 (按月分区)
CREATE TABLE news_unified_202401 PARTITION OF news_unified
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

#### 3.2.3 关键词和股票实体
```sql
-- 统一关键词表
CREATE TABLE keywords_unified (
    keyword_id VARCHAR(100) PRIMARY KEY,
    keyword_text VARCHAR(200) UNIQUE NOT NULL,
    category VARCHAR(100),
    frequency INTEGER DEFAULT 1,
    importance_score FLOAT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 统一股票表
CREATE TABLE stocks_unified (
    stock_id VARCHAR(100) PRIMARY KEY,
    stock_code VARCHAR(20) UNIQUE NOT NULL,
    stock_name VARCHAR(200),
    market VARCHAR(10), -- SH/SZ/HK/US
    industry VARCHAR(100),
    market_cap BIGINT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 新闻-关键词关系表
CREATE TABLE news_keyword_relations (
    news_id VARCHAR(100) REFERENCES news_unified(global_id),
    keyword_id VARCHAR(100) REFERENCES keywords_unified(keyword_id),
    relevance_score FLOAT,
    extraction_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (news_id, keyword_id)
);

-- 新闻-股票关系表
CREATE TABLE news_stock_relations (
    news_id VARCHAR(100) REFERENCES news_unified(global_id),
    stock_id VARCHAR(100) REFERENCES stocks_unified(stock_id),
    relevance_score FLOAT,
    mention_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (news_id, stock_id)
);
```

### 3.3 数据治理模型

#### 3.3.1 元数据管理
```sql
-- 数据血缘表
CREATE TABLE data_lineage (
    lineage_id VARCHAR(50) PRIMARY KEY,
    source_system VARCHAR(100),
    source_table VARCHAR(100),
    source_field VARCHAR(100),
    target_system VARCHAR(100),
    target_table VARCHAR(100),
    target_field VARCHAR(100),
    transformation_rule TEXT,
    transformation_type VARCHAR(50),
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 质量规则表
CREATE TABLE quality_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    rule_name VARCHAR(200),
    rule_type VARCHAR(50), -- NotNull/Unique/Range/Pattern/Custom
    target_table VARCHAR(100),
    target_field VARCHAR(100),
    rule_config JSONB,
    severity VARCHAR(20), -- ERROR/WARNING/INFO
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 质量检查结果表
CREATE TABLE quality_check_results (
    check_id VARCHAR(50) PRIMARY KEY,
    rule_id VARCHAR(50) REFERENCES quality_rules(rule_id),
    data_batch_id VARCHAR(100),
    table_name VARCHAR(100),
    total_records INTEGER,
    passed_records INTEGER,
    failed_records INTEGER,
    pass_rate FLOAT,
    error_details JSONB,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.3.2 变更捕获
```sql
-- 数据变更日志表
CREATE TABLE data_change_logs (
    change_id VARCHAR(50) PRIMARY KEY,
    table_name VARCHAR(100),
    record_id VARCHAR(200),
    operation VARCHAR(20), -- INSERT/UPDATE/DELETE
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    change_source VARCHAR(100), -- 变更来源
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_change_table_time (table_name, changed_at),
    INDEX idx_change_record (table_name, record_id)
);
```

### 3.4 权限控制模型
```sql
-- 用户账户表
CREATE TABLE user_accounts (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE,
    password_hash VARCHAR(200),
    role VARCHAR(50),
    permissions JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 数据访问策略表
CREATE TABLE data_access_policies (
    policy_id VARCHAR(50) PRIMARY KEY,
    policy_name VARCHAR(200),
    resource_pattern VARCHAR(500), -- 表.列的匹配模式
    permission_type VARCHAR(50), -- read/write/delete
    conditions JSONB, -- 访问条件 (时间范围、数据范围等)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户数据访问授权表
CREATE TABLE user_data_access (
    user_id VARCHAR(50) REFERENCES user_accounts(user_id),
    policy_id VARCHAR(50) REFERENCES data_access_policies(policy_id),
    granted_by VARCHAR(50),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    PRIMARY KEY (user_id, policy_id)
);
```

## 4. 存储分层策略

### 4.1 数据生命周期管理
```yaml
# 数据分层配置
data_tiers:
  hot:
    storage: PostgreSQL
    retention: 7 days
    characteristics:
      - 高频查询
      - 实时写入
      - 低延迟要求
      
  warm:
    storage: ClickHouse
    retention: 90 days
    characteristics:
      - 分析查询
      - 聚合计算
      - 高吞吐量
      
  cold:
    storage: MinIO/S3
    retention: unlimited
    characteristics:
      - 归档存储
      - 低成本
      - 压缩存储

# 自动分层规则
tiering_rules:
  - condition: "pub_time < NOW() - INTERVAL '7 days'"
    action: "move_to_warm"
    
  - condition: "pub_time < NOW() - INTERVAL '90 days'"
    action: "move_to_cold"
```

### 4.2 分层实现
```sql
-- 热数据分区 (PostgreSQL)
CREATE TABLE news_hot (
    LIKE news_unified INCLUDING ALL
) PARTITION BY RANGE (pub_time);

-- 温数据表 (ClickHouse)
CREATE TABLE news_warm (
    global_id String,
    source_id String,
    title String,
    content String,
    pub_time DateTime,
    category String,
    sentiment_score Float32,
    created_at DateTime
) ENGINE = MergeTree()
ORDER BY (source_id, pub_time)
PARTITION BY toYYYYMM(pub_time);

-- 冷数据索引表 (PostgreSQL)
CREATE TABLE news_cold_index (
    global_id VARCHAR(100) PRIMARY KEY,
    s3_bucket VARCHAR(100),
    s3_key VARCHAR(500),
    compression_type VARCHAR(20),
    archived_at TIMESTAMP,
    metadata JSONB
);
```

## 5. 数据接入适配器

### 5.1 接入层设计
```python
# 统一数据接入接口
from abc import ABC, abstractmethod
from typing import Dict, List, Any, AsyncIterator

class DataIngestionAdapter(ABC):
    """数据接入适配器基类"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    async def fetch_data(self, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """获取数据"""
        pass
    
    @abstractmethod
    async def get_schema(self) -> Dict[str, Any]:
        """获取数据模式"""
        pass
    
    @abstractmethod
    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """验证数据"""
        pass

# API接入适配器
class APIIngestionAdapter(DataIngestionAdapter):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config['base_url']
        self.headers = config.get('headers', {})
        self.auth = config.get('auth')
    
    async def connect(self) -> bool:
        # 实现API连接逻辑
        pass
    
    async def fetch_data(self, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        # 实现API数据获取
        pass

# CSV接入适配器
class CSVIngestionAdapter(DataIngestionAdapter):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.file_path = config['file_path']
        self.encoding = config.get('encoding', 'utf-8')
        self.delimiter = config.get('delimiter', ',')
    
    async def fetch_data(self, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        import aiofiles
        import csv
        
        async with aiofiles.open(self.file_path, 'r', encoding=self.encoding) as f:
            content = await f.read()
            reader = csv.DictReader(content.splitlines(), delimiter=self.delimiter)
            for row in reader:
                yield row

# 流式数据适配器
class StreamIngestionAdapter(DataIngestionAdapter):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.topic = config['topic']
        self.bootstrap_servers = config['bootstrap_servers']
    
    async def fetch_data(self, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        from aiokafka import AIOKafkaConsumer
        
        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers
        )
        
        await consumer.start()
        try:
            async for msg in consumer:
                yield json.loads(msg.value.decode('utf-8'))
        finally:
            await consumer.stop()
```

## 6. 数据质量引擎

### 6.1 质量规则定义
```python
from enum import Enum
from typing import Dict, Any, List
import json

class QualityRuleType(Enum):
    NOT_NULL = "not_null"
    UNIQUE = "unique"  
    RANGE = "range"
    PATTERN = "pattern"
    REFERENCE = "reference"
    CUSTOM = "custom"

class QualityRule:
    def __init__(self, rule_id: str, rule_type: QualityRuleType, 
                 target_table: str, target_field: str, 
                 config: Dict[str, Any], severity: str = "ERROR"):
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.target_table = target_table
        self.target_field = target_field
        self.config = config
        self.severity = severity
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据是否符合质量规则"""
        result = {
            'rule_id': self.rule_id,
            'passed': True,
            'errors': []
        }
        
        field_value = data.get(self.target_field)
        
        if self.rule_type == QualityRuleType.NOT_NULL:
            if field_value is None or field_value == '':
                result['passed'] = False
                result['errors'].append(f'Field {self.target_field} cannot be null')
        
        elif self.rule_type == QualityRuleType.UNIQUE:
            # 需要与数据库交互检查唯一性
            pass
            
        elif self.rule_type == QualityRuleType.RANGE:
            min_val = self.config.get('min')
            max_val = self.config.get('max')
            if min_val is not None and field_value < min_val:
                result['passed'] = False
                result['errors'].append(f'Field {self.target_field} below minimum {min_val}')
            if max_val is not None and field_value > max_val:
                result['passed'] = False
                result['errors'].append(f'Field {self.target_field} above maximum {max_val}')
        
        elif self.rule_type == QualityRuleType.PATTERN:
            import re
            pattern = self.config.get('pattern')
            if pattern and not re.match(pattern, str(field_value)):
                result['passed'] = False
                result['errors'].append(f'Field {self.target_field} does not match pattern {pattern}')
        
        return result

# 质量检查引擎
class QualityEngine:
    def __init__(self):
        self.rules: List[QualityRule] = []
    
    def add_rule(self, rule: QualityRule):
        self.rules.append(rule)
    
    def check_data_quality(self, table_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查数据质量"""
        applicable_rules = [rule for rule in self.rules if rule.target_table == table_name]
        
        total_records = len(data)
        passed_records = 0
        failed_records = 0
        error_details = []
        
        for record in data:
            record_passed = True
            record_errors = []
            
            for rule in applicable_rules:
                validation_result = rule.validate(record)
                if not validation_result['passed']:
                    record_passed = False
                    record_errors.extend(validation_result['errors'])
            
            if record_passed:
                passed_records += 1
            else:
                failed_records += 1
                error_details.append({
                    'record': record,
                    'errors': record_errors
                })
        
        return {
            'total_records': total_records,
            'passed_records': passed_records,
            'failed_records': failed_records,
            'pass_rate': passed_records / total_records if total_records > 0 else 0,
            'error_details': error_details
        }
```

## 7. 统一访问层设计

### 7.1 查询网关
```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from typing import Dict, List, Any, Optional
import json

class UnifiedQueryGateway:
    """统一查询网关"""
    
    def __init__(self):
        self.engines = {
            'hot': create_engine('postgresql://...'),
            'warm': create_engine('clickhouse://...'),
            'cold': self._get_s3_handler()
        }
    
    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行统一查询"""
        # 分析查询，确定数据层级
        target_tier = self._analyze_query_tier(query)
        
        if target_tier in ['hot', 'warm']:
            engine = self.engines[target_tier]
            with engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                return [dict(row) for row in result]
        elif target_tier == 'cold':
            return await self._query_cold_data(query, params)
        else:
            # 跨层查询，需要联邦查询
            return await self._federated_query(query, params)
    
    def _analyze_query_tier(self, query: str) -> str:
        """分析查询应该在哪个存储层执行"""
        query_lower = query.lower()
        
        # 简单的启发式规则
        if 'where' in query_lower and 'pub_time' in query_lower:
            if 'interval' in query_lower and '7 day' in query_lower:
                return 'hot'
            elif 'interval' in query_lower and '90 day' in query_lower:
                return 'warm'
            else:
                return 'cold'
        
        return 'hot'  # 默认热数据
    
    async def _query_cold_data(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查询冷数据"""
        # 实现S3查询逻辑
        pass
    
    async def _federated_query(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """联邦查询"""
        # 使用Trino/Presto进行跨存储查询
        pass

# GraphQL接口
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType

class NewsType(SQLAlchemyObjectType):
    class Meta:
        model = NewsUnified
        interfaces = (graphene.relay.Node,)

class Query(graphene.ObjectType):
    node = graphene.relay.Node.Field()
    
    news = graphene.List(
        NewsType,
        source_id=graphene.String(),
        category=graphene.String(),
        keywords=graphene.List(graphene.String),
        date_from=graphene.DateTime(),
        date_to=graphene.DateTime(),
        limit=graphene.Int(default_value=20)
    )
    
    def resolve_news(self, info, **kwargs):
        query = info.context['session'].query(NewsUnified)
        
        if kwargs.get('source_id'):
            query = query.filter(NewsUnified.source_id == kwargs['source_id'])
        
        if kwargs.get('category'):
            query = query.filter(NewsUnified.category == kwargs['category'])
        
        if kwargs.get('date_from'):
            query = query.filter(NewsUnified.pub_time >= kwargs['date_from'])
        
        if kwargs.get('date_to'):
            query = query.filter(NewsUnified.pub_time <= kwargs['date_to'])
        
        if kwargs.get('keywords'):
            # 实现关键词搜索
            pass
        
        return query.limit(kwargs['limit']).all()

schema = graphene.Schema(query=Query)
```

### 7.2 权限控制
```python
from functools import wraps
from typing import Callable, List
import jwt

class DataAccessController:
    """数据访问控制器"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """检查用户权限"""
        # 查询用户权限策略
        user_policies = self.db.query(UserDataAccess).filter(
            UserDataAccess.user_id == user_id
        ).all()
        
        for access in user_policies:
            policy = access.policy
            if self._match_resource_pattern(policy.resource_pattern, resource):
                if action in policy.permission_type:
                    return True
        
        return False
    
    def _match_resource_pattern(self, pattern: str, resource: str) -> bool:
        """匹配资源模式"""
        import fnmatch
        return fnmatch.fnmatch(resource, pattern)
    
    def filter_by_permission(self, query, user_id: str, table_name: str):
        """根据权限过滤查询结果"""
        # 获取用户的数据访问条件
        access_conditions = self._get_user_access_conditions(user_id, table_name)
        
        for condition in access_conditions:
            # 应用条件到查询
            if condition['type'] == 'time_range':
                query = query.filter(
                    getattr(query.column_descriptions[0]['type'], 'pub_time') >= condition['start_date'],
                    getattr(query.column_descriptions[0]['type'], 'pub_time') <= condition['end_date']
                )
            elif condition['type'] == 'source_filter':
                query = query.filter(
                    getattr(query.column_descriptions[0]['type'], 'source_id').in_(condition['allowed_sources'])
                )
        
        return query

def require_permission(resource: str, action: str):
    """权限装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从请求中获取用户信息
            user_id = kwargs.get('current_user', {}).get('user_id')
            
            if not user_id:
                raise HTTPException(status_code=401, detail="未认证")
            
            # 检查权限
            access_controller = DataAccessController(db_session)
            if not access_controller.check_permission(user_id, resource, action):
                raise HTTPException(status_code=403, detail="权限不足")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

## 8. 部署和运维

### 8.1 Docker容器化
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 Kubernetes部署
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: newslook-unified-db
spec:
  replicas: 3
  selector:
    matchLabels:
      app: newslook-unified-db
  template:
    metadata:
      labels:
        app: newslook-unified-db
    spec:
      containers:
      - name: app
        image: newslook/unified-db:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: newslook-unified-db-service
spec:
  selector:
    app: newslook-unified-db
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 8.3 监控配置
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'newslook-unified-db'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgresql'
    static_configs:
      - targets: ['localhost:5432']

  - job_name: 'clickhouse'
    static_configs:
      - targets: ['localhost:8123']
```

## 9. 性能优化策略

### 9.1 查询优化
- **索引策略**：基于查询模式创建复合索引
- **分区表**：按时间分区减少扫描数据量
- **物化视图**：预计算常用聚合查询
- **查询缓存**：Redis缓存热点查询结果

### 9.2 存储优化
- **数据压缩**：冷数据使用列式压缩存储
- **数据去重**：基于内容哈希的智能去重
- **分层存储**：自动数据生命周期管理
- **读写分离**：主从复制分离读写负载

### 9.3 并发优化
- **连接池**：数据库连接池管理
- **异步处理**：使用async/await处理I/O密集操作
- **批量操作**：批量插入和更新减少网络开销
- **负载均衡**：多实例负载均衡

## 10. 安全策略

### 10.1 数据加密
- **传输加密**：TLS/SSL加密网络传输
- **存储加密**：敏感字段AES加密
- **密钥管理**：使用专业密钥管理服务

### 10.2 访问控制
- **身份认证**：JWT Token + OAuth2.0
- **权限控制**：RBAC角色权限模型
- **审计日志**：完整的操作审计记录

### 10.3 数据脱敏
- **敏感数据识别**：自动识别PII数据
- **脱敏规则**：配置化脱敏策略
- **测试数据**：生产数据脱敏用于测试

这个统一数据库架构设计为NewsLook项目提供了：
1. **完整的多源数据接入能力**
2. **强大的数据治理功能** 
3. **灵活的存储分层策略**
4. **统一的访问接口**
5. **细粒度的权限控制**
6. **可扩展的技术架构**

通过这个架构，可以有效管理和利用各种财经新闻数据源，提供高质量的数据服务。
