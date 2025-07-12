# NewsLook API 使用指南

## 📋 API快速参考表

| API端点 | 方法 | 功能描述 | 响应时间 | 状态 |
|---------|------|----------|----------|------|
| `/api/health` | GET | 系统健康检查 | ~15ms | ✅ 正常 |
| `/api/stats` | GET | 系统统计数据 | ~25ms | ✅ 正常 |
| `/api/news` | GET | 获取新闻列表 | ~45ms | ✅ 正常 |
| `/api/news/{id}` | GET | 获取单条新闻 | ~20ms | ✅ 正常 |
| `/api/crawler/status` | GET | 爬虫状态监控 | ~30ms | ✅ 正常 |
| `/api/analytics/overview` | GET | 数据分析概览 | ~170ms | ✅ 正常 |

## 🚀 快速开始指南

### 1. 验证API服务状态
```bash
# 检查API服务是否运行
curl -s http://localhost:5000/api/health | jq '.'

# 预期响应
{
  "status": "healthy",
  "timestamp": "2025-06-29T10:30:00Z",
  "version": "4.1.0",
  "database": "connected",
  "services": {
    "crawler": "ready",
    "web": "running"
  }
}
```

### 2. 获取系统统计
```bash
# 获取基础统计信息
curl -s http://localhost:5000/api/stats | jq '.'

# 获取详细统计（包含图表数据）
curl -s "http://localhost:5000/api/stats?include_charts=true" | jq '.'
```

### 3. 查询新闻数据
```bash
# 获取最新10条新闻
curl -s "http://localhost:5000/api/news?limit=10" | jq '.data[0]'

# 按来源筛选
curl -s "http://localhost:5000/api/news?source=东方财富&limit=5" | jq '.'

# 按时间范围查询
curl -s "http://localhost:5000/api/news?date_from=2025-01-01&limit=20" | jq '.'
```

## 🔥 核心数据API详解

### 健康检查API
```http
GET /api/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-29T10:30:00Z",
  "version": "4.1.0",
  "uptime_seconds": 3600,
  "database": {
    "status": "connected",
    "total_news": 47,
    "last_update": "2025-06-29T10:25:00Z"
  },
  "services": {
    "crawler": "ready",
    "web": "running",
    "api": "available"
  },
  "memory_usage": "45.2MB",
  "disk_space": "2.1GB available"
}
```

### 新闻查询API
```http
GET /api/news?page=1&limit=20&source=东方财富
```

**参数说明**:
- `page`: 页码 (默认: 1)
- `limit`: 每页数量 (默认: 20, 最大: 100)
- `source`: 新闻来源筛选
- `date_from`: 开始日期 (YYYY-MM-DD)
- `date_to`: 结束日期 (YYYY-MM-DD)
- `keyword`: 关键词搜索

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": "eastmoney_20250629_001",
      "title": "A股市场今日收盘分析",
      "content": "今日A股三大指数...",
      "source": "东方财富",
      "pub_time": "2025-06-29T15:30:00Z",
      "url": "https://finance.eastmoney.com/...",
      "author": "财经编辑部",
      "keywords": ["A股", "收盘", "分析"],
      "category": "股市动态"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 47,
    "pages": 3
  },
  "filters": {
    "source": "东方财富",
    "date_range": "2025-06-29"
  },
  "response_time_ms": 45
}
```

### 爬虫状态API
```http
GET /api/crawler/status
```

**响应示例**:
```json
{
  "success": true,
  "summary": {
    "total_crawlers": 5,
    "running": 0,
    "stopped": 5,
    "total_news": 47,
    "last_run": "2025-06-29T10:25:00Z"
  },
  "crawlers": [
    {
      "name": "东方财富",
      "status": "stopped",
      "last_run": "2025-06-29T10:25:00Z",
      "total_crawled": 12,
      "error_count": 0,
      "success_rate": "100%"
    }
  ]
}
```

### 数据分析API
```http
GET /api/analytics/overview
```

**响应示例**:
```json
{
  "success": true,
  "overview": {
    "total_news": 47,
    "today_news": 12,
    "total_sources": 5,
    "active_sources": 5,
    "last_update": "2025-06-29T10:25:00Z",
    "avg_daily_news": 15.6
  },
  "trends": {
    "daily_growth": "+8.3%",
    "weekly_growth": "+12.1%",
    "monthly_growth": "+45.2%"
  },
  "top_sources": [
    {"name": "东方财富", "count": 12, "percentage": 25.5},
    {"name": "腾讯财经", "count": 10, "percentage": 21.3}
  ]
}
```

## 📚 实际应用场景

### 场景1：数据监控仪表盘
```javascript
// 创建实时监控仪表盘
async function createDashboard() {
  try {
    // 并行获取多个API数据
    const [healthResponse, statsResponse, analyticsResponse] = await Promise.all([
      fetch('/api/health'),
      fetch('/api/stats?include_charts=true'),
      fetch('/api/analytics/overview')
    ]);
    
    const health = await healthResponse.json();
    const stats = await statsResponse.json();
    const analytics = await analyticsResponse.json();
    
    // 更新仪表盘
    updateDashboard(health, stats, analytics);
    
    console.log('✅ 仪表盘数据已更新');
  } catch (error) {
    console.error('❌ 仪表盘更新失败:', error);
  }
}

