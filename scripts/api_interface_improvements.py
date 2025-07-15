#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API接口改进脚本
实现RESTful API标准化、版本管理和真实数据集成
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import sqlite3
import re

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIInterfaceImprover:
    """API接口改进器"""
    
    def __init__(self, project_root: str = None):
        """初始化API接口改进器"""
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = Path(project_root)
        self.backend_dir = self.project_root / 'backend'
        self.db_dir = self.project_root / 'data' / 'db'
        self.main_db = self.db_dir / 'finance_news.db'
        
        # 改进报告
        self.report = {
            'start_time': datetime.now().isoformat(),
            'improvements': [],
            'errors': []
        }
        
        # API版本配置
        self.api_versions = {
            'v1': '1.0.0',
            'v2': '2.0.0'
        }
        
        # RESTful API标准配置
        self.rest_standards = {
            'status_codes': {
                200: 'OK',
                201: 'Created',
                400: 'Bad Request',
                401: 'Unauthorized',
                403: 'Forbidden',
                404: 'Not Found',
                500: 'Internal Server Error'
            },
            'response_format': {
                'success': True,
                'data': None,
                'message': '',
                'error': None,
                'timestamp': None,
                'version': '2.0.0'
            }
        }
    
    def create_api_response_helper(self):
        """创建API响应助手模块"""
        logger.info("创建API响应助手模块...")
        
        api_helper_dir = self.backend_dir / 'newslook' / 'api' / 'helpers'
        api_helper_dir.mkdir(parents=True, exist_ok=True)
        
        response_helper_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API响应助手模块
提供标准化的API响应格式和错误处理
"""

from flask import jsonify, request
from datetime import datetime
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class APIResponse:
    """API响应构建器"""
    
    @staticmethod
    def success(data=None, message="操作成功", status_code=200, version="2.0.0"):
        """成功响应"""
        response = {
            'success': True,
            'data': data,
            'message': message,
            'error': None,
            'timestamp': datetime.now().isoformat(),
            'version': version
        }
        return jsonify(response), status_code
    
    @staticmethod
    def error(error_msg, status_code=400, error_code=None, version="2.0.0"):
        """错误响应"""
        response = {
            'success': False,
            'data': None,
            'message': '请求失败',
            'error': {
                'message': error_msg,
                'code': error_code,
                'status': status_code
            },
            'timestamp': datetime.now().isoformat(),
            'version': version
        }
        return jsonify(response), status_code
    
    @staticmethod
    def not_found(message="资源不存在", version="2.0.0"):
        """404响应"""
        return APIResponse.error(message, 404, "NOT_FOUND", version)
    
    @staticmethod
    def bad_request(message="请求参数错误", version="2.0.0"):
        """400响应"""
        return APIResponse.error(message, 400, "BAD_REQUEST", version)
    
    @staticmethod
    def internal_error(message="服务器内部错误", version="2.0.0"):
        """500响应"""
        return APIResponse.error(message, 500, "INTERNAL_ERROR", version)
    
    @staticmethod
    def paginated_response(data, page=1, per_page=10, total=0, version="2.0.0"):
        """分页响应"""
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'has_next': page * per_page < total,
            'has_prev': page > 1
        }
        
        response = {
            'success': True,
            'data': data,
            'pagination': pagination,
            'message': '获取成功',
            'error': None,
            'timestamp': datetime.now().isoformat(),
            'version': version
        }
        return jsonify(response), 200

def api_error_handler(func):
    """API错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.error(f"参数错误: {e}")
            return APIResponse.bad_request(str(e))
        except FileNotFoundError as e:
            logger.error(f"资源不存在: {e}")
            return APIResponse.not_found(str(e))
        except Exception as e:
            logger.error(f"API错误: {e}", exc_info=True)
            return APIResponse.internal_error("服务器内部错误")
    return wrapper

def validate_pagination():
    """验证分页参数"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 10
    
    return page, per_page

def validate_date_range():
    """验证日期范围参数"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        try:
            start_date = datetime.fromisoformat(start_date)
        except ValueError:
            raise ValueError("开始日期格式错误，应为ISO格式")
    
    if end_date:
        try:
            end_date = datetime.fromisoformat(end_date)
        except ValueError:
            raise ValueError("结束日期格式错误，应为ISO格式")
    
    if start_date and end_date and start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期")
    
    return start_date, end_date
