# NewsLook 升级指南

## 🎯 推荐升级策略

### 小型项目 (< 10万条新闻)
```bash
# 推荐：SQLite优化
python scripts/emergency_sqlite_optimization.py

# 收益：
# • 立即生效，无停机时间
# • 性能提升100%
# • 实施成本最低
```

### 中型项目 (10万-100万条新闻)
```bash
# 推荐：PostgreSQL迁移
python scripts/migrate_sqlite_to_postgresql.py

# 收益：
# • 性能提升12倍
# • 支持500并发连接
# • 企业级稳定性
```

### 大型项目 (> 100万条新闻)
```bash
# 推荐：完整现代化架构
cd deploy/docker
docker-compose up -d

# 收益：
# • 性能提升70倍
# • 支持1000+并发
# • 实时分析能力
# • 完整监控体系
```

## 🚨 迁移注意事项

### 数据备份
```bash
# 迁移前必须备份
cp -r data/db data/db_backup_$(date +%Y%m%d)

# 或使用Git提交当前状态
git add -A && git commit -m "Migration backup $(date)"
```

### 环境准备
```bash
# 检查系统资源
df -h          # 磁盘空间 (至少剩余数据库大小的3倍)
free -h        # 内存 (推荐8GB+用于大数据量迁移)
docker --version  # Docker版本 (用于现代化部署)
```

### 回滚计划
```bash
# 如果迁移出现问题，快速回滚
docker-compose down           # 停止现代化服务
cp -r data/db_backup/* data/db/  # 恢复原始数据
python app.py                 # 启动原系统
```

## 🔄 版本间升级指南

### v4.0 → v4.1 升级 (推荐)

#### 准备工作
```bash
# 1. 备份现有数据
cp -r data/db data/db_backup_$(date +%Y%m%d)

# 2. 停止现有服务
ps aux | grep "python.*app.py" | awk '{print $2}' | xargs kill -9
```

#### 升级步骤
```bash
# 1. 更新代码
git pull origin main

# 2. 升级Python依赖
pip install -r requirements.txt --upgrade

# 3. 检查系统健康
python -c "
from backend.newslook.web import create_app
from backend.newslook.api.crawler_control import crawler_control_bp
print('✅ 系统健康检查通过')
"

# 4. 重启服务
python app.py
```

#### 验证升级
```bash
# 验证API功能
curl -s http://localhost:5000/api/health | jq '.'

# 验证数据完整性
python -c "
from backend.newslook.utils.database import NewsDatabase
db = NewsDatabase()
print(f'数据库记录数: {db.get_news_count()}')
"
```

### v3.x → v4.0 升级 (重大更新)

#### 架构变化
- 数据库从SQLite迁移到PostgreSQL + ClickHouse
- 前端从传统模板升级到Vue 3 SPA
- API从简单路由升级到RESTful标准

#### 详细步骤

**Phase 1: 环境准备**
```bash
# 1. 停止v3.x服务
pkill -f "python.*app.py"

# 2. 完整备份
tar -czf newslook_v3_backup_$(date +%Y%m%d).tar.gz data/ configs/

# 3. 安装Docker (如果尚未安装)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 4. 安装Node.js (前端构建需要)
curl -fsSL https://nodejs.org/dist/v18.17.0/node-v18.17.0-linux-x64.tar.xz | tar -xJ
```

**Phase 2: 数据迁移**
```bash
# 1. 使用迁移脚本
python scripts/migrate_v3_to_v4.py \
  --source data/db/ \
  --target postgresql://user:pass@localhost/newslook \
  --batch-size 1000

# 2. 验证迁移结果
python scripts/verify_migration.py
```

**Phase 3: 配置更新**
```bash
# 1. 更新配置文件
cp configs/v3_config.yaml configs/v4_config.yaml
python scripts/update_config_v4.py

# 2. 环境变量设置
export NEWSLOOK_DB_URL="postgresql://user:pass@localhost/newslook"
export NEWSLOOK_CLICKHOUSE_URL="clickhouse://localhost:8123/newslook"
```

**Phase 4: 服务启动**
```bash
# 1. 启动基础服务
cd deploy/docker
docker-compose up -d postgres clickhouse redis

# 2. 构建前端
cd frontend
npm install
npm run build

# 3. 启动应用
python app.py --config configs/v4_config.yaml
```

### v2.x → v3.x 升级

#### 主要变化
- 引入前端框架
- API标准化
- 数据库结构优化

#### 升级步骤
```bash
# 1. 数据库结构升级
python scripts/upgrade_db_v2_to_v3.py

# 2. 安装新依赖
pip install -r requirements/v3.txt
npm install

# 3. 迁移配置
python scripts/migrate_config_v2_to_v3.py

# 4. 启动新版本
python app.py --version 3
```

## 🛠️ 迁移工具和脚本

### 自动化迁移脚本