// 每30秒自动更新
setInterval(createDashboard, 30000);
```

### 场景2：新闻搜索应用
```javascript
// 高级新闻搜索功能
async function searchNews(params) {
  const searchParams = new URLSearchParams({
    keyword: params.keyword || '',
    source: params.source || '',
    date_from: params.dateFrom || '',
    date_to: params.dateTo || '',
    page: params.page || 1,
    limit: params.limit || 20
  });
  
  try {
    const response = await fetch(`/api/news?${searchParams}`);
    const data = await response.json();
    
    if (data.success) {
      displayNewsResults(data.data);
      updatePagination(data.pagination);
    }
  } catch (error) {
    console.error('搜索失败:', error);
  }
}

// 使用示例
searchNews({
  keyword: '股市',
  source: '东方财富',
  dateFrom: '2025-06-01',
  limit: 10
});
```

### 场景3：数据分析图表
```javascript
// 使用ECharts创建数据分析图表
async function createAnalyticsCharts() {
  try {
    const response = await fetch('/api/analytics/echarts/data');
    const chartsData = await response.json();
    
    if (chartsData.success) {
      // 创建趋势图
      const trendChart = echarts.init(document.getElementById('trend-chart'));
      trendChart.setOption({
        title: { text: '新闻趋势图' },
        xAxis: { data: chartsData.trend_data.dates },
        yAxis: { type: 'value' },
        series: [{
          name: '新闻数量',
          type: 'line',
          data: chartsData.trend_data.counts,
          smooth: true
        }]
      });
      
      // 创建来源分布饼图
      const pieChart = echarts.init(document.getElementById('source-pie'));
      pieChart.setOption({
        title: { text: '新闻来源分布' },
        series: [{
          type: 'pie',
          radius: '70%',
          data: chartsData.source_data
        }]
      });
    }
  } catch (error) {
    console.error('图表创建失败:', error);
  }
}
```

## 🧪 API测试工具

### 完整API验证脚本
```python
#!/usr/bin/env python3
"""
NewsLook API完整验证工具
"""
import requests
import json
import time

