#!/bin/bash

# NewsLook 开发环境启动脚本
# 支持 Linux/macOS/WSL

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 输出带颜色的文本
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${CYAN}     NewsLook 财经新闻爬虫系统${NC}"
    echo -e "${CYAN}        开发环境一键启动${NC}"  
    echo -e "${BLUE}========================================${NC}"
    echo
}

print_step() {
    echo -e "${YELLOW}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${PURPLE}💡 $1${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未找到，请先安装 $2"
        exit 1
    fi
}

# 检查端口是否占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口 $1 已被占用${NC}"
        return 1
    fi
    return 0
}

# 主函数
main() {
    print_header
    
    print_step "[1/4] 检查环境..."
    
    # 检查Python
    check_command "python3" "Python 3.9+"
    python3 --version
    print_success "Python 环境检查通过"
    
    # 检查Node.js
    check_command "node" "Node.js 16+"
    node --version
    print_success "Node.js 环境检查通过"
    
    # 检查npm
    check_command "npm" "npm 8+"
    npm --version
    print_success "npm 环境检查通过"
    
    echo
    print_step "[2/4] 检查端口..."
    
    # 检查后端端口
    if ! check_port 5000; then
        print_info "如需停止占用端口的进程: lsof -ti:5000 | xargs kill -9"
    fi
    
    # 检查前端端口
    if ! check_port 3000; then
        print_info "如需停止占用端口的进程: lsof -ti:3000 | xargs kill -9"
    fi
    
    echo
    print_step "[3/4] 启动后端服务器 (端口 5000)..."
    
    # 启动后端
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'\" && python3 app.py --port 5000"'
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal --title="NewsLook 后端" -- bash -c "python3 app.py --port 5000; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -title "NewsLook 后端" -hold -e "python3 app.py --port 5000" &
        else
            python3 app.py --port 5000 &
            echo "后端在后台启动，PID: $!"
        fi
    else
        # WSL 或其他
        python3 app.py --port 5000 &
        echo "后端在后台启动，PID: $!"
    fi
    
    print_success "后端启动命令已执行"
    
    # 等待后端启动
    echo "等待后端启动..."
    sleep 3
    
    echo
    print_step "[4/4] 启动前端服务器 (端口 3000)..."
    
    # 检查前端依赖
    if [ ! -d "frontend/node_modules" ]; then
        print_step "安装前端依赖..."
        cd frontend && npm install && cd ..
    fi
    
    # 启动前端
    cd frontend
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'\" && npm run dev"'
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal --title="NewsLook 前端" -- bash -c "npm run dev; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -title "NewsLook 前端" -hold -e "npm run dev" &
        else
            npm run dev &
            echo "前端在后台启动，PID: $!"
        fi
    else
        # WSL 或其他
        npm run dev &
        echo "前端在后台启动，PID: $!"
    fi
    cd ..
    
    print_success "前端启动命令已执行"
    
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}🚀 NewsLook 开发环境启动完成!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
    echo -e "${CYAN}📱 前端界面:${NC} http://localhost:3000"
    echo -e "${CYAN}🔗 后端API:${NC}  http://localhost:5000"
    echo -e "${CYAN}📊 健康检查:${NC} http://localhost:5000/api/health"
    echo
    print_info "提示:"
    echo "  - 前端支持热重载，修改代码会自动刷新"
    echo "  - 后端修改需要手动重启"
    echo "  - 使用 Ctrl+C 停止当前进程"
    echo
    
    # 等待用户输入
    read -p "按回车键退出..."
}

# 运行主函数
main 