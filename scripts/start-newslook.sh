#!/bin/bash

# 设置脚本编码
export LANG=zh_CN.UTF-8

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印标题
echo -e "${CYAN}========================================"
echo -e "   NewsLook 财经新闻爬虫系统启动器"
echo -e "========================================${NC}"
echo

# 检查Python环境
echo -e "${BLUE}🔍 检查Python环境...${NC}"
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo -e "${RED}❌ 错误: 未检测到Python，请先安装Python 3.9+${NC}"
        echo -e "${YELLOW}📥 安装指南: https://www.python.org/downloads/${NC}"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo -e "${GREEN}✅ Python环境检查通过${NC}"
$PYTHON_CMD --version
echo

# 检查Node.js环境
echo -e "${BLUE}🔍 检查Node.js环境...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  警告: 未检测到Node.js，前端功能将不可用${NC}"
    echo -e "${YELLOW}📥 安装指南: https://nodejs.org/${NC}"
    NODE_AVAILABLE=false
else
    echo -e "${GREEN}✅ Node.js环境检查通过${NC}"
    node --version
    NODE_AVAILABLE=true
fi
echo

# 检查依赖文件
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ 错误: 未找到requirements.txt文件${NC}"
    exit 1
fi

# 安装Python依赖
echo -e "${BLUE}📦 检查Python依赖...${NC}"
pip3 install -r requirements.txt > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python依赖检查完成${NC}"
else
    echo -e "${YELLOW}⚠️  警告: Python依赖安装可能有问题，但继续启动${NC}"
fi
echo

# 检查前端文件
if [ -f "package.json" ] && [ "$NODE_AVAILABLE" = true ]; then
    echo -e "${BLUE}📦 检查前端依赖...${NC}"
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}正在安装前端依赖...${NC}"
        npm install
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ 错误: 前端依赖安装失败${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}✅ 前端依赖检查完成${NC}"
    echo
fi

# 创建数据目录
if [ ! -d "data/db" ]; then
    echo -e "${BLUE}📁 创建数据库目录...${NC}"
    mkdir -p data/db
    echo -e "${GREEN}✅ 数据库目录创建完成${NC}"
    echo
fi

# 主菜单函数
show_menu() {
    echo -e "${CYAN}🚀 请选择启动模式:${NC}"
    echo
    echo -e "${GREEN}[1]${NC} 完整模式 - 启动后端API + 前端界面"
    echo -e "${GREEN}[2]${NC} 仅后端API (Flask服务器)"
    if [ "$NODE_AVAILABLE" = true ]; then
        echo -e "${GREEN}[3]${NC} 仅前端界面 (Vue开发服务器)"
    else
        echo -e "${YELLOW}[3]${NC} 仅前端界面 (不可用 - 需要Node.js)"
    fi
    echo -e "${GREEN}[4]${NC} 爬虫模式 - 运行新闻爬虫"
    echo -e "${GREEN}[5]${NC} 查看系统状态"
    echo -e "${RED}[0]${NC} 退出"
    echo
    read -p "请输入选择 (0-5): " choice
}

# 爬虫模式菜单
crawler_menu() {
    echo -e "${CYAN}🕷️ 爬虫模式选项:${NC}"
    echo
    echo -e "${GREEN}[1]${NC} 爬取所有来源"
    echo -e "${GREEN}[2]${NC} 爬取新浪财经"
    echo -e "${GREEN}[3]${NC} 爬取东方财富"
    echo -e "${GREEN}[4]${NC} 爬取腾讯财经"
    echo -e "${GREEN}[5]${NC} 爬取网易财经"
    echo -e "${GREEN}[6]${NC} 爬取凤凰财经"
    echo -e "${RED}[0]${NC} 返回主菜单"
    echo
    read -p "请选择爬虫来源: " crawler_choice
}

