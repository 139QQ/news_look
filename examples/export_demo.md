# NewsLook 数据导出工具使用指南

## 简介

NewsLook 数据导出工具是一个专门用于将爬取的财经新闻数据导出为多种格式的实用工具。该工具能够从爬虫生成的 SQLite 数据库中读取新闻文章，并将其转换为 CSV、Excel 或 JSON 格式，方便用户进行后续的数据分析、处理或存档。

## 功能特点

- **多格式支持**：支持导出为 CSV、Excel 和 JSON 三种常用数据格式
- **灵活的日期筛选**：可按日期范围筛选要导出的新闻数据
- **批量导出**：可一次性将数据导出为多种格式
- **自动生成文件名**：基于数据源和时间戳自动命名导出文件
- **详细的日志记录**：记录导出过程中的关键信息和可能的错误

## 使用方法

### 命令行参数

| 参数 | 说明 | 默认值 |
|-----|-----|-----|
| `db_path` | SQLite 数据库文件路径（必填） | - |
| `--format` | 导出格式，可选 `csv`、`excel`、`json` 或 `all` | `all` |
| `--output-dir` | 导出文件保存目录 | `data/exports` |
| `--start-date` | 开始日期（YYYY-MM-DD格式） | - |
| `--end-date` | 结束日期（YYYY-MM-DD格式） | - |

### 使用示例

1. 导出所有格式（CSV、Excel、JSON）：

```bash
python examples/export_demo.py data/sina_finance.db
```

2. 仅导出为 CSV 格式：

```bash
python examples/export_demo.py data/sina_finance.db --format csv
```

3. 导出指定日期范围的数据：

```bash
python examples/export_demo.py data/sina_finance.db --start-date 2023-01-01 --end-date 2023-01-31
```

4. 导出到自定义目录：

```bash
python examples/export_demo.py data/sina_finance.db --output-dir my_exports
```

5. 组合使用多个参数：

```bash
python examples/export_demo.py data/eastmoney.db --format excel --start-date 2023-05-01 --output-dir financial_data/q2
```

## 输出内容说明

### CSV 格式

- 文件命名：`{数据库名}_{时间戳}.csv`
- 特点：以逗号分隔的表格数据，UTF-8-SIG 编码（支持中文且兼容 Excel）
- 适用场景：通用数据分析，可被大多数数据处理工具识别

### Excel 格式

- 文件命名：`{数据库名}_{时间戳}.xlsx`
- 特点：直接可用于 Microsoft Excel 或 WPS 等办公软件打开
- 适用场景：数据可视化、筛选和基本分析

### JSON 格式

- 文件命名：`{数据库名}_{时间戳}.json`
- 特点：结构化数据，保留完整的数据结构，美化格式便于阅读
- 适用场景：Web 应用开发，需要结构化数据的场景

## 字段说明

导出的数据包含以下主要字段：

- `id`: 文章唯一标识符
- `title`: 文章标题
- `url`: 文章原始链接
- `content`: 文章正文内容
- `summary`: 文章摘要
- `publish_date`: 发布日期时间
- `source`: 新闻来源（如"新浪财经"）
- `author`: 作者（如果有）
- `category`: 文章分类（如"股市"、"财经要闻"等）
- `keywords`: 关键词（如果有）
- `crawl_time`: 爬取时间

## 性能说明

- 对于大型数据库（包含数千篇文章），导出过程可能需要较长时间，请耐心等待
- Excel 格式导出对内存要求较高，如果数据量非常大，建议使用 CSV 格式
- JSON 格式导出时会默认美化输出，文件体积相对较大
- 导出目录会自动创建，无需手动创建

## 常见问题

### Q: 导出时出现"没有找到符合条件的文章"提示

A: 请检查：
- 数据库路径是否正确
- 日期范围是否有效
- 数据库中是否确实包含文章数据

### Q: 如何查看数据库中包含哪些日期范围的文章？

A: 可以先不指定日期范围，导出所有文章，然后查看导出文件中的日期分布。

### Q: 导出的 Excel 文件中日期格式显示不正确

A: Excel 有时会错误识别日期格式，可以在 Excel 中手动设置日期列的格式。

### Q: 文件体积过大难以处理

A: 尝试使用日期范围参数限制导出的数据量，或考虑使用分批次导出的方式。

## 开发说明

如需扩展此工具的功能，可以修改 `export_demo.py` 文件。主要的类和方法包括：

- `NewsExporter` 类：核心导出功能类
- `get_articles_by_date` 方法：可扩展其他过滤条件
- 各种 `export_to_*` 方法：可添加新的导出格式 