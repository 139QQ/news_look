# 财经新闻爬虫系统 (NewsLook)

一个用于爬取各大财经网站新闻的系统，主要目标包括东方财富、新浪财经、网易财经和凤凰财经等。

## 主要功能

- **多网站支持**: 可配置爬取多个主流财经新闻网站。
- **统一接口**: 提供统一的爬虫调用接口和标准化数据输出格式。
- **健壮性**: 包含完善的错误处理、重试机制和日志记录。
- **灵活性**: 支持通过命令行参数进行灵活配置，如爬取时间范围、新闻来源、代理使用等。
- **数据提取**: 自动提取新闻的关键信息，包括标题、内容、发布时间、作者、来源URL等。
- **智能处理**:
    - 自动提取关联股票信息。
    - 可选的情感分析倾向判断。
    - 模拟浏览器行为，降低被封锁风险。
    - 智能内容识别与清理，去除广告和无关元素（网易财经现已禁用过滤功能）。
- **浏览器自动化**:
    - 支持 Selenium 和 Playwright 进行浏览器自动化。
    - 处理动态加载内容，提高爬取成功率。
    - 异步处理提高性能和效率。
- **数据库支持**:
    - 每个来源可使用独立数据库，便于管理和扩展。
    - 支持多数据库自动发现和灵活配置路径。
- **优化的用户界面**:
    - 现代化的视觉设计与交互体验。
    - 响应式布局，适配各种设备屏幕尺寸。
    - 直观的数据筛选与操作界面。

## 最新更新 (建议移至 CHANGELOG.md)

### 2025-05-29
- **修复数据中心趋势图显示问题**
  - 优化Chart.js图表初始化逻辑，解决趋势图无法显示的问题
  - 改进数据传递方式，确保JavaScript正确处理Jinja2模板变量
  - 添加错误捕获和DOM元素检查，提高图表渲染稳定性
  - 增强数据格式验证，避免无效数据导致图表渲染失败
  - 修复了空数据情况下的图表显示问题

### 2025-05-28
- **数据中心界面优化**，解决显示问题并改进整体体验
  - 修复趋势图无法显示的问题
  - 解决已删除数据库的新闻仍然显示的问题 
  - 优化左侧筛选区与主内容区域布局比例
  - 增强图表和表格的视觉体验
  - 添加数据检查和过滤机制，确保数据有效性
  - 改进数据查询逻辑，提高统计准确性
  - 增强了筛选条件的交互体验
  - 添加了错误提示和数据加载状态显示

### 2025-05-25
- **全面优化用户界面**，提升系统操作体验和视觉效果
  - 优化新闻列表布局，采用交替背景色和标准化信息层级排版
  - 改进筛选条件布局，增大间距和突出操作按钮
  - 增强分页控件，提供更大的点击区域和更好的交互反馈
  - 统一卡片和列表元素的视觉风格，提升整体一致性
  - 添加排序功能，支持按发布时间和情感值排序
  - 优化移动端响应式布局，提高不同设备的使用体验

### 2025-05-20

- 修复**凤凰财经爬虫编码问题**，解决爬取的新闻不显示在Web页面的问题
- 增强了凤凰财经爬虫的编码处理能力，支持多种编码格式自动识别（UTF-8、GBK、GB18030）
- 优化了数据库连接配置，确保中文字符能正确保存
- 添加了专门的文本清理函数，处理特殊字符和乱码问题
- 完善了数据库结构检查，自动创建缺失的表结构

### 2025-05-19

- 添加**性能统计和监控功能**，全面分析爬虫效率
- 实时监控爬虫运行状态和资源占用
- 提供可视化仪表板，展示详细性能指标
- 支持历史数据查询和趋势分析
- 访问路径: `/monitor` 查看性能监控仪表板

### 2025-05-18

- 为爬虫添加**数据库事务支持和并发控制**，大幅提升数据库操作可靠性
- 创建 TransactionalDBManager 类，支持事务操作和并发写入
- 数据库操作增加自动重试机制，避免锁冲突导致的失败
- 添加 WAL 模式和批量处理，提高数据库性能和稳定性

