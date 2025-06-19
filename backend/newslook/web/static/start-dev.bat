@echo off
echo ========================================
echo NewsLook 前端开发环境启动脚本
echo ========================================
echo.

:: 检查Node.js是否安装
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到Node.js，请先安装Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo 检测到Node.js版本:
node --version
echo.

:: 检查npm是否可用
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: npm不可用
    pause
    exit /b 1
)

echo 检测到npm版本:
npm --version
echo.

:: 检查package.json是否存在
if not exist package.json (
    echo 错误: 未找到package.json文件
    echo 请确保在正确的目录下运行此脚本
    pause
    exit /b 1
)

:: 检查node_modules是否存在
if not exist node_modules (
    echo 正在安装依赖包...
    npm install
    if %errorlevel% neq 0 (
        echo 错误: 依赖包安装失败
        pause
        exit /b 1
    )
    echo 依赖包安装完成!
    echo.
) else (
    echo 依赖包已存在，跳过安装
    echo.
)

echo 启动开发服务器...
echo 服务器地址: http://localhost:5173
echo 按 Ctrl+C 停止服务器
echo.

npm run dev

pause 