#!/bin/bash

# CORS问题修复脚本
echo "🔧 开始修复CORS问题..."

# 1. 检查后端依赖
echo "📦 检查后端依赖..."
pip install flask-cors

# 2. 重启后端服务
echo "🔄 重启后端服务..."
cd "$(dirname "$0")/../.."
python app.py --port 5000 &
BACKEND_PID=$!
echo "后端PID: $BACKEND_PID"

# 3. 重启前端服务
echo "🔄 重启前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "前端PID: $FRONTEND_PID"

echo "✅ 服务重启完成"
echo "🌐 前端地址: http://localhost:3000"
echo "🔗 后端地址: http://localhost:5000"
echo "❌ 停止服务: kill $BACKEND_PID $FRONTEND_PID"