# 完整模式启动
start_full_mode() {
    echo
    echo -e "${PURPLE}🌟 启动完整模式...${NC}"
    echo -e "${BLUE}⚡ 正在启动后端API服务器...${NC}"
    
    # 启动后端服务器（后台运行）
    nohup $PYTHON_CMD run.py web --host 0.0.0.0 --port 5000 > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    sleep 3
    
    if [ -f "package.json" ] && [ "$NODE_AVAILABLE" = true ]; then
        echo -e "${BLUE}⚡ 正在启动前端开发服务器...${NC}"
        
        # 启动前端服务器（后台运行）
        nohup npm run dev > logs/frontend.log 2>&1 &
        FRONTEND_PID=$!
        sleep 2
        
        echo
        echo -e "${GREEN}✅ 系统启动完成！${NC}"
        echo -e "${CYAN}🌐 后端API: http://localhost:5000${NC}"
        echo -e "${CYAN}🎨 前端界面: http://localhost:3000${NC}"
        echo
        echo -e "${YELLOW}📝 注意: 请等待几秒钟让服务完全启动${NC}"
        echo -e "${YELLOW}📋 后端PID: $BACKEND_PID${NC}"
        echo -e "${YELLOW}📋 前端PID: $FRONTEND_PID${NC}"
        
        # 等待用户输入停止服务
        echo
        read -p "按 Enter 键停止所有服务..."
        kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}✅ 服务已停止${NC}"
    else
        echo -e "${CYAN}🌐 后端API启动完成: http://localhost:5000${NC}"
        echo -e "${YELLOW}⚠️  前端文件不存在或Node.js不可用，仅启动后端API${NC}"
        echo -e "${YELLOW}📋 后端PID: $BACKEND_PID${NC}"
        
        echo
        read -p "按 Enter 键停止后端服务..."
        kill $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}✅ 后端服务已停止${NC}"
    fi
}

# 仅后端模式
start_backend_only() {
    echo
    echo -e "${BLUE}🔧 启动后端API服务器...${NC}"
    echo -e "${CYAN}🌐 服务器地址: http://localhost:5000${NC}"
    echo
    $PYTHON_CMD run.py web --host 0.0.0.0 --port 5000
}

# 仅前端模式
start_frontend_only() {
    if [ ! -f "package.json" ]; then
        echo -e "${RED}❌ 错误: 未找到前端配置文件${NC}"
        return 1
    fi
    
    if [ "$NODE_AVAILABLE" != true ]; then
        echo -e "${RED}❌ 错误: Node.js不可用${NC}"
        return 1
    fi
    
    echo
    echo -e "${BLUE}🎨 启动前端开发服务器...${NC}"
    echo -e "${CYAN}🌐 开发服务器: http://localhost:3000${NC}"
    echo
    npm run dev
}

# 爬虫模式
start_crawler_mode() {
    while true; do
        crawler_menu
        
        case $crawler_choice in
            1)
                echo -e "${BLUE}🕷️ 启动所有爬虫...${NC}"
                $PYTHON_CMD run.py crawler --all --max 50
                ;;
            2)
                echo -e "${BLUE}🕷️ 启动新浪财经爬虫...${NC}"
                $PYTHON_CMD run.py crawler --source sina --max 50
                ;;
            3)
                echo -e "${BLUE}🕷️ 启动东方财富爬虫...${NC}"
                $PYTHON_CMD run.py crawler --source eastmoney --max 50
                ;;
            4)
                echo -e "${BLUE}🕷️ 启动腾讯财经爬虫...${NC}"
                $PYTHON_CMD run.py crawler --source tencent --max 50
                ;;
            5)
                echo -e "${BLUE}🕷️ 启动网易财经爬虫...${NC}"
                $PYTHON_CMD run.py crawler --source netease --max 50
                ;;
            6)
                echo -e "${BLUE}🕷️ 启动凤凰财经爬虫...${NC}"
                $PYTHON_CMD run.py crawler --source ifeng --max 50
                ;;
            0)
                return
                ;;
            *)
                echo -e "${RED}❌ 无效选择${NC}"
                ;;
        esac
        
        echo
        read -p "按 Enter 键继续..."
        echo
    done
}

# 状态检查
check_status() {
    echo
    echo -e "${BLUE}📊 系统状态检查...${NC}"
    echo
    echo -e "${CYAN}📁 数据库统计:${NC}"
    $PYTHON_CMD run.py db stats --format table
    echo
    echo -e "${YELLOW}📈 如需查看详细信息，请访问Web界面${NC}"
    echo
    read -p "按 Enter 键继续..."
}

# 创建日志目录
mkdir -p logs

# 主循环
while true; do
    show_menu
    
    case $choice in
        1)
            start_full_mode
            ;;
        2)
            start_backend_only
            ;;
        3)
            start_frontend_only
            ;;
        4)
            start_crawler_mode
            ;;
        5)
            check_status
            ;;
        0)
            echo -e "${GREEN}👋 感谢使用NewsLook财经新闻爬虫系统！${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ 无效选择，请重新输入${NC}"
            echo
            read -p "按 Enter 键继续..."
            ;;
    esac
    
    echo
done 