### 2025-05-17

- 为爬虫添加**异步支持**，使用 aiohttp 实现高效并发爬取
- 创建 AsyncCrawler 基类，提供通用的异步爬取功能  
- 目前已支持东方财富和凤凰财经爬虫的异步版本，后续会逐步扩展到其他爬虫
- 添加了性能测试和演示脚本，异步爬虫性能提升显著
- 所有爬虫均支持回退机制，当异步爬取失败时自动使用同步方式

### 2025-05-16

- 统一了所有爬虫的日志输出格式，采用 `%(asctime)s [%(levelname)s] [%(name)s] %(message)s` 格式。
- 统一了日志文件命名规则，使用 `[爬虫名称]_YYYYMMDD.log` 格式。
- 优化了日志处理器管理，自动检测并移除重复的处理器。
- 更新了爬虫类中的自定义日志设置，统一使用核心日志模块。
- 创建了CHANGELOG.md文件，开始记录项目的详细更新历史。

### 2025-05-15

- 网易财经爬虫更新：根据需求禁用了广告URL过滤和广告图片过滤功能。
- 现在网易财经爬虫将爬取所有符合URL格式的内容，包括之前被识别为广告的URL。
- 保留所有图片内容，不再过滤可能的广告图片。

### 2025-05-12

- 修复凤凰财经爬虫日志重复输出问题，优化日志记录机制。
- 改进`get_crawler_logger`函数，确保避免日志处理器重复添加。
- 增强爬虫测试脚本，提供更清晰的日志处理器状态信息。

### 2025-05-01

- 移除腾讯财经爬虫模块，精简代码结构。
- 优化爬虫管理器，提高系统稳定性。
- 更新Web界面，移除腾讯财经相关选项。

### 2025-04-02

- 修复数据库路径处理，避免将文件路径误认为目录。
- 增强 `AdFilter`，支持动态加载广告过滤规则。
- 改进错误处理和日志记录。
- 优化数据库初始化和备用目录创建。
- 全面优化凤凰财经爬虫，增强页面适应性。
- 扩展内容选择器范围，更新 User-Agent。
- 实现智能内容识别与清理机制。
- 添加短内容和特殊页面处理。
- 增加多层次容错，优化日志。

*（此处省略了更早的更新记录，建议创建一个 `CHANGELOG.md` 文件来存放完整的更新历史）*

## 安装说明

1.  **克隆仓库**:
    ```bash
    git clone <your-repository-url>
    cd NewsLook
    ```
