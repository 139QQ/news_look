# API 文档

本文档详细说明了金融新闻爬虫系统提供的API接口，供开发者集成使用。

## 1. API 概述

金融新闻爬虫系统提供了一套RESTful API，允许您以编程方式获取、管理和操作金融新闻数据。所有API请求均使用HTTP协议，响应数据格式为JSON。

### 1.1 基本URL

```
http://localhost:5000/api/v1
```

### 1.2 认证

API使用基于令牌的认证机制。在请求头中包含您的API令牌：

```
Authorization: Bearer your_api_token_here
```

可以通过管理界面生成API令牌。

### 1.3 请求限制

为防止滥用，API请求限制为每个IP地址每分钟60次请求。超过限制将返回429状态码。

### 1.4 通用返回格式

所有API响应均使用以下JSON格式：

```json
{
  "status": "success",  // 或 "error"
  "data": {},           // 成功时返回的数据
  "message": "",        // 错误消息（如果有）
  "code": 200           // HTTP状态码
}
```

## 2. 新闻数据接口

### 2.1 获取新闻列表

获取符合条件的新闻列表。

**请求**：

```
GET /api/v1/news
```

**参数**：

| 参数名 | 类型 | 必须 | 描述 |
|-------|------|------|------|
| source | 字符串 | 否 | 新闻来源筛选，如 "东方财富" |
| category | 字符串 | 否 | 新闻分类，如 "期货", "股票" |
| start_date | 字符串 | 否 | 开始日期，格式：YYYY-MM-DD |
| end_date | 字符串 | 否 | 结束日期，格式：YYYY-MM-DD |
| keywords | 字符串 | 否 | 关键词搜索 |
| page | 整数 | 否 | 页码，默认为1 |
| per_page | 整数 | 否 | 每页条数，默认为20，最大100 |

**响应**：

```json
{
  "status": "success",
  "data": {
    "news": [
      {
        "id": 1,
        "title": "市场情绪回暖，A股迎来反弹",
        "url": "https://example.com/news/12345",
        "source": "东方财富",
        "category": "股票",
        "date": "2023-06-01",
        "summary": "市场情绪回暖，沪深两市今日小幅上涨...",
        "created_at": "2023-06-01T08:30:00Z"
      },
      // 更多新闻...
    ],
    "total": 1520,
    "page": 1,
    "per_page": 20,
    "total_pages": 76
  },
  "code": 200
}
```

### 2.2 获取单条新闻详情

通过ID获取单条新闻的完整信息。

**请求**：

```
GET /api/v1/news/{id}
```

**参数**：无

**响应**：

```json
{
  "status": "success",
  "data": {
    "id": 1,
    "title": "市场情绪回暖，A股迎来反弹",
    "content": "完整的新闻内容...",
    "url": "https://example.com/news/12345",
    "source": "东方财富",
    "category": "股票",
    "date": "2023-06-01",
    "keywords": ["A股", "反弹", "股市"],
    "created_at": "2023-06-01T08:30:00Z",
    "updated_at": "2023-06-01T08:30:00Z"
  },
  "code": 200
}
```

### 2.3 搜索新闻

全文搜索新闻内容。

**请求**：

```
GET /api/v1/news/search
```

**参数**：

| 参数名 | 类型 | 必须 | 描述 |
|-------|------|------|------|
| q | 字符串 | 是 | 搜索查询词 |
| source | 字符串 | 否 | 新闻来源筛选 |
| start_date | 字符串 | 否 | 开始日期，格式：YYYY-MM-DD |
| end_date | 字符串 | 否 | 结束日期，格式：YYYY-MM-DD |
| page | 整数 | 否 | 页码，默认为1 |
| per_page | 整数 | 否 | 每页条数，默认为20 |

**响应**：

```json
{
  "status": "success",
  "data": {
    "news": [
      // 新闻列表...
    ],
    "total": 42,
    "page": 1,
    "per_page": 20,
    "total_pages": 3
  },
  "code": 200
}
```

### 2.4 获取新闻统计

获取新闻的统计数据。

**请求**：

```
GET /api/v1/news/stats
```

**参数**：

| 参数名 | 类型 | 必须 | 描述 |
|-------|------|------|------|
| start_date | 字符串 | 否 | 开始日期，格式：YYYY-MM-DD |
| end_date | 字符串 | 否 | 结束日期，格式：YYYY-MM-DD |
| group_by | 字符串 | 否 | 分组方式，可选：'source', 'category', 'date' |

**响应**：

