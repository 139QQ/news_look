#!/bin/bash
# 财经新闻爬虫系统 - 启动脚本
echo "启动财经新闻爬虫系统..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python 3。请安装Python 3。"
    exit 1
fi

# 创建必要的目录
mkdir -p logs data/db data/output

# 设置环境变量
export LOG_LEVEL="INFO"
export LOG_DIR="$(pwd)/logs"
export DB_DIR="$(pwd)/data/db"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate || source venv/Scripts/activate
fi

# 运行Web应用
echo "启动Web应用..."
python3 run.py web --debug --host=0.0.0.0 --port=5000 --with-crawler

if [ $? -ne 0 ]; then
    echo "启动失败，请检查logs目录下的日志文件。"
else
    echo "Web应用已启动，正在运行中..."
fi 