# 编码规范

本文档定义了项目的编码规范，旨在保持代码一致性和可读性。

## 1. Python 版本

- 项目使用 Python 3.9 或更高版本

## 2. 代码格式化

### 2.1 格式化工具

项目使用以下工具来自动化代码格式化：

- **Black**: 自动格式化 Python 代码
- **isort**: 对导入语句进行排序

### 2.2 行长度

- 最大行长度为 88 个字符（Black 默认）
- 文档字符串和注释最大行长度为 80 个字符

### 2.3 缩进

- 使用 4 个空格进行缩进，不使用制表符
- 连续的行缩进应该对齐

## 3. 命名约定

### 3.1 一般命名规则

- 类名：使用 `CamelCase` (例如: `EastMoneyCrawler`)
- 函数和变量：使用 `snake_case` (例如: `crawl_news`, `article_count`)
- 常量：使用 `UPPER_CASE_WITH_UNDERSCORES` (例如: `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- 模块名：简短的、全小写的名称 (例如: `crawler.py`, `logger.py`)
- 包名：简短的、全小写的名称，避免使用下划线 (例如: `crawlers`, `utils`)

### 3.2 特殊命名约定

- 私有方法和属性以单下划线开头 (例如: `_extract_text`)
- 内部使用的类或函数以双下划线开头 (例如: `__format_data`)
- 避免使用单个字符的变量名，除非在简短的循环中

## 4. 代码组织

### 4.1 导入语句

- 导入应按照以下顺序排列：
  1. 标准库导入
  2. 第三方库导入
  3. 本地应用/库特定导入
- 各组之间应该用空行分隔
- 每个组内按字母顺序排序
- 避免使用通配符导入 (`from module import *`)

```python
# 正确的导入顺序示例
import os
import sys
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from app.utils.logger import get_logger
from app.db.sqlite_manager import SQLiteManager
```

### 4.2 类和函数

- 每个类和函数应该有文档字符串
- 相关的函数应该组合在一起
- 类方法顺序：
  1. 特殊方法 (`__init__`, `__str__`, 等)
  2. 公共方法
  3. 私有方法

### 4.3 行间距和空行

- 顶级函数和类定义之间用两个空行隔开
- 类内的方法定义之间用一个空行隔开
- 使用空行来分隔逻辑相关的代码块

## 5. 注释和文档

### 5.1 文档字符串格式

项目使用 Google 风格的文档字符串：

```python
def extract_news(url, timeout=30):
    """
    从给定URL提取新闻内容。
    
    Args:
        url: 新闻页面的URL
        timeout: 请求超时时间，默认30秒
        
    Returns:
        包含标题、内容、发布时间等信息的字典
        
    Raises:
        RequestError: 如果请求页面失败
    """
    # 实现代码...
```

### 5.2 行内注释

- 注释应该是完整的句子
- 行内注释应该在代码后至少两个空格，以 # 开始，然后再一个空格
- 避免不必要的注释，代码应该是自解释的

## 6. 错误处理

- 使用明确的异常类型，避免捕获所有异常
- 为捕获的异常提供有意义的错误消息
- 使用 `finally` 子句来清理资源

```python
try:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
except requests.exceptions.Timeout:
    logger.error(f"请求 {url} 超时")
    raise RequestError(f"请求超时: {url}")
except requests.exceptions.HTTPError as e:
    logger.error(f"HTTP错误: {e}")
    raise RequestError(f"HTTP错误: {url}, 状态码: {response.status_code}")
finally:
    # 清理代码
```

## 7. 代码检查

项目使用以下工具进行代码质量检查：

- **Pylint**: 代码分析工具，用于静态检查代码错误和风格问题
- **Mypy**: 静态类型检查

每次提交代码前应运行这些工具，确保代码符合规范：

```bash
# 格式化代码
black .
isort .

# 代码检查
pylint app tests
mypy app tests
```

## 8. 版本控制

### 8.1 Git 提交消息

提交消息应遵循以下格式：

```
<类型>: <简短描述>

<详细描述（可选）>
```

类型包括：
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更改
- `style`: 格式化、缺少分号等（不改变代码逻辑）
- `refactor`: 代码重构
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具的变动

### 8.2 分支管理

- `main`: 主分支，始终保持稳定
- `develop`: 开发分支
- 功能分支: 从`develop`分支创建，命名为`feature/<功能名称>`
- 修复分支: 命名为`fix/<错误描述>`

## 9. 测试

- 每个模块应该有相应的测试
- 测试文件命名为`test_<被测试模块>.py`
- 使用 pytest 运行测试

## 10. 文档

- 代码的变更应该反映在相应的文档中
- 新功能应该有对应的文档说明
- API更改应该更新API文档 