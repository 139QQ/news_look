# 财经新闻爬虫系统统一入口使用指南

本文档介绍如何使用系统的统一入口 `run.py` 来运行不同模式的应用，包括爬虫模式、调度模式和Web应用模式。

## 基本用法

统一入口支持三种运行模式：

```bash
# 爬虫模式
python run.py crawler [参数]

# 调度模式
python run.py scheduler [参数]

# Web应用模式
python run.py web [参数]
```

如果不指定运行模式，默认使用Web应用模式。

## 爬虫模式

爬虫模式用于运行爬虫任务，支持多种爬虫类型。

### 基本参数

```bash
python run.py crawler -s eastmoney -d 3
```

主要参数说明：
- `-s, --source`：爬虫来源，支持eastmoney, eastmoney_simple, sina, tencent等
- `-d, --days`：爬取最近几天的新闻，默认为1天
- `-p, --use-proxy`：是否使用代理
- `--db-path`：数据库路径，如不指定则使用默认路径
- `--source-db`：是否使用来源专用数据库
- `--log-level`：日志级别，可选值：DEBUG, INFO, WARNING, ERROR，默认为INFO
- `--log-dir`：日志存储目录，默认为./logs
- `--output-dir`：输出文件目录，默认为./data/output
- `--debug`：是否开启调试模式

### 东方财富网爬虫特有参数

```bash
python run.py crawler -s eastmoney --max-news 20 --categories 财经 股票 期货
```

特有参数说明：
- `--max-news`：每个分类最多爬取多少条新闻，默认10条
- `--categories`：要爬取的新闻分类，默认为财经和股票
- `--delay`：请求间隔时间(秒)，默认5秒
- `--max-retries`：最大重试次数，默认3次
- `--timeout`：请求超时时间(秒)，默认30秒
- `--use-selenium`：是否使用Selenium（仅适用于东方财富网爬虫）

### 运行所有爬虫

如果不指定爬虫来源，则运行所有可用的爬虫：

```bash
python run.py crawler -d 2
```

## 调度模式

调度模式用于定时运行爬虫任务。

### 基本参数

```bash
python run.py scheduler --daemon
```

主要参数说明：
- `--daemon`：以守护进程方式运行
- `--config`：指定配置文件路径
- `--log-level`：日志级别，可选值：DEBUG, INFO, WARNING, ERROR，默认为INFO
- `--log-dir`：日志存储目录，默认为./logs
- `--task`：指定要执行的任务名称，如不指定则执行配置文件中的所有任务
- `--list-tasks`：列出所有可用的调度任务

### 查看可用任务

```bash
python run.py scheduler --list-tasks
```

### 运行特定任务

```bash
python run.py scheduler --task eastmoney_daily
```

## Web应用模式

Web应用模式用于启动Web界面，查看和管理爬虫数据。

### 基本参数

```bash
python run.py web --host 127.0.0.1 --port 8080
```

主要参数说明：
- `--host`：监听主机，默认为0.0.0.0
- `--port`：监听端口，默认为5000
- `--debug`：是否开启调试模式

## 示例

### 爬取东方财富网最近3天的财经和股票新闻

```bash
python run.py crawler -s eastmoney -d 3 --categories 财经 股票 --max-news 20
```

### 以守护进程方式运行调度器

```bash
python run.py scheduler --daemon --log-level DEBUG
```

### 在开发模式下启动Web应用

```bash
python run.py web --debug --port 8080
```

## 注意事项

1. 所有日志文件都保存在 `logs` 目录下相应的子目录中
2. 数据库文件默认保存在 `data` 目录下
3. 输出文件默认保存在 `data/output` 目录下
4. 如果使用调度模式，请确保已正确配置调度任务 