# 财经新闻爬虫系统 - 优化项目结构

## 当前问题

1. 文件组织混乱，存在重复功能的文件（如web_viewer.py和web_server.py）
2. 目录结构不清晰，web相关文件分散在多个目录（web/、templates/、static/）
3. 爬虫模块存在冗余（如sina_crawler.py和sina_finance_crawler.py）
4. 工具类过多且分散，功能重叠
5. 入口点不明确（存在多个启动脚本）

## 优化方案

### 1. 目录结构优化

```
finance_news_crawler/
├── app/                      # 应用核心目录
│   ├── __init__.py           # 应用初始化
│   ├── config.py             # 配置文件
│   ├── models/               # 数据模型
│   │   ├── __init__.py
│   │   └── news.py           # 新闻数据模型
│   ├── crawlers/             # 爬虫模块
│   │   ├── __init__.py
│   │   ├── base.py           # 爬虫基类
│   │   ├── eastmoney.py      # 东方财富爬虫
│   │   ├── sina.py           # 新浪财经爬虫
│   │   ├── tencent.py        # 腾讯财经爬虫
│   │   └── netease.py        # 网易财经爬虫
│   ├── utils/                # 工具模块
│   │   ├── __init__.py
│   │   ├── database.py       # 数据库操作
│   │   ├── db_manager.py     # 数据库管理
│   │   ├── text_cleaner.py   # 文本清洗
│   │   ├── sentiment.py      # 情感分析
│   │   └── logger.py         # 日志工具
│   ├── web/                  # Web应用
│   │   ├── __init__.py
│   │   ├── routes.py         # 路由定义
│   │   ├── forms.py          # 表单定义
│   │   ├── static/           # 静态资源
│   │   │   ├── css/
│   │   │   ├── js/
│   │   │   └── img/
│   │   └── templates/        # 模板文件
│   └── tasks/                # 任务模块
│       ├── __init__.py
│       └── scheduler.py      # 任务调度器
├── db/                       # 数据库文件目录
├── logs/                     # 日志文件目录
├── data/                     # 数据文件目录
├── backup/                   # 备份文件目录
├── tests/                    # 测试目录
│   ├── __init__.py
│   ├── test_crawlers.py
│   ├── test_database.py
│   └── test_utils.py
├── run.py                    # 主入口点
├── run_crawler.py            # 爬虫运行脚本
├── run_scheduler.py          # 调度器运行脚本
├── requirements.txt          # 依赖列表
├── README.md                 # 项目说明
└── docs/                     # 文档目录
    └── 项目文档.md
```

### 2. 功能整合

1. **统一入口点**：
   - `run.py` - Web应用入口
   - `run_crawler.py` - 爬虫运行入口
   - `run_scheduler.py` - 调度器运行入口

2. **爬虫模块整合**：
   - 将重复的爬虫合并（如sina_crawler.py和sina_finance_crawler.py）
   - 统一爬虫接口和命名规范

3. **工具模块整合**：
   - 将功能相似的工具类合并
   - 明确各工具类的职责

4. **Web应用整合**：
   - 将所有Web相关文件统一到app/web目录下
   - 统一静态资源和模板管理

### 3. 代码优化

1. **统一编码风格**：
   - 添加.editorconfig文件规范编码风格
   - 统一注释和文档风格

2. **优化导入方式**：
   - 使用相对导入或绝对导入，避免导入混乱
   - 规范导入顺序

3. **增强错误处理**：
   - 统一异常处理机制
   - 完善日志记录

4. **提高代码复用**：
   - 抽取公共功能到基类或工具函数
   - 减少代码重复

### 4. 文档完善

1. **更新README**：
   - 完善安装和使用说明
   - 添加项目结构说明

2. **添加开发文档**：
   - 添加开发指南
   - 添加API文档

3. **添加注释**：
   - 为关键函数和类添加详细注释
   - 使用docstring规范化注释

## 实施步骤

1. 创建新的目录结构
2. 迁移和重构现有代码
3. 更新导入路径
4. 测试功能完整性
5. 更新文档 