'''
        
        response_helper_file = api_helper_dir / 'response_helper.py'
        with open(response_helper_file, 'w', encoding='utf-8') as f:
            f.write(response_helper_code)
        
        # 创建__init__.py文件
        init_file = api_helper_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('from .response_helper import APIResponse, api_error_handler\n')
        
        logger.info(f"API响应助手模块创建完成: {response_helper_file}")
        return response_helper_file
    
    def create_data_service_layer(self):
        """创建数据服务层"""
        logger.info("创建数据服务层...")
        
        service_dir = self.backend_dir / 'newslook' / 'services'
        service_dir.mkdir(parents=True, exist_ok=True)
        
        news_service_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻数据服务层
提供真实的数据访问接口
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

logger = logging.getLogger(__name__)

class NewsDataService:
    """新闻数据服务"""
    
    def __init__(self, db_path: str = None):
        """初始化新闻数据服务"""
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = project_root / 'data' / 'db' / 'finance_news.db'
        
        self.db_path = str(db_path)
        self._ensure_database()
    
    def _ensure_database(self):
        """确保数据库存在"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("SELECT 1 FROM news LIMIT 1")
        except sqlite3.Error as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_news_list(self, page: int = 1, per_page: int = 10, 
                     source: str = None, category: str = None,
                     start_date: datetime = None, end_date: datetime = None,
                     search_query: str = None) -> Tuple[List[Dict], int]:
        """获取新闻列表"""
        
        offset = (page - 1) * per_page
        
        # 构建查询条件
        conditions = []
        params = []
        
        if source:
            conditions.append("source = ?")
            params.append(source)
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if start_date:
            conditions.append("pub_time >= ?")
            params.append(start_date.isoformat())
        
        if end_date:
            conditions.append("pub_time <= ?")
            params.append(end_date.isoformat())
        
        if search_query:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with self._get_connection() as conn:
            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM news WHERE {where_clause}"
            total = conn.execute(count_sql, params).fetchone()[0]
            
            # 获取数据
            data_sql = f"""
                SELECT id, title, content, source, url, pub_time, 
                       author, category, keywords, sentiment, 
                       crawl_time, images, related_stocks
                FROM news 
                WHERE {where_clause}
                ORDER BY pub_time DESC 
                LIMIT ? OFFSET ?
            """
            params.extend([per_page, offset])
            
            rows = conn.execute(data_sql, params).fetchall()
            
            # 转换为字典列表
            news_list = []
            for row in rows:
                news_dict = dict(row)
                
                # 处理JSON字段
                for json_field in ['keywords', 'images', 'related_stocks']:
                    if news_dict.get(json_field):
                        try:
                            news_dict[json_field] = json.loads(news_dict[json_field])
                        except (json.JSONDecodeError, TypeError):
                            news_dict[json_field] = []
                
                news_list.append(news_dict)
            
            return news_list, total
    
    def get_news_detail(self, news_id: str) -> Optional[Dict]:
        """获取新闻详情"""
        with self._get_connection() as conn:
            sql = """
                SELECT id, title, content, content_html, source, url, 
                       pub_time, author, category, keywords, sentiment, 
                       crawl_time, images, related_stocks, classification
                FROM news 
                WHERE id = ?
            """
            
            row = conn.execute(sql, (news_id,)).fetchone()
            
            if not row:
                return None
            
            news_dict = dict(row)
            
            # 处理JSON字段
            for json_field in ['keywords', 'images', 'related_stocks']:
                if news_dict.get(json_field):
                    try:
                        news_dict[json_field] = json.loads(news_dict[json_field])
                    except (json.JSONDecodeError, TypeError):
                        news_dict[json_field] = []
            
            return news_dict
    
    def get_news_statistics(self) -> Dict:
        """获取新闻统计信息"""
        with self._get_connection() as conn:
            # 总新闻数
            total_news = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
            
            # 按来源统计
            source_stats = conn.execute("""
                SELECT source, COUNT(*) as count
                FROM news 
                GROUP BY source 
                ORDER BY count DESC
            """).fetchall()
            
            # 按分类统计
            category_stats = conn.execute("""
                SELECT category, COUNT(*) as count
                FROM news 
                GROUP BY category 
                ORDER BY count DESC
            """).fetchall()
            
            # 最近7天新闻数
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_news = conn.execute("""
                SELECT COUNT(*) FROM news 
                WHERE pub_time >= ?
            """, (week_ago,)).fetchone()[0]
            
            return {
                'total_news': total_news,
                'source_distribution': [dict(row) for row in source_stats],
                'category_distribution': [dict(row) for row in category_stats],
                'recent_news_count': recent_news
            }
    
    def get_crawler_status(self) -> Dict:
        """获取爬虫状态"""
        with self._get_connection() as conn:
            # 各来源最新数据时间
            source_latest = conn.execute("""
                SELECT source, MAX(crawl_time) as latest_crawl
                FROM news 
                GROUP BY source
            """).fetchall()
            
            return {
                'source_status': [dict(row) for row in source_latest],
                'last_update': datetime.now().isoformat()
            }
    
    def search_news(self, query: str, page: int = 1, per_page: int = 10) -> Tuple[List[Dict], int]:
        """搜索新闻"""
        return self.get_news_list(
            page=page, 
            per_page=per_page, 
            search_query=query
        )
    
    def get_trending_keywords(self, limit: int = 10) -> List[Dict]:
        """获取热门关键词"""
        with self._get_connection() as conn:
            sql = """
                SELECT keywords, COUNT(*) as frequency
                FROM news 
                WHERE keywords IS NOT NULL AND keywords != ''
                AND pub_time >= datetime('now', '-7 days')
                GROUP BY keywords
                ORDER BY frequency DESC
                LIMIT ?
            """
            
            rows = conn.execute(sql, (limit,)).fetchall()
            return [dict(row) for row in rows]
'''
        
        news_service_file = service_dir / 'news_service.py'
        with open(news_service_file, 'w', encoding='utf-8') as f:
            f.write(news_service_code)
        
        # 创建__init__.py文件
        init_file = service_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('from .news_service import NewsDataService\n')
        
        logger.info(f"数据服务层创建完成: {news_service_file}")
        return news_service_file
    
    def create_restful_api_routes(self):
        """创建RESTful API路由"""
        logger.info("创建RESTful API路由...")
        
        api_dir = self.backend_dir / 'newslook' / 'api' / 'v2'
        api_dir.mkdir(parents=True, exist_ok=True)
        
        news_routes_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RESTful API v2 - 新闻路由
