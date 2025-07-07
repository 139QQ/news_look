# NewsLook 故障排除指南

## 🧠 智能问题诊断系统

### ❌ 常见错误自愈方案

```python
# 自动修复日志冲突 (v4.1+)
def auto_fix_log_conflict():
    """自动修复日志记录字段冲突"""
    if 'message' in log_record:
        log_record['log_message'] = log_record.pop('message')
    return True

# 数据库连接自动修复
def auto_fix_db_connection():
    """自动修复数据库连接问题"""
    import os
    if not os.path.exists('backend/data/'):
        os.makedirs('backend/data/', exist_ok=True)
    return "数据库目录已创建"
```

### 🔧 智能配置生成器

```bash
# 交互式配置向导
python -c "
import yaml, os
from pathlib import Path

def generate_smart_config():
    print('🚀 NewsLook智能配置生成器')
    env = input('部署环境 (dev/test/prod) [dev]: ').strip() or 'dev'
    
    config = {
        'environment': env,
        'database': {'type': 'sqlite', 'pool_size': 10},
        'crawler': {'concurrency': 5, 'delay': 1.0},
        'server': {'port': 5000, 'debug': env == 'dev'}
    }
    
    Path('configs').mkdir(exist_ok=True)
    with open(f'configs/{env}_generated.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    print('✅ 配置文件已生成')

try:
    import yaml
    generate_smart_config()
except ImportError:
    print('❌ 需要安装PyYAML: pip install pyyaml')
"
```

## 🔍 分步诊断流程

### 1. 启动失败诊断

```bash
# 全面环境检查
python -c "
import sys, os, subprocess
print('🐍 Python版本:', sys.version)
print('📂 当前目录:', os.getcwd())

# 检查关键文件
files = ['app.py', 'requirements.txt', 'frontend/package.json']
for file in files:
    print('✅' if os.path.exists(file) else '❌', file)

# 检查端口占用
import socket
def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

print('🌐 端口状态:')
print('  5000:', '🔴 占用' if check_port(5000) else '🟢 可用')
print('  3000:', '🔴 占用' if check_port(3000) else '🟢 可用')
"
```

### 2. 数据库连接问题

```bash
# 数据库健康检查 + 自动修复
python -c "
import os, sqlite3, sys
from pathlib import Path

def fix_database_issues():
    data_dir = Path('backend/data')
    data_dir.mkdir(parents=True, exist_ok=True)
    print('✅ 数据目录已确保存在')
    
    # 测试数据库连接
    try:
        conn = sqlite3.connect('backend/data/test.db')
        conn.execute('CREATE TABLE test (id INTEGER)')
        conn.commit()
        conn.close()
        print('✅ 数据库连接测试成功')
        os.remove('backend/data/test.db')
        return True
    except Exception as e:
        print(f'❌ 数据库连接失败: {e}')
        return False

fix_database_issues()
"
```

### 3. 前端构建问题

```bash
# 前端构建智能修复
cd frontend/
python -c "
import os, subprocess, shutil

def smart_frontend_rebuild():
    # 检查 Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        print(f'🟢 Node.js版本: {result.stdout.strip()}')
    except:
        print('❌ Node.js未安装')
        return False
    
    # 清理缓存
    if os.path.exists('node_modules'):
        shutil.rmtree('node_modules')
        print('🧹 已清理node_modules')
    
    # 重新安装
    result = subprocess.run(['npm', 'install'], capture_output=True, text=True)
    if result.returncode == 0:
        print('✅ 依赖安装成功')
        return True
    else:
        print(f'❌ 安装失败: {result.stderr}')
        return False

smart_frontend_rebuild()
"
```

## 🚨 常见错误速查

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `ModuleNotFoundError` | 缺少依赖 | `pip install -r requirements.txt` |
| `Address already in use` | 端口占用 | `python app.py --port 5001` |
| `Database connection failed` | 数据库问题 | 运行数据库修复脚本 |
| `TypeError: expected str, not NoneType` | 配置问题 | 检查环境变量和配置文件 |

## 📊 性能诊断工具

```python
# 性能基准测试
def benchmark_system():
    import time, sqlite3
    
    # 数据库性能测试
    test_queries = [
        'SELECT COUNT(*) FROM news',
        'SELECT * FROM news ORDER BY pub_time DESC LIMIT 10'
    ]
    
    for query in test_queries:
        start = time.time()
        try:
            conn = sqlite3.connect('data/db/finance_news.db')
            cursor = conn.cursor()
            cursor.execute(query)
            cursor.fetchall()
            conn.close()
            elapsed = (time.time() - start) * 1000
            
            performance = ('🚀 优秀' if elapsed < 10 else 
                         '⚡ 良好' if elapsed < 50 else 
                         '🔶 一般' if elapsed < 200 else '🔴 需优化')
            print(f'{performance} {query[:30]}... - {elapsed:.1f}ms')
        except Exception as e:
            print(f'❌ 查询失败: {e}')

benchmark_system()
```

## 🔄 自动修复脚本

```bash
# 一键修复常见问题
python -c "
import os, subprocess, shutil

def auto_fix_common_issues():
    print('🔧 开始自动修复...')
    
    # 1. 创建必要目录
    os.makedirs('data/db', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    print('✅ 目录结构已修复')
    
    # 2. 修复权限
    try:
        os.chmod('data/db', 0o755)
        print('✅ 权限已修复')
    except:
        print('⚠️ 权限修复失败')
    
    # 3. 检查依赖
    try:
        subprocess.run(['pip', 'check'], check=True)
        print('✅ Python依赖正常')
    except:
        print('⚠️ 发现依赖问题，建议运行: pip install -r requirements.txt')
    
    print('🎉 自动修复完成')

auto_fix_common_issues()
"
```

## 📋 问题诊断清单

### 系统环境检查
- [ ] Python版本 >= 3.9
- [ ] 必要的系统依赖已安装
- [ ] 目录权限正确
- [ ] 端口未被占用

### 应用状态检查
- [ ] 配置文件格式正确
- [ ] 数据库连接正常
- [ ] 日志文件可写入
- [ ] 前端资源可访问

### 性能状态检查
- [ ] 内存使用率 < 80%
- [ ] 磁盘空间充足
- [ ] 数据库查询响应 < 200ms
- [ ] API响应时间 < 1s

## 🆘 紧急恢复

### 数据恢复
```bash
# 恢复数据库备份
cp data/db_backup_*/finance_news.db data/db/

# 验证数据完整性
python -c "
from backend.newslook.utils.database import NewsDatabase
db = NewsDatabase()
print(f'恢复数据: {db.get_news_count()} 条新闻')
"
```

### 服务重启
```bash
# 强制重启服务
pkill -f "python.*app.py"
python app.py --port 5001
```

## 📞 技术支持

### 获取帮助
1. 查看系统日志：`tail -f logs/app.log`
2. 运行诊断脚本确认问题
3. 收集错误信息和环境信息
4. 提交Issue或联系技术支持

### 联系方式
- GitHub Issues: [项目仓库](https://github.com/yourusername/NewsLook/issues)
- 技术文档: 参考docs/目录下的其他文档

---

*最后更新: 2025-06-25* 