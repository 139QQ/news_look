# 安装指南

本文档提供了安装和配置金融新闻爬虫系统的详细说明。

## 1. 系统要求

### 1.1 软件要求

- Python 3.9 或更高版本
- pip (Python 包管理器)
- Git (可选，用于克隆代码库)

### 1.2 硬件推荐

- CPU: 2核或更多
- 内存: 至少4GB RAM
- 磁盘空间: 至少1GB可用空间

### 1.3 支持的操作系统

- Windows 10/11
- macOS 10.15+ (Catalina 或更高版本)
- 主流 Linux 发行版 (Ubuntu 20.04+, CentOS 8+, Debian 10+)

## 2. 基本安装

### 2.1 获取代码

有两种方式获取代码：

**方式1：使用Git克隆**

```bash
git clone https://github.com/username/finance_news_crawler.git
cd finance_news_crawler
```

**方式2：下载ZIP包**

1. 访问 https://github.com/username/finance_news_crawler
2. 点击 "Code" 按钮，然后点击 "Download ZIP"
3. 解压下载的ZIP文件
4. 使用命令行进入解压后的目录

### 2.2 创建虚拟环境

我们强烈建议使用虚拟环境来安装依赖，避免与系统其他Python项目产生冲突。

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2.3 安装依赖

**基本安装（仅爬虫功能）:**

```bash
pip install -r requirements/base.txt
```

**完整安装（包括Web界面和所有功能）:**

```bash
pip install -r requirements.txt
```

**开发环境（包括测试和开发工具）:**

```bash
pip install -r requirements/dev.txt
```

## 3. 配置

### 3.1 数据库配置

默认情况下，系统使用SQLite数据库，存储在`data/finance_news.db`。对于大多数用例，这已经足够，无需额外配置。

如果需要，你可以修改`app/config/default.py`中的数据库配置：

```python
# SQLite配置
DB_CONFIG = {
    'db_file': 'data/finance_news.db',
}
```

### 3.2 日志配置

日志文件默认存储在`logs/`目录下，按爬虫名称分类。你可以通过命令行参数`--log-dir`自定义日志存储位置：

```bash
python run_crawler.py --log-dir /path/to/logs
```

### 3.3 代理配置 (可选)

如果需要使用网络代理进行爬取，可以设置`--use-proxy`参数：

```bash
python run_crawler.py --use-proxy
```

默认代理配置在`app/config/default.py`中：

```python
PROXY_CONFIG = {
    'enabled': False,
    'proxy': {
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890'
    }
}
```

## 4. 验证安装

### 4.1 运行测试

运行以下命令来验证系统是否安装正确：

```bash
python run_crawler.py -s 东方财富 -d 1 --max-news 2
```

如果一切正常，你应该会看到爬虫成功爬取了东方财富网的新闻，并且日志会显示爬取的进度和结果。

### 4.2 启动Web界面

如果你安装了Web依赖，可以启动Web界面：

```bash
python run.py
```

打开浏览器，访问 http://localhost:5000 即可访问Web界面。

## 5. 常见问题

### 5.1 依赖安装失败

**问题**: 安装依赖时出现错误。

**解决方案**:
- 确保你的Python版本符合要求
- 尝试更新pip: `pip install --upgrade pip`
- 对于Windows用户，某些包可能需要安装Visual C++ Build Tools

### 5.2 爬虫运行失败

**问题**: 运行爬虫时出现连接错误或超时。

**解决方案**:
- 检查网络连接
- 尝试使用代理
- 调整超时参数: `python run_crawler.py --timeout 60`

### 5.3 数据库错误

**问题**: 遇到数据库相关的错误。

**解决方案**:
- 确保`data`目录存在且有写入权限
- 尝试删除数据库文件重新创建: `rm data/finance_news.db`

## 6. Docker安装 (可选)

如果你熟悉Docker，也可以使用Docker方式部署：

```bash
# 构建镜像
docker build -t finance-news-crawler .

# 运行容器
docker run -p 5000:5000 -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs finance-news-crawler
```

## 7. 升级指南

当有新版本发布时，按照以下步骤升级：

```bash
# 拉取最新代码
git pull

# 更新依赖
pip install -r requirements.txt

# 运行数据库迁移(如果有)
python -m app.db.migrations
```

## 8. 卸载

如果需要卸载，只需删除项目目录和虚拟环境即可。

```bash
# 停用虚拟环境
deactivate

# 删除项目目录
cd ..
rm -rf finance_news_crawler
```

## 9. 支持与帮助

如果在安装过程中遇到任何问题，请：

1. 查看项目的[FAQ](../faq.md)文档
2. 在GitHub上提交Issue
3. 联系项目维护者 