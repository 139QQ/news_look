# CORS跨域问题故障排除指南

## 问题概述

CORS（Cross-Origin Resource Sharing）跨域资源共享是Web安全的重要机制。NewsLook项目采用前后端分离架构，前端运行在端口3000/3001，后端运行在端口5000，因此需要正确配置CORS以避免跨域访问问题。

## 常见CORS错误

### 1. 典型错误信息

```
Access to XMLHttpRequest at 'http://localhost:5000/api/...' from origin 'http://localhost:3000' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

```
Access to XMLHttpRequest at 'http://localhost:5000/api/...' from origin 'http://localhost:3000' has been blocked by CORS policy: Response to preflight request doesn't pass access control check.
```

### 2. 错误分类

- **配置缺失**: 后端未启用CORS
- **源地址不匹配**: 前端地址未包含在允许列表中
- **方法限制**: HTTP方法不被允许
- **头部限制**: 请求头不被允许
- **预检失败**: OPTIONS请求失败

## 当前配置检查

### 前端配置 (vite.config.js)

```javascript
server: {
  host: '0.0.0.0',
  port: 3000,
  cors: true,  // ✅ 启用CORS
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true  // ✅ 重要配置
    }
  }
}
```

### 后端配置 (configs/app.yaml)

```yaml
web:
  cors:
    enabled: true  # ✅ 启用CORS
    origins: 
      - "http://localhost:3000"
      - "http://127.0.0.1:3000"
```

### 后端代码 (app.py)

```python
CORS(app, 
     supports_credentials=True, 
     origins=["http://localhost:3000", "http://127.0.0.1:3000"],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'])
```

## 诊断步骤

### 1. 快速诊断

运行自动诊断脚本：

```bash
cd frontend
node scripts/cors-diagnostic.js
```

### 2. 手动检查

#### 检查后端服务状态

```bash
curl -i http://localhost:5000/api/health
```

预期响应应包含CORS头：
```
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With
```

#### 检查预检请求

```bash
curl -X OPTIONS -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: content-type" \
     -i http://localhost:5000/api/health
```

#### 检查实际请求

```bash
curl -H "Origin: http://localhost:3000" \
     -i http://localhost:5000/api/health
```

## 修复方案

### 方案1: 更新CORS配置

如果配置不完整，更新`configs/app.yaml`：

```yaml
web:
  cors:
    enabled: true
    origins: 
      - "http://localhost:3000"
      - "http://127.0.0.1:3000"
      - "http://localhost:3001"  # 添加preview端口
      - "http://127.0.0.1:3001"
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers: ["Content-Type", "Authorization", "X-Requested-With"]
    supports_credentials: true
```

### 方案2: 增强前端代理配置

更新`frontend/vite.config.js`：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true,
      secure: false,
      configure: (proxy, _options) => {
        proxy.on('error', (err, _req, _res) => {
          console.log('代理错误', err);
        });
        proxy.on('proxyReq', (proxyReq, req, _res) => {
          console.log('发送请求到目标', req.method, req.url);
        });
        proxy.on('proxyRes', (proxyRes, req, _res) => {
          console.log('从目标接收到响应', proxyRes.statusCode, req.url);
        });
      }
    }
  }
}
```

### 方案3: 处理开发环境特殊情况

对于localhost vs 127.0.0.1的问题，确保两者都被支持：

```javascript
// frontend/src/api/index.js
const getBaseURL = () => {
  // 开发环境使用代理
  if (import.meta.env.DEV) {
    return '/api'
  }
  
  // 生产环境或特殊情况
  const host = window.location.hostname
  const port = host === 'localhost' ? '5000' : '5000'
  return `http://${host}:${port}/api`
}

const api = axios.create({
  baseURL: getBaseURL(),
  // ...其他配置
})
```

## 生产环境配置

### 安全CORS配置

生产环境避免使用通配符：

```yaml
web:
  cors:
    enabled: true
    origins: 
      - "https://your-domain.com"
      - "https://www.your-domain.com"
    methods: ["GET", "POST"]  # 限制方法
    allow_headers: ["Content-Type", "Authorization"]
    supports_credentials: true
    max_age: 86400  # 预检缓存时间
```

### Nginx配置

如果使用Nginx代理：

```nginx
server {
    location /api/ {
        proxy_pass http://localhost:5000/;
        
        # CORS配置
        add_header Access-Control-Allow-Origin $http_origin;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With";
        add_header Access-Control-Allow-Credentials true;
        
        # 处理预检请求
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin $http_origin;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With";
            add_header Access-Control-Max-Age 86400;
            return 204;
        }
    }
}
```

## 常见问题解答

### Q: 为什么开发环境正常，生产环境报CORS错误？

A: 可能原因：
1. 生产环境域名未添加到CORS允许列表
2. 生产环境使用了HTTPS，需要对应配置
3. 代理配置在生产环境不生效

### Q: 为什么有时候能正常访问，有时候报CORS错误？

A: 可能原因：
1. 浏览器缓存了失败的预检请求
2. 服务重启导致配置变化
3. 网络环境变化（localhost vs 127.0.0.1）

解决方法：
```bash
# 清除浏览器缓存或使用无痕模式
# 重启服务
python app.py --port 5000
```

### Q: OPTIONS请求总是失败怎么办？

A: 检查后端是否正确处理OPTIONS请求：

```python
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response
```

## 监控和调试

### 浏览器开发者工具

1. 打开Network选项卡
2. 查看失败的请求
3. 检查Response Headers中的CORS头
4. 注意区分预检请求（OPTIONS）和实际请求

### 后端日志

启用详细的CORS日志：

```python
import logging
logging.getLogger('flask_cors').level = logging.DEBUG
```

### 测试脚本

创建简单的测试脚本：

```javascript
// test-cors.js
fetch('http://localhost:5000/api/health', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log('成功:', data))
.catch(error => console.error('CORS错误:', error));
```

## 最佳实践

1. **开发环境**：使用宽松的CORS配置便于调试
2. **生产环境**：严格限制允许的源、方法和头部
3. **监控**：记录CORS相关的错误和访问
4. **文档**：维护清晰的API文档和CORS策略
5. **测试**：定期测试跨域访问功能

## 相关资源

- [MDN CORS文档](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Flask-CORS文档](https://flask-cors.readthedocs.io/)
- [Vite代理配置](https://vitejs.dev/config/server-options.html#server-proxy)

## 快速修复脚本

运行以下命令快速修复常见CORS问题：

```bash
# 使用诊断脚本
cd frontend && node scripts/cors-diagnostic.js

# 使用修复脚本（如果生成）
chmod +x frontend/scripts/fix-cors.sh && ./frontend/scripts/fix-cors.sh
``` 