2.  **创建并激活虚拟环境** (推荐):
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # macOS / Linux
    python -m venv venv
    source venv/bin/activate
    ```
3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
    *请确保你的 Python 版本符合项目要求 (例如 Python 3.8+)*。

4.  **安装 Playwright 浏览器**:
    ```bash
    # 安装 Playwright 浏览器（首次使用时需要）
    playwright install
    ```

## 配置说明

- **主要配置文件**: 项目的配置可能分散在 `config.py`, `config.ini` 或 `.env` 文件中（请根据实际情况填写）。
- **数据库配置**:
    - 默认使用 SQLite 数据库，存储在 `data/db/` 或 `db/` 目录下。
    - 系统会自动发现这些目录下的数据库文件。
    - 如果需要使用其他数据库或指定特定路径，请修改相关配置（例如通过 `--db-path` 参数或配置文件）。
- **代理配置**: 如需使用代理 (`--use-proxy` 参数)，请确保代理服务可用并在配置中正确设置代理地址。
- **环境变量**: 敏感信息（如 API 密钥）应通过环境变量或安全的配置文件管理，避免硬编码。
- **浏览器自动化配置**:
    - 默认使用 Playwright 处理动态内容加载。
    - 可以通过配置选择使用 Selenium 或 Playwright。
- **广告过滤配置**:
    - 大部分爬虫支持广告URL和图片过滤功能。
    - 网易财经爬虫自2025-05-15起已禁用广告URL过滤和图片过滤功能，将爬取所有内容。
    - 其他爬虫仍继续使用AdFilter进行广告过滤。
- **日志系统配置**:
    - 系统使用层次化的日志结构，为每个爬虫提供专门的日志记录器。
    - 日志文件按日期和爬虫类型自动组织，存储在 `logs/<爬虫名称>/` 目录下。
    - 通过 `--log-level` 参数设置日志级别（DEBUG, INFO, WARNING, ERROR），默认为 INFO。
    - 使用 `get_crawler_logger()` 函数获取爬虫专用日志记录器，避免日志冲突。
    - 日志输出格式统一为 `%(asctime)s [%(levelname)s] [%(name)s] %(message)s`，方便日志分析和问题追踪。
    - 2025-05-21 更新：修复了凤凰财经爬虫日志路径问题，现在使用 `os.path.abspath` 确保日志文件位置正确。
    - 2025-05-21 更新：改进日志记录器初始化方式，避免继承问题导致的日志重复输出。
    - 2025-05-21 更新：每个爬虫现在使用独立的日志记录器和处理器，不共享处理器，避免日志配置冲突。
    - 2025-05-12 更新：优化了日志处理器管理，修复了凤凰财经爬虫日志重复输出问题。

## 项目结构

```
NewsLook/
├── app/                  # 主应用模块
│   ├── crawlers/         # 爬虫模块 (核心)
│   │   ├── __init__.py
│   │   ├── base.py       # 爬虫基类
│   │   ├── manager.py    # 爬虫管理器
│   │   └── [specific_crawlers].py # 各网站爬虫实现
│   ├── db/               # 数据库模块
│   ├── models/           # 数据模型
│   ├── tasks/            # 任务模块 (如调度器)
│   ├── utils/            # 通用工具模块
│   ├── web/              # Web应用模块
│   │   ├── static/
│   │   └── templates/
│   ├── config.py         # 应用配置
│   └── __init__.py
│
├── newslook/             # 新版应用模块
│   ├── api/              # API接口模块
│   ├── core/             # 核心逻辑
│   ├── models/           # 数据模型
│   └── ...
│
├── data/                 # 数据存储目录 (数据库、输出文件等)
│   ├── db/               # 默认数据库存放目录
│   └── output/           # 默认输出文件目录
│
├── db/                   # 备选数据库存放目录
│
├── docs/                 # 项目文档
│   ├── architecture/     # 架构文档
│   ├── api/              # API文档
│   └── ...
│
├── logs/                 # 日志文件目录
│   ├── crawlers/         # 各爬虫日志
│   └── web/              # Web应用日志
│
├── scripts/              # 辅助脚本目录
│   ├── db_utils/         # 数据库工具
│   ├── search_utils/     # 搜索工具
│   └── web_utils/        # Web应用工具
│
├── static/               # Web应用静态文件
├── templates/            # Web应用模板
│
├── tests/                # 测试代码目录
│   ├── unit/             # 单元测试
│   └── integration/      # 集成测试
│
├── requirements.txt      # Python 依赖库
├── requirements/         # 按环境分类的依赖文件 (可选)
├── run.py                # 主运行入口脚本
├── main.py               # 另一个入口脚本
├── start.bat / start.sh  # 启动脚本示例
├── README.md             # 项目说明文件
└── ...                   # 其他配置文件 (.gitignore, .editorconfig 等)
```

## 使用说明

本项目可以通过 `run.py` 脚本以不同模式启动。

### 命令行模式

**基础命令格式**:
```bash
python run.py [模式] [选项]
```

**主要模式**:

1.  **爬虫模式 (`crawler`)**: 单次执行爬虫任务。
    ```bash
    # 爬取所有来源的最近一天新闻
    python run.py crawler --source all --days 1

    # 爬取新浪财经的股票分类新闻，最多20条
    python run.py crawler --source sina --category 股票 --max-news 20

    # 使用优化版爬虫爬取网易财经新闻，并使用代理
    python run.py crawler --source netease --optimized --use-proxy
    ```

2.  **调度器模式 (`scheduler`)**: 定时自动执行爬虫任务。
    ```bash
    # 每隔1小时 (3600秒) 爬取一次所有来源的新闻
    python run.py scheduler --interval 3600 --source all
    ```

3.  **Web应用模式 (`web`)**: 启动Web界面。
    ```bash
    # 启动Web应用，监听默认端口 (如 8000)
    python run.py web

    # 启动Web应用，指定端口为 8080
    python run.py web --port 8080
    ```
    启动后，可以通过浏览器访问 `http://127.0.0.1:端口号` 来查看新闻数据或进行管理操作。