def test_api_endpoints():
    base_url = "http://localhost:5000"
    
    tests = [
        {
            "name": "健康检查",
            "url": f"{base_url}/api/health",
            "expected_status": 200,
            "expected_keys": ["status", "version", "database"]
        },
        {
            "name": "系统统计",
            "url": f"{base_url}/api/stats",
            "expected_status": 200,
            "expected_keys": ["total_news", "sources"]
        },
        {
            "name": "新闻查询",
            "url": f"{base_url}/api/news?limit=5",
            "expected_status": 200,
            "expected_keys": ["success", "data", "pagination"]
        },
        {
            "name": "爬虫状态",
            "url": f"{base_url}/api/crawler/status",
            "expected_status": 200,
            "expected_keys": ["success", "summary", "crawlers"]
        }
    ]
    
    print("🧪 开始API测试...")
    results = []
    
    for test in tests:
        print(f"  测试: {test['name']}")
        try:
            start_time = time.time()
            response = requests.get(test['url'], timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == test['expected_status']:
                data = response.json()
                missing_keys = [key for key in test['expected_keys'] if key not in data]
                
                if not missing_keys:
                    print(f"    ✅ 通过 ({response_time:.1f}ms)")
                    results.append({"test": test['name'], "status": "PASS", "time": response_time})
                else:
                    print(f"    ❌ 缺少字段: {missing_keys}")
                    results.append({"test": test['name'], "status": "FAIL", "error": f"缺少字段: {missing_keys}"})
            else:
                print(f"    ❌ HTTP {response.status_code}")
                results.append({"test": test['name'], "status": "FAIL", "error": f"HTTP {response.status_code}"})
                
        except Exception as e:
            print(f"    ❌ 异常: {e}")
            results.append({"test": test['name'], "status": "FAIL", "error": str(e)})
    
    # 生成测试报告
    passed = len([r for r in results if r['status'] == 'PASS'])
    total = len(results)
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    if passed == total:
        print("🎉 所有API测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查服务状态")
    
    return results

if __name__ == "__main__":
    test_api_endpoints()
```

## 📅 版本与开发路线图

### 当前版本: v1.0 (稳定)

**已实现功能**:
- ✅ 6个核心API端点全部可用
- ✅ 完整的数据查询和筛选功能
- ✅ 实时爬虫状态监控
- ✅ 基础数据分析和统计
- ✅ 标准化JSON响应格式
- ✅ 完善的错误处理机制

### 计划版本: v1.1 (2025年Q3)

**新增功能**:
- 🔄 实时数据流API - WebSocket推送
- 🔍 高级搜索API - 全文搜索和关键词匹配
- 📈 性能监控API - 系统指标和告警
- 🗂️ 数据导出API - 支持CSV/Excel/JSON格式

### 未来版本: v2.0 (现代化架构)

**长期规划**:
- 🏗️ PostgreSQL + ClickHouse 双引擎
- ⚡ 分布式架构支持
- 🔐 OAuth2 认证系统
- 📊 高级分析引擎 (机器学习)
- 🌐 多语言支持

## ⚠️ API使用注意事项

### 1. 兼容性保证
- 当前所有v1 API保证向后兼容
- 新增功能通过版本号区分 (v1, v2)
- 废弃API会提前6个月通知

### 2. 限流和配额
```bash
# 当前无限流限制，推荐合理使用
# 单个IP建议: 100请求/分钟
# 批量操作建议: 添加适当延时
```

### 3. 错误码说明
| HTTP状态码 | 含义 | 处理建议 |
|------------|------|----------|
| 200 | 成功 | 正常处理 |
| 400 | 参数错误 | 检查请求参数 |
| 404 | 资源不存在 | 检查URL路径 |
| 500 | 服务器错误 | 稍后重试或联系支持 |
| 503 | 服务不可用 | 系统维护中，稍后重试 |

## 🔧 开发者工具

### 1. API测试工具
```bash
# 内置验证脚本
python verify_api_improvements.py

# 手动测试健康检查
curl http://localhost:5000/api/health

# 批量API测试
python test_api_response.py
```

### 2. 调试模式
```bash
# 启用详细日志
python app.py --debug

# 查看API请求日志
tail -f data/logs/app.log
```

## 🤝 反馈与支持

如果您在使用API时遇到问题或有改进建议：

1. **问题报告**: 请在项目Issues中提交
2. **功能建议**: 欢迎提出您的需求
3. **技术支持**: 提供详细的错误信息和重现步骤
4. **贡献代码**: 欢迎提交Pull Request

**联系方式**:
- GitHub Issues: [项目仓库](https://github.com/yourusername/NewsLook/issues)
- API文档更新: 本README会随版本更新保持同步

---

*最后更新: 2025-06-29*  
*API版本: v1.0*  
*文档状态: ✅ 完整且已验证* 