```json
{
  "status": "success",
  "data": {
    "total_news": 15243,
    "by_source": {
      "东方财富": 8765,
      "新浪财经": 4321,
      "其他来源": 2157
    },
    "by_category": {
      "股票": 7890,
      "期货": 3210,
      "外汇": 2143,
      "其他": 2000
    },
    "by_date": {
      "2023-06-01": 521,
      "2023-05-31": 498,
      // 更多日期...
    }
  },
  "code": 200
}
```

## 3. 爬虫管理接口

### 3.1 获取所有爬虫

获取系统中所有可用的爬虫。

**请求**：

```
GET /api/v1/crawlers
```

**参数**：无

**响应**：

```json
{
  "status": "success",
  "data": {
    "crawlers": [
      {
        "id": "eastmoney",
        "name": "东方财富",
        "status": "ready",
        "last_run": "2023-06-01T10:00:00Z",
        "supported_categories": ["股票", "期货", "外汇", "黄金"]
      },
      {
        "id": "sina",
        "name": "新浪财经",
        "status": "running",
        "last_run": "2023-06-01T09:00:00Z",
        "supported_categories": ["股票", "财经"]
      }
      // 更多爬虫...
    ]
  },
  "code": 200
}
```

### 3.2 运行爬虫任务

触发爬虫任务的执行。

**请求**：

```
POST /api/v1/crawlers/{crawler_id}/run
```

**参数**：

| 参数名 | 类型 | 必须 | 描述 |
|-------|------|------|------|
| days | 整数 | 否 | 爬取过去几天的新闻，默认为1 |
| max_news | 整数 | 否 | 最多爬取的新闻数量 |
| categories | 数组 | 否 | 要爬取的新闻类别 |

**请求体示例**：

```json
{
  "days": 3,
  "max_news": 100,
  "categories": ["期货", "外汇"]
}
```

**响应**：

```json
{
  "status": "success",
  "data": {
    "task_id": "task_12345678",
    "crawler": "eastmoney",
    "status": "started",
    "started_at": "2023-06-02T14:30:00Z"
  },
  "code": 200
}
```

### 3.3 获取任务状态

获取爬虫任务的执行状态。

**请求**：

```
GET /api/v1/tasks/{task_id}
```

**参数**：无

**响应**：

```json
{
  "status": "success",
  "data": {
    "task_id": "task_12345678",
    "crawler": "eastmoney",
    "status": "completed", // 可能值：'started', 'running', 'completed', 'failed'
    "progress": 100,
    "started_at": "2023-06-02T14:30:00Z",
    "completed_at": "2023-06-02T14:35:12Z",
    "results": {
      "total_found": 87,
      "new_added": 65,
      "failed": 2
    },
    "error": null
  },
  "code": 200
}
```

### 3.4 取消运行中的任务

取消正在运行的爬虫任务。

**请求**：

```
DELETE /api/v1/tasks/{task_id}
```

**参数**：无

**响应**：

```json
{
  "status": "success",
  "data": {
    "task_id": "task_12345678",
    "status": "cancelled"
  },
  "code": 200
}
```

## 4. 用户管理接口

### 4.1 用户登录

获取API访问令牌。

**请求**：

```
POST /api/v1/auth/login
```

**请求体**：

```json
{
  "username": "admin",
  "password": "your_password"
}
```

**响应**：

```json
{
  "status": "success",
  "data": {
    "token": "your_api_token_here",
    "expires_at": "2023-07-02T14:30:00Z",
    "user": {
      "id": 1,
      "username": "admin",
      "role": "administrator"
    }
  },
  "code": 200
}
```

### 4.2 创建API密钥

创建新的API访问密钥。

**请求**：

```
POST /api/v1/auth/api-keys
```

**请求体**：

```json
{
  "name": "My API Key",
  "expires_in": 30  // 有效天数，0表示永不过期
}
```

**响应**：

```json
{
  "status": "success",
  "data": {
    "api_key": "new_api_key_value",
    "id": "key_12345",
    "name": "My API Key",
    "created_at": "2023-06-02T14:30:00Z",
    "expires_at": "2023-07-02T14:30:00Z"
  },
  "code": 200
}
```

**注意**：API密钥只会在创建时显示一次，请妥善保存。

### 4.3 获取API密钥列表

获取当前用户的所有API密钥。

**请求**：

```
GET /api/v1/auth/api-keys
```

**参数**：无

**响应**：

