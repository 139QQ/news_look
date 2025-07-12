# NewsLook WebSocket 功能指南

## 🚀 概述

NewsLook Web界面现已集成WebSocket实时通信功能，提供：
- 实时爬虫状态更新
- 系统监控数据推送
- 实时日志流
- 双向通信支持

## 🔧 后端配置

### 1. 安装依赖

```bash
# 安装WebSocket相关依赖
pip install Flask-SocketIO>=5.3.0
pip install python-socketio>=5.8.0
pip install python-engineio>=4.7.0
pip install eventlet>=0.33.0
```

### 2. 启动WebSocket服务器

```bash
# 使用新的WebSocket服务器启动脚本
python backend/newslook/web/socketio_server.py
```

或者使用传统方式：

```bash
# 传统Flask应用启动（WebSocket功能可能受限）
python backend/main.py --web
```

### 3. 验证功能

```bash
# 运行后端功能测试
python test_websocket_backend.py
```

## 🌐 前端集成

### 1. WebSocket连接

前端已集成WebSocket管理器，自动处理：
- 连接建立和重连
- 心跳检测
- 消息队列管理
- 事件监听

### 2. 实时功能

**爬虫状态监控：**
- 实时显示爬虫启动/停止状态
- 自动更新进度条和状态图标
- 错误信息即时推送

**系统监控：**
- CPU、内存使用率实时更新
- 磁盘空间监控
- 网络连接状态显示

**日志流：**
- 实时日志显示
- 按级别过滤（INFO、WARNING、ERROR）
- 关键词搜索和高亮

## 📡 API 接口

### 健康检查
```
GET /api/v2/health
```

### 系统状态
```
GET /api/v2/status/system
```

### 爬虫状态
```
GET /api/v2/status/crawler
```

### WebSocket统计
```
GET /api/v2/websocket/stats
```

### 爬虫控制
```
POST /api/v2/crawler/{name}/start
POST /api/v2/crawler/{name}/stop
POST /api/v2/crawler/batch/start
POST /api/v2/crawler/batch/stop
```

## 🔌 WebSocket 事件

### 客户端 → 服务器

- `connect` - 建立连接
- `disconnect` - 断开连接
- `join_room` - 加入房间
- `leave_room` - 离开房间
- `ping` - 心跳检测
- `get_crawler_status` - 获取爬虫状态
- `get_system_status` - 获取系统状态

### 服务器 → 客户端

- `connected` - 连接确认
- `heartbeat` - 心跳响应
- `crawler_status_changed` - 爬虫状态变化
- `system_status` - 系统状态更新
- `log_message` - 日志消息
- `system_alert` - 系统告警

## 💻 使用示例

### 启动完整系统

```bash
# 1. 启动后端WebSocket服务器
python backend/newslook/web/socketio_server.py

# 2. 启动前端开发服务器
cd frontend
npm run dev

# 3. 访问 http://localhost:3000
```

### 测试WebSocket功能

```bash
# 测试后端API
python test_websocket_backend.py

# 检查前端WebSocket连接
# 在浏览器开发者工具中查看Network > WS标签
```

## 🐛 故障排除

### 常见问题

**1. WebSocket连接失败**
- 检查Flask-SocketIO是否正确安装
- 确认服务器启动使用了socketio_server.py
- 检查防火墙设置

**2. 实时更新不工作**
- 确认WebSocket连接状态
- 检查浏览器控制台错误信息
- 验证事件监听器是否正确注册

**3. 性能问题**
- 调整心跳间隔设置
- 限制日志流数据量
- 优化WebSocket房间管理

### 调试方法

```bash
# 启用详细日志
export FLASK_DEBUG=1
python backend/newslook/web/socketio_server.py

# 检查WebSocket连接
curl -I http://localhost:5000/api/v2/health
```

## 🔧 配置选项

### 后端配置 (configs/app.yaml)

```yaml
web:
  host: "127.0.0.1"
  port: 5000
  debug: true
  
websocket:
  ping_timeout: 60
  ping_interval: 25
  heartbeat_interval: 30
  max_connections: 100
```

### 前端配置

```javascript
// frontend/src/utils/websocket.js
const wsManager = new WebSocketManager()
wsManager.connect('ws://localhost:5000/socket.io/')
```

## 🎯 最佳实践

1. **连接管理**
   - 实现自动重连机制
   - 处理网络中断情况
   - 维护消息队列

2. **性能优化**
   - 合理设置心跳间隔
   - 限制广播频率
   - 使用房间机制减少不必要的消息

3. **错误处理**
   - 优雅处理连接失败
   - 提供fallback机制
   - 记录详细错误信息

4. **安全考虑**
   - 验证WebSocket连接
   - 限制连接数量
   - 过滤敏感信息

## 📚 更多资源

- [Flask-SocketIO 官方文档](https://flask-socketio.readthedocs.io/)
- [Socket.IO 客户端文档](https://socket.io/docs/v4/client-api/)
- [WebSocket 协议规范](https://tools.ietf.org/html/rfc6455)

---

*本文档是NewsLook Web界面优化的一部分，提供完整的WebSocket实时通信解决方案。* 