**SQLite to PostgreSQL 迁移**
```python
#!/usr/bin/env python3
"""
SQLite到PostgreSQL迁移工具
"""
import sqlite3
import psycopg2
import sys
from datetime import datetime

def migrate_sqlite_to_postgresql(sqlite_path, pg_config):
    """迁移SQLite数据到PostgreSQL"""
    print(f"🔄 开始迁移: {sqlite_path} → PostgreSQL")
    
    # 连接SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()
    
    # 连接PostgreSQL
    pg_conn = psycopg2.connect(**pg_config)
    pg_cursor = pg_conn.cursor()
    
    # 创建表结构
    create_tables(pg_cursor)
    
    # 迁移数据
    migrate_data(sqlite_cursor, pg_cursor)
    
    # 提交事务
    pg_conn.commit()
    
    print("✅ 迁移完成")

def create_tables(pg_cursor):
    """创建PostgreSQL表结构"""
    tables = {
        'news': '''
            CREATE TABLE IF NOT EXISTS news (
                id VARCHAR PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                pub_time TIMESTAMP,
                source VARCHAR,
                url VARCHAR UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'sources': '''
            CREATE TABLE IF NOT EXISTS sources (
                id SERIAL PRIMARY KEY,
                name VARCHAR UNIQUE,
                url VARCHAR,
                status VARCHAR DEFAULT 'active'
            )
        '''
    }
    
    for table_name, sql in tables.items():
        pg_cursor.execute(sql)
        print(f"✅ 创建表: {table_name}")

def migrate_data(sqlite_cursor, pg_cursor):
    """迁移数据"""
    # 迁移新闻数据
    sqlite_cursor.execute("SELECT * FROM news")
    news_data = sqlite_cursor.fetchall()
    
    for row in news_data:
        pg_cursor.execute("""
            INSERT INTO news (id, title, content, pub_time, source, url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, row)
    
    print(f"✅ 迁移新闻数据: {len(news_data)} 条")

if __name__ == "__main__":
    pg_config = {
        'host': 'localhost',
        'database': 'newslook',
        'user': 'postgres',
        'password': 'password'
    }
    
    migrate_sqlite_to_postgresql('data/db/finance_news.db', pg_config)
```

### 配置迁移工具
```bash
# 配置文件格式转换
python -c "
import yaml
import json

# 读取旧配置
with open('config.json', 'r') as f:
    old_config = json.load(f)

# 转换为新格式
new_config = {
    'database': {
        'url': old_config['database']['path'],
        'pool_size': 10,
        'timeout': 30
    },
    'crawler': {
        'sources': old_config['sources'],
        'concurrent': old_config.get('concurrent', 5),
        'delay': old_config.get('delay', 1.0)
    }
}

# 保存新配置
with open('config.yaml', 'w') as f:
    yaml.dump(new_config, f, default_flow_style=False)

print('✅ 配置文件已转换')
"
```

## 🔍 升级验证清单

### 功能验证
- [ ] 系统能够正常启动
- [ ] 所有API端点响应正常
- [ ] 数据查询功能正常
- [ ] 爬虫功能正常
- [ ] 前端界面正常显示
- [ ] 数据统计正确

### 性能验证
- [ ] 响应时间在预期范围内
- [ ] 并发处理能力正常
- [ ] 内存使用率合理
- [ ] 数据库查询效率正常

### 数据完整性验证
```bash
# 验证数据完整性
python -c "
from backend.newslook.utils.database import NewsDatabase
db = NewsDatabase()

# 检查数据总数
total = db.get_news_count()
print(f'总新闻数: {total}')

# 检查数据源分布
sources = db.get_sources()
print(f'数据源数: {len(sources)}')

# 检查最新数据
latest = db.query_news(limit=1, order_by='created_at DESC')
if latest:
    print(f'最新新闻: {latest[0][\"title\"]}')
"
```

## 🚨 回滚指南

### 快速回滚
```bash
# 1. 停止新版本服务
pkill -f "python.*app.py"
docker-compose down

# 2. 恢复数据备份
rm -rf data/db/
cp -r data/db_backup_*/ data/db/

# 3. 恢复配置
cp configs/backup_config.yaml configs/app.yaml

# 4. 重启旧版本
python app.py --version old
```

### 渐进式回滚
```bash
# 1. 启用维护模式
touch .maintenance_mode

# 2. 逐步切换流量
# 使用负载均衡器将流量从新版本切换到旧版本

# 3. 验证旧版本稳定性
curl -s http://localhost:5000/api/health

# 4. 完全切换后关闭新版本
```

## 📋 升级最佳实践

### 升级前准备
1. **完整备份**: 数据库、配置文件、日志文件
2. **环境检查**: 确保系统资源充足
3. **依赖检查**: 验证所有依赖项可用
4. **测试环境**: 先在测试环境完成升级验证

### 升级过程
1. **分阶段升级**: 避免一次性升级所有组件
2. **实时监控**: 监控系统状态和性能指标
3. **验证确认**: 每个阶段都要验证功能正常
4. **文档记录**: 记录升级过程和遇到的问题

### 升级后维护
1. **性能监控**: 持续监控系统性能
2. **错误日志**: 检查是否有新的错误日志
3. **用户反馈**: 收集用户使用反馈
4. **优化调整**: 根据实际使用情况进行优化

## 🤝 技术支持

### 升级遇到问题时
1. **查看日志**: 检查系统日志了解具体错误
2. **文档搜索**: 在本文档中搜索相关问题
3. **回滚操作**: 如果问题严重，先回滚到稳定版本
4. **寻求帮助**: 提交Issue或联系技术支持

### 联系方式
- GitHub Issues: [项目仓库](https://github.com/yourusername/NewsLook/issues)
- 技术文档: [在线文档](https://docs.newslook.com)
- 邮件支持: support@newslook.com

---

*最后更新: 2025-06-25*  
*维护者: NewsLook开发团队* 