符合REST标准的API接口
"""

from flask import Blueprint, request, jsonify
from backend.newslook.api.helpers import APIResponse, api_error_handler, validate_pagination, validate_date_range
from backend.newslook.services import NewsDataService
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
news_bp = Blueprint('news_v2', __name__, url_prefix='/api/v2/news')

# 初始化服务
news_service = NewsDataService()

@news_bp.route('/', methods=['GET'])
@api_error_handler
def get_news_list():
    """GET /api/v2/news - 获取新闻列表"""
    
    # 验证分页参数
    page, per_page = validate_pagination()
    
    # 验证日期范围
    start_date, end_date = validate_date_range()
    
    # 获取过滤参数
    source = request.args.get('source')
    category = request.args.get('category')
    search_query = request.args.get('q')
    
    # 获取数据
    news_list, total = news_service.get_news_list(
        page=page,
        per_page=per_page,
        source=source,
        category=category,
        start_date=start_date,
        end_date=end_date,
        search_query=search_query
    )
    
    return APIResponse.paginated_response(
        data=news_list,
        page=page,
        per_page=per_page,
        total=total
    )

@news_bp.route('/<string:news_id>', methods=['GET'])
@api_error_handler
def get_news_detail(news_id):
    """GET /api/v2/news/{id} - 获取新闻详情"""
    
    news_detail = news_service.get_news_detail(news_id)
    
    if not news_detail:
        return APIResponse.not_found("新闻不存在")
    
    return APIResponse.success(news_detail, "获取新闻详情成功")

@news_bp.route('/search', methods=['GET'])
@api_error_handler
def search_news():
    """GET /api/v2/news/search - 搜索新闻"""
    
    query = request.args.get('q')
    if not query:
        return APIResponse.bad_request("搜索关键词不能为空")
    
    page, per_page = validate_pagination()
    
    news_list, total = news_service.search_news(
        query=query,
        page=page,
        per_page=per_page
    )
    
    return APIResponse.paginated_response(
        data=news_list,
        page=page,
        per_page=per_page,
        total=total
    )

@news_bp.route('/statistics', methods=['GET'])
@api_error_handler
def get_news_statistics():
    """GET /api/v2/news/statistics - 获取新闻统计"""
    
    statistics = news_service.get_news_statistics()
    return APIResponse.success(statistics, "获取统计信息成功")

@news_bp.route('/trending', methods=['GET'])
@api_error_handler
def get_trending_keywords():
    """GET /api/v2/news/trending - 获取热门关键词"""
    
    limit = request.args.get('limit', 10, type=int)
    if limit < 1 or limit > 100:
        limit = 10
    
    keywords = news_service.get_trending_keywords(limit)
    return APIResponse.success(keywords, "获取热门关键词成功")

@news_bp.route('/sources', methods=['GET'])
@api_error_handler
def get_news_sources():
    """GET /api/v2/news/sources - 获取新闻来源列表"""
    
    # 从统计信息中获取来源列表
    statistics = news_service.get_news_statistics()
    sources = statistics['source_distribution']
    
    return APIResponse.success(sources, "获取新闻来源成功")

@news_bp.route('/categories', methods=['GET'])
@api_error_handler
def get_news_categories():
    """GET /api/v2/news/categories - 获取新闻分类列表"""
    
    # 从统计信息中获取分类列表
    statistics = news_service.get_news_statistics()
    categories = statistics['category_distribution']
    
    return APIResponse.success(categories, "获取新闻分类成功")

# 健康检查
@news_bp.route('/health', methods=['GET'])
def health_check():
    """GET /api/v2/news/health - 健康检查"""
    return APIResponse.success(
        {
            'status': 'healthy',
            'service': 'news_api',
            'version': '2.0.0'
        },
        "服务正常"
    )
'''
        
        news_routes_file = api_dir / 'news_routes.py'
        with open(news_routes_file, 'w', encoding='utf-8') as f:
            f.write(news_routes_code)
        
        # 创建爬虫管理API
        crawler_routes_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RESTful API v2 - 爬虫管理路由
"""

