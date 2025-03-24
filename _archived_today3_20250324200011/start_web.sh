#!/bin/bash
# 财经新闻爬虫系统 - Web启动脚本
echo "正在启动财经新闻爬虫系统Web应用..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python环境，请确保已安装Python 3"
    exit 1
fi

# 检查必要的目录
mkdir -p logs
mkdir -p data/db

# 设置虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo "使用虚拟环境..."
    source venv/bin/activate
fi

# 启动Web应用
python3 start_web.py --debug --with-crawler

# 检查启动结果
if [ $? -ne 0 ]; then
    echo "启动失败，请检查日志文件了解详情"
    read -p "按Enter键继续..."
else
    echo "Web应用已启动，按Ctrl+C终止程序..."
    # 保持脚本运行，直到用户中断
    tail -f logs/web_app.log 2>/dev/null || sleep infinity
fi 