**通用选项**:

```bash
--source SOURCE       指定新闻来源 (sina, netease, ifeng, eastmoney, all)
--days DAYS           爬取最近几天的数量 (默认 1)
--category CATEGORY   指定新闻分类 (需要爬虫支持)
--max-news MAX_NEWS   每个分类最多爬取数量
--use-proxy           是否启用代理
--db-path DB_PATH     指定数据库文件或目录路径
--source-db           是否为每个来源使用独立数据库
--log-level LEVEL     日志级别 (DEBUG, INFO, WARNING, ERROR), 默认 INFO
--log-dir LOG_DIR     日志存储目录 (默认 ./logs)
--output-dir OUTPUT_DIR 输出文件目录 (默认 ./data/output)
--debug               开启调试模式
--interval INTERVAL   调度器模式下的执行间隔 (秒)
--port PORT           Web模式下的监听端口
--optimized           使用优化版的爬虫 (如果存在)
```
*（请参考 `run.py --help` 获取最全最新的参数列表和说明）*

### 批处理脚本

项目提供了 `start.bat` (Windows) 和 `start.sh` (Linux/macOS) 脚本，可能包含了一些常用的启动命令组合，方便快速启动。

```bash
# Windows 示例
start.bat crawler all

# Linux/macOS 示例
./start.sh web
```

### API 说明

如果项目提供了 API 接口（可能通过 `newslook/api/` 或 `app/web/` 实现），请在此处说明：

-   API 的基础 URL。
-   主要的 API 端点及其功能。
-   请求和响应格式示例。
-   认证方式（如 API Key, JWT 等）。
-   指向详细 API 文档的链接（例如 `docs/api/` 下的 Swagger 或 Markdown 文件）。

### 运行测试

```bash
# 运行所有测试用例
pytest tests/

# 运行特定模块的测试
pytest tests/unit/test_crawler.py
```

## 开发指南

### 爬虫开发最佳实践

1. **继承基类**：所有爬虫应继承 `BaseCrawler` 类，并实现必要的方法。
   ```python
   from app.crawlers.base import BaseCrawler
   
   class YourCrawler(BaseCrawler):
       # 实现必要方法
   ```

2. **日志使用**：
   - 使用 `get_crawler_logger` 函数获取专用日志记录器
   - 避免在爬虫类中重复配置日志处理器
   - 正确使用不同级别的日志（DEBUG, INFO, WARNING, ERROR）
   ```python
   from app.utils.logger import get_crawler_logger
   
   # 在模块级别创建日志记录器
   logger = get_crawler_logger('your_crawler_name')
   
   class YourCrawler(BaseCrawler):
       def crawl(self):
           logger.info("开始爬取...")
           # 爬取逻辑
   ```

3. **异常处理**：
   - 使用 try-except 块捕获所有预期异常
   - 适当记录异常信息
   - 使用 `log_exception` 函数记录完整异常堆栈
   ```python
   from app.utils.logger import log_exception
   
   try:
       # 可能抛出异常的代码
   except Exception as e:
       log_exception(logger, e, "爬取过程中出错")
   ```

