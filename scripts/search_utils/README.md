# 新闻搜索工具

此目录包含与新闻搜索和检索相关的工具脚本：

- `search_main_db.py` - 搜索主数据库中的新闻
- `search_tencent_news.py` - 专门搜索腾讯财经新闻
- `get_full_news.py` - 根据标题获取完整新闻内容并保存为HTML和文本格式
- `get_news.py` - 简单的新闻获取工具
- `search_news.py` - 通用的新闻搜索工具

## 使用方法

### 搜索主数据库
```bash
python search_main_db.py "关键词"
```

### 获取完整新闻内容
```bash
python get_full_news.py "文章标题"
```

### 搜索腾讯财经新闻
```bash
python search_tencent_news.py "关键词"
``` 