```json
{
  "status": "success",
  "data": {
    "api_keys": [
      {
        "id": "key_12345",
        "name": "My API Key",
        "created_at": "2023-06-02T14:30:00Z",
        "expires_at": "2023-07-02T14:30:00Z",
        "last_used": "2023-06-02T15:10:00Z"
      },
      // 更多API密钥...
    ]
  },
  "code": 200
}
```

### 4.4 撤销API密钥

撤销API密钥的访问权限。

**请求**：

```
DELETE /api/v1/auth/api-keys/{key_id}
```

**参数**：无

**响应**：

```json
{
  "status": "success",
  "data": {
    "id": "key_12345",
    "revoked": true
  },
  "code": 200
}
```

## 5. 数据导出接口

### 5.1 导出新闻数据

导出符合条件的新闻数据为不同格式。

**请求**：

```
GET /api/v1/export/news
```

**参数**：

| 参数名 | 类型 | 必须 | 描述 |
|-------|------|------|------|
| format | 字符串 | 是 | 导出格式，可选：'csv', 'json', 'excel' |
| source | 字符串 | 否 | 新闻来源筛选 |
| category | 字符串 | 否 | 新闻类别筛选 |
| start_date | 字符串 | 否 | 开始日期，格式：YYYY-MM-DD |
| end_date | 字符串 | 否 | 结束日期，格式：YYYY-MM-DD |
| fields | 字符串 | 否 | 导出字段，逗号分隔，例如：'id,title,date,source' |

**响应**：

导出文件的二进制流，头信息中包含适当的Content-Type和Content-Disposition。

### 5.2 创建导出任务

创建后台导出任务，适用于大数据量导出。

**请求**：

```
POST /api/v1/export/tasks
```

**请求体**：

```json
{
  "format": "csv",
  "query": {
    "source": "东方财富",
    "start_date": "2023-01-01",
    "end_date": "2023-06-01"
  },
  "fields": ["id", "title", "content", "date", "source", "category"],
  "notify_email": "user@example.com"
}
```

**响应**：

```json
{
  "status": "success",
  "data": {
    "task_id": "export_12345678",
    "status": "queued",
    "created_at": "2023-06-02T14:30:00Z"
  },
  "code": 200
}
```

### 5.3 获取导出任务状态

获取导出任务的执行状态。

**请求**：

```
GET /api/v1/export/tasks/{task_id}
```

**参数**：无

**响应**：

```json
{
  "status": "success",
  "data": {
    "task_id": "export_12345678",
    "status": "completed", // 可能值：'queued', 'processing', 'completed', 'failed'
    "progress": 100,
    "created_at": "2023-06-02T14:30:00Z",
    "completed_at": "2023-06-02T14:35:12Z",
    "file_url": "https://example.com/downloads/export_12345678.csv",
    "file_size": 1540982,
    "expires_at": "2023-06-09T14:35:12Z",
    "error": null
  },
  "code": 200
}
```

## 6. 系统状态接口

### 6.1 获取系统状态

获取系统的运行状态和健康信息。

**请求**：

```
GET /api/v1/system/status
```

**参数**：无

**响应**：

```json
{
  "status": "success",
  "data": {
    "status": "healthy",
    "version": "1.2.3",
    "uptime": 1234567, // 秒
    "database": {
      "status": "connected",
      "total_news": 15243,
      "last_update": "2023-06-02T12:30:45Z"
    },
    "crawlers": {
      "total": 5,
      "active": 3,
      "running": 1
    },
    "tasks": {
      "queued": 2,
      "running": 1,
      "completed_today": 15
    },
    "system": {
      "cpu_usage": 34.5, // 百分比
      "memory_usage": 67.2, // 百分比
      "disk_usage": 45.3 // 百分比
    }
  },
  "code": 200
}
```

### 6.2 获取日志

获取系统日志。

**请求**：

```
GET /api/v1/system/logs
```

**参数**：

| 参数名 | 类型 | 必须 | 描述 |
|-------|------|------|------|
| level | 字符串 | 否 | 日志级别筛选，可选：'debug', 'info', 'warning', 'error', 'critical' |
| source | 字符串 | 否 | 日志来源筛选，例如爬虫名称 |
| start_time | 字符串 | 否 | 开始时间，ISO格式 |
| end_time | 字符串 | 否 | 结束时间，ISO格式 |
| limit | 整数 | 否 | 返回条数，默认100，最大1000 |

**响应**：