4. **防止日志重复**：
   - 不要在爬虫类中手动创建和添加日志处理器
   - 如果需要自定义日志，修改 `get_crawler_logger` 的参数而非手动配置
   - 2025-05-12更新：日志系统现已优化，会自动检测并清除重复的处理器

5. **代码风格**：
   - 遵循 PEP 8 代码风格指南
   - 添加适当的类型注解
   - 每个函数和类都应有文档字符串

### 日志系统详解

1. **日志级别**：
   - DEBUG：详细调试信息，包括HTTP请求详情、解析步骤等
   - INFO：常规信息，如爬取进度、成功提取的新闻数量等
   - WARNING：警告信息，如解析失败但不影响整体爬取的情况
   - ERROR：错误信息，导致部分功能失败的情况
   - CRITICAL：严重错误，导致整个爬虫无法工作的情况

2. **日志文件位置**：
   - 系统日志：`logs/finance_news_crawler.log`
   - 爬虫专用日志：`logs/<爬虫名称>/<日期>.log` 或 `logs/<爬虫名称>/<日期>_<序号>.log`
   - Web应用日志：`logs/web/web.log`

3. **日志格式**：
   ```
   2025-05-12 10:30:45 [INFO] [crawler.ifeng] 开始爬取凤凰财经新闻，爬取天数: 1
   ```
   包含时间戳、日志级别、日志记录器名称和消息内容。

4. **日志注意事项**：
   - 避免在循环中过度记录日志，特别是DEBUG级别
   - 敏感信息（如密码、API密钥）不应记录在日志中
   - 在生产环境中，建议使用INFO或更高级别的日志

## 支持的爬虫来源

目前系统支持以下财经新闻来源：

1. **东方财富** (EastMoneyCrawler)
2. **新浪财经** (SinaCrawler)
3. **网易财经** (NeteaseCrawler)
4. **凤凰财经** (IfengCrawler)

> 注意：腾讯财经爬虫模块已于2025-05-01移除。如需该功能，请参考历史版本。

## 使用说明

本项目可以通过 `run.py` 脚本以不同模式启动。

### 命令行模式

**基础命令格式**:
```bash
python run.py [模式] [选项]
```

**主要模式**:

1.  **爬虫模式 (`crawler`)**: 单次执行爬虫任务。
    ```bash
    # 爬取所有来源的最近一天新闻
    python run.py crawler --source all --days 1

    # 爬取新浪财经的股票分类新闻，最多20条
    python run.py crawler --source sina --category 股票 --max-news 20

    # 使用优化版爬虫爬取网易财经新闻，并使用代理
    python run.py crawler --source netease --optimized --use-proxy
    ```

2.  **调度器模式 (`scheduler`)**: 定时自动执行爬虫任务。
    ```bash
    # 每隔1小时 (3600秒) 爬取一次所有来源的新闻
    python run.py scheduler --interval 3600 --source all
    ```

3.  **Web应用模式 (`web`)**: 启动Web界面。
    ```bash
    # 启动Web应用，监听默认端口 (如 8000)
    python run.py web

    # 启动Web应用，指定端口为 8080
    python run.py web --port 8080
    ```
    启动后，可以通过浏览器访问 `http://127.0.0.1:端口号` 来查看新闻数据或进行管理操作。

**通用选项**:

```bash
--source SOURCE       指定新闻来源 (sina, netease, ifeng, eastmoney, all)
--days DAYS           爬取最近几天的数量 (默认 1)
--category CATEGORY   指定新闻分类 (需要爬虫支持)
--max-news MAX_NEWS   每个分类最多爬取数量
--use-proxy           是否启用代理
--db-path DB_PATH     指定数据库文件或目录路径
--source-db           是否为每个来源使用独立数据库
--log-level LEVEL     日志级别 (DEBUG, INFO, WARNING, ERROR), 默认 INFO
--log-dir LOG_DIR     日志存储目录 (默认 ./logs)
--output-dir OUTPUT_DIR 输出文件目录 (默认 ./data/output)
--debug               开启调试模式
--interval INTERVAL   调度器模式下的执行间隔 (秒)
--port PORT           Web模式下的监听端口
--optimized           使用优化版的爬虫 (如果存在)
```
*（请参考 `run.py --help` 获取最全最新的参数列表和说明）*