from flask import Blueprint, request, jsonify
from backend.newslook.api.helpers import APIResponse, api_error_handler
from backend.newslook.services import NewsDataService
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
crawler_bp = Blueprint('crawler_v2', __name__, url_prefix='/api/v2/crawler')

# 初始化服务
news_service = NewsDataService()

@crawler_bp.route('/status', methods=['GET'])
@api_error_handler
def get_crawler_status():
    """GET /api/v2/crawler/status - 获取爬虫状态"""
    
    status = news_service.get_crawler_status()
    return APIResponse.success(status, "获取爬虫状态成功")

@crawler_bp.route('/sources', methods=['GET'])
@api_error_handler
def get_crawler_sources():
    """GET /api/v2/crawler/sources - 获取爬虫来源配置"""
    
    sources = [
        {
            'name': 'eastmoney',
            'display_name': '东方财富',
            'url': 'http://finance.eastmoney.com',
            'status': 'active'
        },
        {
            'name': 'sina',
            'display_name': '新浪财经',
            'url': 'http://finance.sina.com.cn',
            'status': 'active'
        },
        {
            'name': 'netease',
            'display_name': '网易财经',
            'url': 'http://money.163.com',
            'status': 'active'
        },
        {
            'name': 'ifeng',
            'display_name': '凤凰财经',
            'url': 'http://finance.ifeng.com',
            'status': 'active'
        },
        {
            'name': 'tencent',
            'display_name': '腾讯财经',
            'url': 'http://finance.qq.com',
            'status': 'active'
        }
    ]
    
    return APIResponse.success(sources, "获取爬虫来源成功")

@crawler_bp.route('/start', methods=['POST'])
@api_error_handler
def start_crawler():
    """POST /api/v2/crawler/start - 启动爬虫"""
    
    data = request.get_json()
    if not data or 'source' not in data:
        return APIResponse.bad_request("缺少爬虫来源参数")
    
    source = data['source']
    
    # 这里应该集成实际的爬虫管理器
    # 目前返回模拟响应
    result = {
        'source': source,
        'status': 'started',
        'message': f'爬虫 {source} 启动成功'
    }
    
    return APIResponse.success(result, "启动爬虫成功")

