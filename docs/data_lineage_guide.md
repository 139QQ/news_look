# NewsLook 数据谱系管理指南

## 🎯 概述

数据谱系（Data Lineage）是NewsLook数据架构的核心组件，用于自动追踪数据的来源、转换过程和流向。通过完整的血缘关系记录，实现数据治理、影响分析和合规审计。

## 🏗️ 架构组件

### 核心组件
```
📦 数据谱系架构
├── 🧠 DataLineageManager     # 数据血缘管理器
├── 🔍 LineageTracker         # 自动追踪装饰器  
├── 🌐 LineageAPI            # REST API接口
├── 📊 质量监控引擎            # 数据质量检查
└── 📈 可视化组件             # 血缘关系图谱
```

### 数据流向追踪
```
🌐 外部数据源 → 🕷️ 爬虫组件 → 🗄️ 原始数据库 → 🧹 数据清洗 → 📊 智能分析 → 🌐 API输出
    ↓血缘追踪    ↓血缘追踪    ↓血缘追踪    ↓血缘追踪    ↓血缘追踪    ↓血缘追踪
    📋 谱系记录   📋 谱系记录   📋 谱系记录   📋 谱系记录   📋 谱系记录   📋 谱系记录
```

## 🚀 快速开始

### 1. 初始化数据谱系
```bash
# 运行初始化脚本
python scripts/setup_data_lineage.py
```

### 2. 在爬虫中使用追踪装饰器
```python
from backend.newslook.core.lineage_tracker import track_crawler

@track_crawler(
    source_name="新浪财经",
    source_url="https://finance.sina.com.cn",
    target_table="news_data",
    field_mapping={
        'title': 'title',
        'content': 'content',
        'time': 'pub_time',
        'link': 'url'
    }
)
async def crawl_sina_finance(url):
    # 爬虫逻辑
    news_data = await fetch_news(url)
    return news_data
```

### 3. 在API中使用追踪装饰器
```python
from backend.newslook.core.lineage_tracker import track_api

@track_api(
    endpoint="/api/news/list",
    source_table="news_data",
    query_fields=['title', 'content', 'pub_time']
)
async def get_news_list(request):
    # API逻辑
    return {"news": news_list}
```

## 📋 核心功能

### 1. 血缘关系查询
```python
from backend.newslook.core.data_lineage_manager import get_lineage_manager

# 获取表的血缘关系
lineage_manager = get_lineage_manager()
lineage_data = await lineage_manager.get_lineage_by_table(
    table_name="news_data",
    direction="both"  # upstream/downstream/both
)

print(f"上游数据源: {len(lineage_data['upstream'])}")
print(f"下游处理: {len(lineage_data['downstream'])}")
```

### 2. 影响分析
```python
# 分析字段变更的影响范围
impact_data = await lineage_manager.analyze_impact(
    table_name="news_data",
    field_name="title",
    max_depth=5
)

print(f"影响对象数量: {impact_data['total_affected_count']}")
print(f"涉及系统: {impact_data['affected_systems']}")
```

### 3. 数据质量监控
```python
# 记录数据转换血缘
await lineage_manager.record_transformation_lineage(
    source_table="news_raw",
    target_table="news_cleaned", 
    transformation_type="数据清洗",
    transformation_rule="去除HTML标签和重复内容",
    field_mappings=[
        {
            "source_field": "raw_content",
            "target_field": "clean_content",
            "transform_logic": "HTML标签清理 + 内容去重"
        }
    ]
)
```

## 🌐 REST API 接口

### 1. 获取表血缘关系
```http
GET /api/lineage/table/news_data?direction=both&format=graph
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "table_name": "news_data",
    "upstream": [
      {
        "source_system": "external",
        "source_table": "新浪财经",
        "transformation_type": "crawler_source"
      }
    ],
    "downstream": [
      {
        "target_system": "newslook",
        "target_table": "news_cleaned",
        "transformation_type": "data_transformation"
      }
    ]
  }
}
```