```json
{
  "status": "success",
  "data": {
    "logs": [
      {
        "timestamp": "2023-06-02T14:32:15Z",
        "level": "INFO",
        "source": "eastmoney",
        "message": "爬虫任务开始执行，目标：东方财富网"
      },
      {
        "timestamp": "2023-06-02T14:32:20Z",
        "level": "INFO",
        "source": "eastmoney",
        "message": "成功获取45个新闻链接"
      },
      {
        "timestamp": "2023-06-02T14:33:05Z",
        "level": "WARNING",
        "source": "eastmoney",
        "message": "内容解析失败：https://example.com/news/12346"
      },
      // 更多日志...
    ],
    "total": 543
  },
  "code": 200
}
```

## 7. 错误码

以下是API可能返回的错误码及其含义：

| 错误码 | 描述 |
|-------|------|
| 400 | 无效请求，通常是参数错误 |
| 401 | 认证失败，令牌无效或已过期 |
| 403 | 权限不足，无法执行请求的操作 |
| 404 | 请求的资源不存在 |
| 429 | 请求过于频繁，超过限制 |
| 500 | 服务器内部错误 |
| 503 | 服务暂时不可用，可能是维护或过载 |

错误响应示例：

```json
{
  "status": "error",
  "message": "API密钥无效或已过期",
  "code": 401,
  "data": null
}
```

## 8. 批量操作

### 8.1 批量获取新闻

批量获取多条新闻的详情。

**请求**：

```
POST /api/v1/news/batch
```

**请求体**：

```json
{
  "ids": [1, 2, 3, 4, 5]
}
```

**响应**：

```json
{
  "status": "success",
  "data": {
    "news": [
      {
        "id": 1,
        "title": "新闻标题1",
        // 其他字段...
      },
      {
        "id": 2,
        "title": "新闻标题2",
        // 其他字段...
      },
      // 更多新闻...
    ],
    "not_found": []
  },
  "code": 200
}
```

## 9. Webhook

系统支持以下类型的Webhook通知：

### 9.1 创建Webhook

创建新的Webhook订阅。

**请求**：

```
POST /api/v1/webhooks
```

**请求体**：

```json
{
  "name": "我的Webhook",
  "url": "https://example.com/webhook",
  "events": ["crawler.completed", "export.completed"],
  "secret": "your_webhook_secret"
}
```

`events` 可选值：
- `crawler.started` - 爬虫任务开始
- `crawler.completed` - 爬虫任务完成
- `crawler.failed` - 爬虫任务失败
- `export.completed` - 数据导出完成
- `system.alert` - 系统警报

**响应**：

```json
{
  "status": "success",
  "data": {
    "id": "webhook_12345",
    "name": "我的Webhook",
    "url": "https://example.com/webhook",
    "events": ["crawler.completed", "export.completed"],
    "created_at": "2023-06-02T14:30:00Z"
  },
  "code": 200
}
```

### 9.2 Webhook载荷示例

```json
{
  "event": "crawler.completed",
  "timestamp": "2023-06-02T14:35:12Z",
  "data": {
    "task_id": "task_12345678",
    "crawler": "eastmoney",
    "results": {
      "total_found": 87,
      "new_added": 65,
      "failed": 2
    }
  }
}
```

Webhook请求会包含`X-API-Signature`头，用于验证请求的真实性。它是使用您配置的secret对请求体进行HMAC-SHA256计算得到的。

## 10. 使用示例

### 10.1 Python示例

使用Python请求新闻列表：

```python
import requests

API_URL = "http://localhost:5000/api/v1"
API_TOKEN = "your_api_token_here"

headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

# 获取最近7天的外汇新闻
params = {
    "category": "外汇",
    "start_date": "2023-05-26",
    "end_date": "2023-06-02"
}

response = requests.get(f"{API_URL}/news", headers=headers, params=params)
if response.status_code == 200:
    news_data = response.json()
    for news in news_data["data"]["news"]:
        print(f"{news['date']} - {news['title']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

### 10.2 Shell示例

使用curl获取系统状态：

```bash
curl -X GET "http://localhost:5000/api/v1/system/status" \
  -H "Authorization: Bearer your_api_token_here"
```

### 10.3 触发爬虫任务：

```bash
curl -X POST "http://localhost:5000/api/v1/crawlers/eastmoney/run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_token_here" \
  -d '{"days": 3, "categories": ["期货", "外汇"]}'
```

## 11. 更新历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2023-01-15 | 初始API版本发布 |
| v1.1 | 2023-03-20 | 添加批量操作和导出功能 |
| v1.2 | 2023-05-10 | 添加Webhook支持和系统状态API | 