### 批处理脚本

项目提供了 `start.bat` (Windows) 和 `start.sh` (Linux/macOS) 脚本，可能包含了一些常用的启动命令组合，方便快速启动。

```bash
# Windows 示例
start.bat crawler all

# Linux/macOS 示例
./start.sh web
```

### API 说明

如果项目提供了 API 接口（可能通过 `newslook/api/` 或 `app/web/` 实现），请在此处说明：

-   API 的基础 URL。
-   主要的 API 端点及其功能。
-   请求和响应格式示例。
-   认证方式（如 API Key, JWT 等）。
-   指向详细 API 文档的链接（例如 `docs/api/` 下的 Swagger 或 Markdown 文件）。

### 运行测试

```bash
# 运行所有测试用例
pytest tests/

# 运行特定模块的测试
pytest tests/unit/test_crawler.py
```

## 主要依赖

本项目主要依赖以下 Python 库：

-   **Requests**: 用于发送 HTTP 请求
-   **BeautifulSoup4**: 用于解析HTML页面
-   **Flask**: Web应用框架
-   **SQLite3**: 轻量级数据库
-   **Playwright/Selenium**: 浏览器自动化工具
-   **Fake-UserAgent**: 生成随机User-Agent
-   **Logging**: 日志管理

## 贡献指南

欢迎为本项目做出贡献！如果你想参与开发，请遵循以下步骤：

1. Fork本仓库
2. 创建你的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启一个Pull Request

## 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 作者

项目团队 - [联系方式](mailto:your-email@example.com)

## 致谢

- 感谢所有为本项目做出贡献的开发者
- 感谢各个使用的开源库的作者

## 常见问题与故障排除

### 1. 日志重复输出问题 (已修复)

**问题描述**：在凤凰财经爬虫中，同一条日志会在控制台或日志文件中出现两次。

**原因**：爬虫中手动添加了日志处理器，而 `get_crawler_logger` 函数也会添加处理器，导致日志被输出两次。

**解决方法**：
1. 2025-05-12 版本中已修复此问题：`get_crawler_logger` 函数现在会检查并清除重复的处理器
2. 如果使用旧版本，手动修复方法：
   - 移除爬虫代码中手动添加的日志处理器配置（在 `app/crawlers/ifeng.py` 文件中）
   ```python
   # 注释或删除这些行
   # file_handler = logging.FileHandler(log_file, encoding='utf-8')
   # file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
   # logger.addHandler(file_handler)
   ```

### 2. 爬虫无法获取新闻内容

**问题描述**：爬虫运行时未能提取到新闻内容或内容不完整。

**可能原因**：
- 网站结构发生变化，选择器已过时
- 被目标网站的反爬机制阻止
- 连接超时或网络不稳定

**解决方法**：
1. 检查网站是否正常访问，手动确认内容位置
2. 更新选择器以适应新的页面结构
3. 增加休眠时间减轻爬取压力
4. 检查日志文件获取详细错误信息

### 3. 数据库连接问题

**问题描述**：爬虫运行时出现数据库连接错误。

**可能原因**：
- 数据库文件路径错误
- 数据库文件权限问题
- 数据库被锁定（多线程/进程访问）

**解决方法**：
1. 确保数据库目录存在并有正确权限
2. 使用 `--db-path` 参数指定正确的数据库路径
3. 检查是否有多个进程同时访问数据库

## 使用说明

### 常规使用

```python
from app.crawlers import get_crawler

# 创建爬虫实例
crawler = get_crawler("东方财富")

# 爬取新闻
news_list = crawler.crawl(days=3, max_news=100)

# 输出结果
for news in news_list[:5]:  # 只显示前5条
    print(f"标题: {news['title']}")
    print(f"日期: {news['pub_time']}")
    print(f"链接: {news['url']}")
    print("-" * 50)
```

