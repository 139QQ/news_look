数据库问题

## 数据库表结构不一致问题：

- 不同的实现中表结构字段不完全一致

- 有的使用 SQLAlchemy ORM，有的直接使用 SQLite

- 建议统一表结构，使用以下字段：

```sql
CREATE TABLE news (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    content_html TEXT,
    pub_time TEXT,
    author TEXT,
    source TEXT,
    url TEXT UNIQUE,
    keywords TEXT,
    images TEXT,
    related_stocks TEXT,
    sentiment TEXT,
    classification TEXT, 
    category TEXT,
    crawl_time TEXT,
    summary TEXT,
    status INTEGER DEFAULT 0
)
```

## 字段处理逻辑分散：

- 不同爬虫中的字段处理逻辑不统一

- 建议在基类中统一处理字段：

```python
def preprocess_news_data(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
    """统一预处理新闻数据"""
    # 确保必要字段存在
    if 'id' not in news_data or not news_data['id']:
        news_data['id'] = hashlib.md5(news_data['url'].encode('utf-8')).hexdigest()
        
    # 设置默认值
    defaults = {
        'author': self.source,
        'source': self.source,
        'sentiment': '中性',
        'category': '财经',
        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'keywords': '',
        'images': '',
        'related_stocks': '',
        'classification': '',
        'summary': '',
        'status': 0
    }
    
    for field, default in defaults.items():
        if field not in news_data or not news_data[field]:
            news_data[field] = default
            
    # 处理特殊字段
    for field in ['keywords', 'images', 'related_stocks']:
        if isinstance(news_data[field], (list, dict)):
            news_data[field] = json.dumps(news_data[field], ensure_ascii=False)
            
    return news_data
```

## 数据验证不统一：

- 有的实现检查 URL 重复，有的检查 ID 重复

- 建议统一使用复合唯一约束：

```sql
CREATE UNIQUE INDEX idx_news_id_url ON news(id, url);
```

## 事务处理不完善：

- 部分实现缺少事务回滚

- 建议统一使用上下文管理器：



```python
def save_news_to_db(self, news_data: Dict[str, Any]) -> bool:
    """统一的保存实现"""
    try:
        with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 预处理数据
                news_data = self.preprocess_news_data(news_data)
                
                # 检查重复
                cursor.execute(
                    "SELECT id FROM news WHERE id = ? OR url = ?",
                    (news_data['id'], news_data['url'])
                )
                if cursor.fetchone():
                    logger.info(f"新闻已存在: {news_data['title']}")
                    return True
                    
                # 插入数据
                fields = ['id', 'title', 'content', 'content_html', 'pub_time',
                         'author', 'source', 'url', 'keywords', 'images',
                         'related_stocks', 'sentiment', 'classification',
                         'category', 'crawl_time', 'summary', 'status']
                         
                placeholders = ','.join(['?' for _ in fields])
                sql = f"INSERT INTO news ({','.join(fields)}) VALUES ({placeholders})"
                
                values = [news_data.get(field) for field in fields]
                cursor.execute(sql, values)
                
                return True
                
    except Exception as e:
        logger.error(f"保存新闻失败: {str(e)}")
        return False
```

## 编码处理不统一：

- 建议统一使用 UTF-8 编码

- 添加编码处理工具函数：

```python
def ensure_utf8(text: str) -> str:
    """确保文本使用UTF-8编码"""
    if not isinstance(text, str):
        text = str(text)
        
    try:
        return text.encode('utf-8', 'ignore').decode('utf-8')
    except UnicodeError:
        try:
            return text.encode('latin1').decode('utf-8')
        except UnicodeError:
            return text.encode('ascii', 'ignore').decode('ascii')
```



## 日志记录优化：

- 统一日志格式

- 添加更多调试信息：

```python
def save_news_to_db(self, news_data: Dict[str, Any]) -> bool:
    """带详细日志的保存实现"""
    logger.debug(f"开始保存新闻: {news_data.get('title')}")
    logger.debug(f"数据库路径: {self.db_path}")
    
    try:
        # ... 保存逻辑 ...
        
        logger.info(f"成功保存新闻: {news_data['title']}")
        logger.debug(f"保存的字段: {list(news_data.keys())}")
        return True
        
    except Exception as e:
        logger.error(f"保存新闻失败: {str(e)}")
        logger.debug(f"失败的新闻数据: {news_data}")
        return False
```





## 性能优化建议：

- 添加适当的索引

- 批量插入支持

- 使用连接池

- 定期清理过期数据