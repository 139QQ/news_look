#!/bin/bash

echo "========================================"
echo "   NewsLook 财经新闻爬虫系统启动器"
echo "========================================"
echo

cd "$(dirname "$0")"

echo "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    echo "请安装Python 3.9+"
    exit 1
fi

echo "检查依赖..."
if [ ! -f requirements.txt ]; then
    echo "❌ requirements.txt文件不存在"
    exit 1
fi

echo "安装/更新依赖..."
pip3 install -r requirements.txt

echo
echo "启动后端服务..."
echo "后端地址: http://localhost:5000"
echo

python3 main.py &
BACKEND_PID=$!

echo
echo "检查前端环境..."
cd frontend

if [ ! -d node_modules ]; then
    echo "安装前端依赖..."
    npm install
fi

echo "启动前端开发服务器..."
echo "前端地址: http://localhost:3000"
echo

npm run dev &
FRONTEND_PID=$!

cd ..

echo
echo "✅ NewsLook 启动完成!"
echo "请在浏览器中访问: http://localhost:3000"
echo
echo "按Ctrl+C停止服务"

# 捕获Ctrl+C信号并停止服务
trap "echo; echo '停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

wait