### 2. 影响分析
```http
GET /api/lineage/impact/news_data?field=title&max_depth=3
```

### 3. 搜索血缘关系
```http
GET /api/lineage/search?q=title&type=field&limit=10
```

### 4. 生成谱系报告
```http
GET /api/lineage/report?tables=news_data,news_cleaned&start_date=2024-01-01
```

## 📊 数据可视化

### 血缘关系图
```javascript
// 前端可视化示例
const lineageGraph = {
  nodes: [
    { id: 'sina', label: '新浪财经', type: 'source' },
    { id: 'news_data', label: 'news_data', type: 'table' },
    { id: 'api', label: '/api/news', type: 'target' }
  ],
  edges: [
    { source: 'sina', target: 'news_data', label: '爬虫采集' },
    { source: 'news_data', target: 'api', label: 'API输出' }
  ]
};
```

## 🎛️ 高级配置

### 1. 配置文件设置
```yaml
# configs/app.yaml
data_lineage:
  enabled: true
  cache_ttl: 3600  # 缓存时间(秒)
  auto_discover: true  # 自动发现血缘关系
  quality_checks: true  # 启用质量检查
  retention_days: 365  # 血缘记录保留天数
```

### 2. 自定义追踪器
```python
from backend.newslook.core.lineage_tracker import LineageTracker

# 创建自定义追踪器
custom_tracker = LineageTracker()

# 禁用特定操作的追踪
custom_tracker.disable_tracking()

# 使用上下文管理器
async with LineageContext("数据迁移") as ctx:
    # 执行数据操作
    pass
```

## 🔧 故障排除

### 常见问题

1. **血缘记录失败**
   ```python
   # 检查数据库连接
   async with lineage_manager.get_db_connection() as conn:
       cursor = conn.cursor()
       await cursor.execute("SELECT COUNT(*) FROM data_lineage")
       count = await cursor.fetchone()
       print(f"血缘记录数: {count[0]}")
   ```

2. **缓存问题**
   ```python
   # 清理缓存
   lineage_manager.clear_cache()
   ```

3. **性能优化**
   ```python
   # 批量清理旧记录
   await lineage_manager.cleanup_old_lineage(retention_days=180)
   ```

## 📈 监控指标

### 关键指标
- **血缘覆盖率**: 有血缘记录的表/字段比例
- **追踪成功率**: 成功记录血缘关系的操作比例  
- **查询响应时间**: 血缘查询的平均响应时间
- **影响分析深度**: 平均影响分析层级数

### 健康检查
```http
GET /api/lineage/health
```

```json
{
  "status": "healthy",
  "metrics": {
    "total_relations": 1250,
    "active_tables": 15,
    "cache_hit_rate": 0.85,
    "avg_query_time": "120ms"
  }
}
```

## 🎯 最佳实践

### 1. 装饰器使用
- ✅ 在数据源头使用 `@track_crawler`
- ✅ 在API端点使用 `@track_api`  
- ✅ 在数据转换函数使用 `@track_transformation`
- ❌ 避免在频繁调用的内部函数上使用

### 2. 字段映射
- ✅ 提供详细的字段映射关系
- ✅ 包含转换逻辑说明
- ✅ 使用有意义的字段名
- ❌ 避免空映射或不准确的映射

### 3. 性能优化
- ✅ 使用批量操作减少数据库调用
- ✅ 合理设置缓存TTL
- ✅ 定期清理历史数据
- ❌ 避免在高频操作中进行复杂血缘查询

## 🚀 未来规划

### Phase 2 增强功能
- [ ] 实时血缘流计算
- [ ] 机器学习驱动的自动发现
- [ ] 跨系统血缘同步
- [ ] 3D可视化血缘图谱
- [ ] 智能影响预测

### 集成计划
- [ ] 与Apache Atlas集成
- [ ] 与DataHub联邦
- [ ] Kafka血缘追踪
- [ ] Spark任务血缘自动发现

---

💡 **提示**: 数据谱系是数据治理的基石，建议在项目初期就开始使用，确保数据流向的完整可追溯性。 