### 使用异步爬虫

```python
from app.crawlers import get_crawler

# 创建异步爬虫实例（目前支持东方财富和凤凰财经）
crawler = get_crawler("东方财富", use_async=True, max_concurrency=8)

# 爬取新闻（与同步爬虫API相同）
news_list = crawler.crawl(days=3, max_news=100)

# 输出结果
print(f"共爬取 {len(news_list)} 条新闻")
```

### 性能测试

可以使用提供的演示脚本比较同步和异步爬虫的性能差异：

```bash
# 运行完整演示
python scripts/async_crawler_demo.py

# 测试特定爬虫
python scripts/async_crawler_demo.py --mode specific --source 东方财富

# 运行性能测试并生成对比图表
python scripts/async_crawler_demo.py --mode test --source 东方财富 --max_news 30
```

## 数据库优化

系统智能识别并使用多个数据库文件，确保您可以查看所有历史爬取的新闻数据。

### 多数据库支持特性

- **自动数据库发现：** 系统自动搜索可能的数据库目录，查找并使用所有可用的数据库文件。
- **灵活的数据库位置：** 支持多个可能的数据库位置，按优先顺序搜索：
    - `./data/db/` (项目根目录下的data/db目录)
    - `./db/` (项目根目录下的db目录)
    - 当前工作目录下的相应目录
- **命令行参数：** 使用 `--db-dir` 参数明确指定数据库目录。
- **合并查询结果：** 查询并合并来自多个数据库文件的结果，提供完整的数据视图。

### 如何使用多数据库功能

系统默认启用多数据库功能。启动Web应用程序时，它会自动搜索并使用所有可用的数据库文件：

```bash
# 使用自动检测的数据库目录
python run.py web

# 指定数据库目录
python run.py web --db-dir path/to/your/db
```

在控制台输出中，您可以看到系统找到的数据库文件：

```
找到主数据库: /path/to/your/db/finance_news.db
找到 X 个数据库文件
```

### 数据库搜索逻辑

1. 首先，检查命令行参数 `--db-dir` 是否指定了数据库目录。
2. 如果未指定，则检查环境变量 `DB_DIR`。
3. 如果未设置环境变量，则按优先顺序在可能的目录中搜索包含 `.db` 文件的第一个有效目录。
4. 如果所有目录都不存在或不包含数据库文件，则创建并使用默认目录。

### 数据中心界面优化

为提供更好的数据可视化体验，我们对数据中心页面进行了全面优化：

- **布局优化**
  - 调整左侧筛选区与主内容区域的比例，实现更合理的空间分配
  - 左侧筛选栏在滚动时固定可见，便于随时调整筛选条件
  - 采用响应式布局，适配不同设备屏幕尺寸
  
- **图表与数据显示改进**
  - 优化趋势图和来源分布图表的显示效果
  - 增强表格样式，增加行高、间距和背景色交替
  - 添加图表数据验证和过滤功能，确保数据有效性
  - 优化空数据状态的提示和反馈

- **数据查询逻辑优化**
  - 改进数据库查询方式，确保移除已删除数据库的统计
  - 优化日期范围查询，提高趋势数据准确性
  - 添加数据缓存机制，提升页面加载速度

- **交互体验增强**
  - 增加筛选条件的直观操作界面
  - 提供日期快捷选择功能
  - 添加数据加载状态和错误状态提示
  - 提供一键重置筛选条件功能

- **问题修复**
  - 解决趋势图无法显示的问题
  - 修复已删除数据库的新闻仍会显示在统计中的问题
  - 优化图表初始化逻辑，增强错误处理能力

通过这些优化，数据中心页面现在提供了更加直观、易用的数据分析体验，使用户能够更有效地获取和理解新闻数据统计信息。

### 编码优化与乱码处理