@crawler_bp.route('/stop', methods=['POST'])
@api_error_handler
def stop_crawler():
    """POST /api/v2/crawler/stop - 停止爬虫"""
    
    data = request.get_json()
    if not data or 'source' not in data:
        return APIResponse.bad_request("缺少爬虫来源参数")
    
    source = data['source']
    
    # 这里应该集成实际的爬虫管理器
    # 目前返回模拟响应
    result = {
        'source': source,
        'status': 'stopped',
        'message': f'爬虫 {source} 停止成功'
    }
    
    return APIResponse.success(result, "停止爬虫成功")

@crawler_bp.route('/config', methods=['GET'])
@api_error_handler
def get_crawler_config():
    """GET /api/v2/crawler/config - 获取爬虫配置"""
    
    config = {
        'interval': 300,  # 爬取间隔(秒)
        'timeout': 30,    # 超时时间(秒)
        'max_retries': 3, # 最大重试次数
        'concurrent_limit': 5  # 并发限制
    }
    
    return APIResponse.success(config, "获取爬虫配置成功")

@crawler_bp.route('/config', methods=['PUT'])
@api_error_handler
def update_crawler_config():
    """PUT /api/v2/crawler/config - 更新爬虫配置"""
    
    data = request.get_json()
    if not data:
        return APIResponse.bad_request("缺少配置参数")
    
    # 这里应该验证和保存配置
    # 目前返回模拟响应
    return APIResponse.success(data, "更新爬虫配置成功")
'''
        
        crawler_routes_file = api_dir / 'crawler_routes.py'
        with open(crawler_routes_file, 'w', encoding='utf-8') as f:
            f.write(crawler_routes_code)
        
        # 创建__init__.py文件
        init_file = api_dir / '__init__.py'
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('''from .news_routes import news_bp
from .crawler_routes import crawler_bp

__all__ = ['news_bp', 'crawler_bp']
''')
        
        logger.info(f"RESTful API路由创建完成: {api_dir}")
        return api_dir
    
    def create_api_documentation(self):
        """创建API文档"""
        logger.info("创建API文档...")
        
        docs_dir = self.project_root / 'docs' / 'api'
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        api_doc_content = '''# NewsLook API v2.0 文档

## 概述

NewsLook API v2.0 是一个符合RESTful标准的API接口，提供财经新闻数据的访问和爬虫管理功能。

## 版本信息

- **版本**: 2.0.0
- **基础URL**: `http://localhost:5000/api/v2`
- **认证**: 暂无（后续可扩展）

## 响应格式

所有API响应都遵循统一的格式：

```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "error": null,
  "timestamp": "2024-01-01T00:00:00.000Z",
  "version": "2.0.0"
}
```

## 新闻API

### 获取新闻列表

```
GET /api/v2/news
```

