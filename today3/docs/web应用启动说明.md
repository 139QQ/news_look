# 财经新闻爬虫系统 - Web应用启动说明

本文档介绍如何使用统一入口启动Web应用，以及如何解决常见问题。

## 统一入口说明

我们已经优化了项目结构，将所有功能整合到了统一的入口文件 `run.py` 中。这个文件支持三种运行模式：
- 爬虫模式 (crawler)
- 调度模式 (scheduler)
- Web应用模式 (web)

## 启动Web应用

### 方法一：使用启动脚本（推荐）

#### Windows 环境：

双击运行 `start.bat` 文件，它会自动：
1. 检查Python环境
2. 创建必要的目录（logs、data/db、data/output）
3. 以调试模式启动Web应用
4. 初始化爬虫管理器

```batch
start.bat
```

#### Linux/Mac 环境：

```bash
chmod +x start.sh
./start.sh
```

### 方法二：直接使用 run.py

如果你需要更精细的控制，可以直接使用 `run.py` 启动Web应用：

```bash
# 基本启动（默认为Web模式）
python run.py

# 指定Web模式，使用调试模式
python run.py web --debug

# 指定主机和端口
python run.py web --host 127.0.0.1 --port 8080

# 生产环境模式
python run.py web --prod

# 带爬虫管理器启动
python run.py web --with-crawler
```

## 参数说明

Web模式支持以下参数：

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--host` | 监听主机 | 0.0.0.0 |
| `--port` | 监听端口 | 5000 |
| `--debug` | 启用调试模式 | 否 |
| `--prod` | 启用生产模式（禁用调试） | 否 |
| `--log-level` | 日志级别（DEBUG/INFO/WARNING/ERROR） | INFO |
| `--log-dir` | 日志存储目录 | ./logs |
| `--with-crawler` | 启动时初始化爬虫管理器 | 否 |

## 环境变量

系统使用以下环境变量来配置各个组件：

| 环境变量 | 说明 | 默认值 |
| --- | --- | --- |
| `LOG_LEVEL` | 日志级别 | INFO |
| `LOG_DIR` | 日志目录 | ./logs |
| `DB_DIR` | 数据库目录 | ./data/db |

这些环境变量会在程序启动时自动设置，也可以通过操作系统的方式提前设置。

## 目录结构

应用需要以下目录结构才能正常运行：

```
project_root/
├── run.py               # 统一入口
├── start.bat            # Windows启动脚本
├── start.sh             # Linux/Mac启动脚本
├── logs/                # 日志目录
├── data/                # 数据目录
│   ├── db/              # 数据库目录
│   └── output/          # 输出目录
└── app/                 # 应用代码
```

## 常见问题

### 1. 无法启动Web应用

如果无法启动Web应用，请检查：
- Python是否已安装并添加到PATH
- 项目依赖是否已安装：`pip install -r requirements.txt`
- 端口是否被占用，可尝试更换端口：`python run.py web --port 8080`

### 2. 爬虫管理器初始化失败

如果爬虫管理器初始化失败，可能是因为：
- 数据库连接问题
- 爬虫模块导入错误

解决方法：
- 检查 `logs` 目录下的日志文件，查看详细错误信息
- 确认 `data/db` 目录存在且有写入权限
- 尝试不启用爬虫管理器启动：`python run.py web`

### 3. 数据库相关错误

如果遇到数据库相关错误，可能需要：
- 确保数据库目录存在：`mkdir -p data/db`
- 重置数据库（谨慎操作）：删除 `data/db` 目录下的数据库文件，系统会自动重新创建

### 4. KeyError: 'DB_DIR' 错误

如果遇到 `KeyError: 'DB_DIR'` 错误，可能是因为：
- 没有正确设置 `DB_DIR` 环境变量
- 配置加载有问题

解决方法：
- 手动创建数据库目录：`mkdir -p data/db`
- 手动设置环境变量：
  - Windows: `set DB_DIR=./data/db`
  - Linux/Mac: `export DB_DIR=./data/db`
- 使用最新版本的启动脚本，它会自动处理这些设置

## 项目结构优化

我们已经进行了以下优化：

1. 统一了入口文件：
   - 使用 `run.py` 作为主入口
   - 删除了重复的入口文件（`web_server.py`、`web_viewer.py`、`start_web.py`）
   - 整合了Web启动功能到 `run.py` 中

2. 优化了启动脚本：
   - 创建了新的 `start.bat` 用于Windows环境
   - 创建了新的 `start.sh` 用于Linux/Mac环境
   - 添加了环境检查和目录创建功能
   - 添加了错误处理和日志查看功能

3. 移除了不必要的参数：
   - 删除了爬虫初始化中不必要的数据库参数
   - 简化了爬虫实例的创建过程

4. 改进了环境变量处理：
   - 增加了 DB_DIR 环境变量的默认设置
   - 确保在所有运行模式下正确创建必要的目录 