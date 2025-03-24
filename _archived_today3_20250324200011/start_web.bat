@echo off
REM 财经新闻爬虫系统 - Web启动脚本
echo 正在启动财经新闻爬虫系统Web应用...

REM 检查Python环境
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到Python环境，请确保已安装Python并添加到PATH环境变量中
    pause
    exit /b 1
)

REM 检查必要的目录
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "data\db" mkdir data\db

REM 启动Web应用
python start_web.py --debug --with-crawler

REM 如果出错，显示错误信息并暂停
if %ERRORLEVEL% NEQ 0 (
    echo 启动失败，请检查日志文件了解详情
    pause
) else (
    echo Web应用已启动，按任意键关闭此窗口...
    pause >nul
) 