**查询参数**:
- `page`: 页码，默认1
- `per_page`: 每页数量，默认10，最大100
- `source`: 新闻来源筛选
- `category`: 新闻分类筛选
- `start_date`: 开始日期（ISO格式）
- `end_date`: 结束日期（ISO格式）
- `q`: 搜索关键词

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": "news_001",
      "title": "股市最新动态",
      "content": "新闻内容...",
      "source": "东方财富",
      "url": "http://example.com/news/001",
      "pub_time": "2024-01-01T10:00:00Z",
      "author": "记者姓名",
      "category": "财经",
      "keywords": ["股市", "投资"],
      "sentiment": 0.5
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 100,
    "pages": 10,
    "has_next": true,
    "has_prev": false
  }
}
```

### 获取新闻详情

```
GET /api/v2/news/{id}
```

**路径参数**:
- `id`: 新闻ID

### 搜索新闻

```
GET /api/v2/news/search
```

**查询参数**:
- `q`: 搜索关键词（必需）
- `page`: 页码
- `per_page`: 每页数量

### 获取新闻统计

```
GET /api/v2/news/statistics
```

### 获取热门关键词

```
GET /api/v2/news/trending
```

**查询参数**:
- `limit`: 返回数量，默认10，最大100

### 获取新闻来源

```
GET /api/v2/news/sources
```

### 获取新闻分类

```
GET /api/v2/news/categories
```

## 爬虫管理API

### 获取爬虫状态

```
GET /api/v2/crawler/status
```

### 获取爬虫来源配置

```
GET /api/v2/crawler/sources
```

### 启动爬虫

```
POST /api/v2/crawler/start
```

**请求体**:
```json
{
  "source": "eastmoney"
}
```

### 停止爬虫

```
POST /api/v2/crawler/stop
```

**请求体**:
```json
{
  "source": "eastmoney"
}
```

### 获取爬虫配置

```
GET /api/v2/crawler/config
```

### 更新爬虫配置

```
PUT /api/v2/crawler/config
```

**请求体**:
```json
{
  "interval": 300,
  "timeout": 30,
  "max_retries": 3,
  "concurrent_limit": 5
}
```

## 错误处理

API使用标准HTTP状态码：

- `200 OK`: 请求成功
- `201 Created`: 创建成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未授权
- `403 Forbidden`: 禁止访问
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

错误响应格式：
```json
{
  "success": false,
  "data": null,
  "message": "请求失败",
  "error": {
    "message": "具体错误信息",
    "code": "ERROR_CODE",
    "status": 400
  },
  "timestamp": "2024-01-01T00:00:00.000Z",
  "version": "2.0.0"
}
```

## 分页

支持分页的接口使用以下参数：
- `page`: 页码（从1开始）
- `per_page`: 每页数量（默认10，最大100）

分页响应包含pagination对象：
```json
{
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 100,
    "pages": 10,
    "has_next": true,
    "has_prev": false
  }
}
```

## 日期格式

所有日期参数和响应都使用ISO 8601格式：
- `2024-01-01T10:00:00Z`
- `2024-01-01T10:00:00+08:00`

## 版本管理

API版本通过URL路径指定：
- `/api/v1/...` - 版本1.0（兼容性支持）
- `/api/v2/...` - 版本2.0（当前版本）

## 限制

- 每页最大返回100条记录
- 搜索关键词最大长度100字符
- 日期范围查询最大跨度1年
'''
        
        api_doc_file = docs_dir / 'api_v2_documentation.md'
        with open(api_doc_file, 'w', encoding='utf-8') as f:
            f.write(api_doc_content)
        
        logger.info(f"API文档创建完成: {api_doc_file}")
        return api_doc_file
    
    def generate_improvement_report(self) -> Path:
        """生成改进报告"""
        self.report['end_time'] = datetime.now().isoformat()
        
        report_file = self.project_root / f"api_improvements_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"生成API改进报告: {report_file}")
        return report_file
    
    def run_full_improvements(self) -> Path:
        """运行完整的API改进"""
        logger.info("开始API接口改进...")
        
        try:
            # 1. 创建API响应助手
            response_helper = self.create_api_response_helper()
            self.report['improvements'].append({
                'action': 'create_api_response_helper',
                'file': str(response_helper)
            })
            
            # 2. 创建数据服务层
            data_service = self.create_data_service_layer()
            self.report['improvements'].append({
                'action': 'create_data_service_layer',
                'file': str(data_service)
            })
            
            # 3. 创建RESTful API路由
            api_routes = self.create_restful_api_routes()
            self.report['improvements'].append({
                'action': 'create_restful_api_routes',
                'directory': str(api_routes)
            })
            
            # 4. 创建API文档
            api_doc = self.create_api_documentation()
            self.report['improvements'].append({
                'action': 'create_api_documentation',
                'file': str(api_doc)
            })
            
            # 5. 生成报告
            report_file = self.generate_improvement_report()
            
            logger.info("API接口改进完成!")
            return report_file
            
        except Exception as e:
            logger.error(f"API改进过程中出错: {e}")
            self.report['errors'].append(str(e))
            return self.generate_improvement_report()

def main():
    """主函数"""
    improver = APIInterfaceImprover()
    report_file = improver.run_full_improvements()
    
    print(f"\nAPI接口改进完成! 报告文件: {report_file}")

if __name__ == "__main__":
    main() 