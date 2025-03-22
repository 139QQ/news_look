import sqlite3
import os
import logging
from datetime import datetime, timedelta
import tempfile
import shutil

class NewsDatabase:
    """新闻数据库操作类 - 优化版，支持按网站分类存储数据"""
    
    def __init__(self, db_path=None, source=None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            source: 新闻来源，如果提供则使用对应来源的专用数据库
        """
        # 获取项目根目录
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 创建专门的数据库目录
        self.db_dir = os.path.join(self.base_dir, 'db')
        os.makedirs(self.db_dir, exist_ok=True)
        
        if db_path:
            # 使用指定的数据库路径
            self.db_path = db_path
        elif source:
            # 使用来源专用数据库
            source_db_name = f"{source.lower().replace(' ', '_')}_news.db"
            self.db_path = os.path.join(self.db_dir, source_db_name)
            logging.info(f"使用来源专用数据库: {self.db_path}")
        else:
            # 使用主数据库
            self.db_path = os.path.join(self.db_dir, 'finance_news.db')
            logging.info(f"使用主数据库: {self.db_path}")
        
        # 记录数据库来源
        self.source = source
        
        # 初始化数据库
        self.init_database()
        
    def init_database(self):
        """初始化数据库表结构"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # 尝试连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建新闻表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                pub_time TEXT,
                author TEXT,
                source TEXT,
                url TEXT,
                keywords TEXT,
                sentiment REAL,
                crawl_time TEXT,
                category TEXT,
                images TEXT,
                related_stocks TEXT
            )
            ''')
            
            # 创建反馈表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                feedback_type TEXT,
                title TEXT,
                content TEXT,
                email TEXT,
                urgent INTEGER,
                status TEXT DEFAULT 'pending',
                submit_time TEXT,
                update_time TEXT,
                response TEXT
            )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON news (source)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pub_time ON news (pub_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sentiment ON news (sentiment)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON news (category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback (feedback_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback (status)')
            
            conn.commit()
            conn.close()
            logging.info(f"数据库初始化完成: {self.db_path}")
        except Exception as e:
            logging.error(f"数据库初始化失败: {str(e)}")
            # 打印更多调试信息
            logging.error(f"数据库路径: {self.db_path}")
            logging.error(f"目录是否存在: {os.path.exists(os.path.dirname(self.db_path))}")
            logging.error(f"当前工作目录: {os.getcwd()}")
        
    def save_news(self, news_item):
        """保存新闻到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute("SELECT id FROM news WHERE id = ?", (news_item['id'],))
            if cursor.fetchone():
                logging.info(f"新闻已存在: {news_item['title']}")
                conn.close()
                return False
            
            # 准备数据字段
            fields = [
                'id', 'title', 'content', 'pub_time', 'author', 'source', 
                'url', 'keywords', 'sentiment', 'crawl_time'
            ]
            
            # 添加可选字段
            optional_fields = ['category', 'images', 'related_stocks']
            for field in optional_fields:
                if field in news_item:
                    fields.append(field)
            
            # 构建SQL语句
            placeholders = ', '.join(['?'] * len(fields))
            fields_str = ', '.join(fields)
            
            # 准备值
            values = []
            for field in fields:
                if field in news_item:
                    # 处理特殊类型
                    if field in ['images', 'related_stocks'] and isinstance(news_item[field], (list, dict)):
                        import json
                        values.append(json.dumps(news_item[field], ensure_ascii=False))
                    else:
                        values.append(news_item[field])
                else:
                    values.append(None)
            
            # 执行插入
            sql = f"INSERT INTO news ({fields_str}) VALUES ({placeholders})"
            cursor.execute(sql, values)
            
            conn.commit()
            conn.close()
            
            # 同步到主数据库（如果当前不是主数据库）
            if self.source and self.db_path != os.path.join(self.db_dir, 'finance_news.db'):
                self.sync_to_main_db(news_item)
                
            return True
        except Exception as e:
            logging.error(f"保存新闻到数据库失败: {str(e)}")
            return False
    
    def sync_to_main_db(self, news_item):
        """同步新闻到主数据库"""
        try:
            main_db_path = os.path.join(self.db_dir, 'finance_news.db')
            main_db = NewsDatabase(main_db_path)
            main_db.save_news(news_item)
            logging.info(f"新闻已同步到主数据库: {news_item['title']}")
        except Exception as e:
            logging.error(f"同步新闻到主数据库失败: {str(e)}")
    
    def query_news(self, keyword=None, days=None, source=None, category=None, limit=None, offset=0):
        """查询新闻数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if keyword:
                conditions.append("(title LIKE ? OR content LIKE ? OR keywords LIKE ?)")
                params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
                
            if days:
                # 计算日期范围
                from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                conditions.append("pub_time >= ?")
                params.append(from_date)
                
            if source:
                conditions.append("source = ?")
                params.append(source)
            
            if category:
                conditions.append("category = ?")
                params.append(category)
                
            # 构建SQL语句
            sql = "SELECT * FROM news"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
                
            # 添加排序
            sql += " ORDER BY pub_time DESC"
            
            # 添加分页
            if limit:
                sql += f" LIMIT {limit}"
                if offset:
                    sql += f" OFFSET {offset}"
                    
            # 执行查询
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            news_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # 处理JSON字段
            for item in news_data:
                for field in ['images', 'related_stocks']:
                    if field in item and item[field]:
                        try:
                            import json
                            item[field] = json.loads(item[field])
                        except:
                            pass
            
            conn.close()
            return news_data
            
        except Exception as e:
            logging.error(f"查询新闻数据失败: {str(e)}")
            return [] 

    def count_news(self, keyword=None, days=None, source=None):
        """统计新闻数量"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if keyword:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if days:
            from datetime import datetime, timedelta
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            conditions.append("pub_time >= ?")
            params.append(start_date)
        
        if source:
            conditions.append("source = ?")
            params.append(source)
        
        # 构建SQL查询
        sql = "SELECT COUNT(*) FROM news"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        # 执行查询
        cursor.execute(sql, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_sources(self):
        """获取所有新闻来源"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT source FROM news")
        sources = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sources

    def get_news_by_id(self, news_id):
        """根据ID获取新闻"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询指定ID的新闻
            cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # 转换为字典
            columns = [col[0] for col in cursor.description]
            news = dict(zip(columns, row))
            
            conn.close()
            return news
            
        except Exception as e:
            logging.error(f"获取新闻详情失败: {str(e)}")
            return None 

    def count_news_by_date(self, date):
        """统计指定日期的新闻数量"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM news WHERE pub_time = ?", (date,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def count_news_by_sentiment(self, min_value, max_value):
        """统计指定情感值范围的新闻数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询指定情感值范围的新闻数量
            cursor.execute("SELECT COUNT(*) FROM news WHERE sentiment >= ? AND sentiment <= ?", 
                          (min_value, max_value))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
            
        except Exception as e:
            logging.error(f"统计情感新闻数量失败: {str(e)}")
            return 0 

    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except Exception as e:
            logging.error(f"获取数据库连接失败: {str(e)}")
            raise e 

    def save_feedback(self, feedback_data):
        """保存用户反馈到数据库
        
        Args:
            feedback_data (dict): 包含反馈信息的字典
                {
                    'id': 跟踪ID,
                    'feedback_type': 反馈类型,
                    'title': 标题,
                    'content': 内容,
                    'email': 电子邮箱,
                    'urgent': 是否紧急,
                    'submit_time': 提交时间
                }
        
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 准备数据
            feedback_id = feedback_data.get('id')
            feedback_type = feedback_data.get('feedback_type')
            title = feedback_data.get('title')
            content = feedback_data.get('content')
            email = feedback_data.get('email', '')
            urgent = 1 if feedback_data.get('urgent') else 0
            submit_time = feedback_data.get('submit_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # 插入数据
            cursor.execute('''
            INSERT INTO feedback (id, feedback_type, title, content, email, urgent, status, submit_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (feedback_id, feedback_type, title, content, email, urgent, 'pending', submit_time, submit_time))
            
            conn.commit()
            conn.close()
            logging.info(f"反馈保存成功: {feedback_id}")
            return True
        except Exception as e:
            logging.error(f"反馈保存失败: {e}")
            return False
    
    def get_feedback(self, feedback_id):
        """根据ID获取反馈信息
        
        Args:
            feedback_id (str): 反馈ID
        
        Returns:
            dict: 反馈信息字典，未找到返回None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, feedback_type, title, content, email, urgent, status, submit_time, update_time, response
            FROM feedback
            WHERE id = ?
            ''', (feedback_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'feedback_type': row[1],
                    'title': row[2],
                    'content': row[3],
                    'email': row[4],
                    'urgent': bool(row[5]),
                    'status': row[6],
                    'submit_time': row[7],
                    'update_time': row[8],
                    'response': row[9]
                }
            return None
        except Exception as e:
            logging.error(f"获取反馈失败: {e}")
            return None
    
    def query_feedback(self, feedback_type=None, status=None, urgent=None, limit=None, offset=0):
        """查询反馈列表
        
        Args:
            feedback_type (str, optional): 反馈类型
            status (str, optional): 反馈状态
            urgent (bool, optional): 是否紧急
            limit (int, optional): 限制返回数量
            offset (int, optional): 偏移量
        
        Returns:
            list: 反馈列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT id, feedback_type, title, content, email, urgent, status, submit_time, update_time, response FROM feedback WHERE 1=1"
            params = []
            
            if feedback_type:
                query += " AND feedback_type = ?"
                params.append(feedback_type)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if urgent is not None:
                query += " AND urgent = ?"
                params.append(1 if urgent else 0)
            
            query += " ORDER BY submit_time DESC"
            
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'feedback_type': row[1],
                    'title': row[2],
                    'content': row[3],
                    'email': row[4],
                    'urgent': bool(row[5]),
                    'status': row[6],
                    'submit_time': row[7],
                    'update_time': row[8],
                    'response': row[9]
                })
            
            return result
        except Exception as e:
            logging.error(f"查询反馈失败: {e}")
            return []
    
    def update_feedback_status(self, feedback_id, status, response=None):
        """更新反馈状态
        
        Args:
            feedback_id (str): 反馈ID
            status (str): 新状态
            response (str, optional): 回复内容
        
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if response:
                cursor.execute('''
                UPDATE feedback
                SET status = ?, update_time = ?, response = ?
                WHERE id = ?
                ''', (status, update_time, response, feedback_id))
            else:
                cursor.execute('''
                UPDATE feedback
                SET status = ?, update_time = ?
                WHERE id = ?
                ''', (status, update_time, feedback_id))
            
            conn.commit()
            conn.close()
            logging.info(f"反馈状态更新成功: {feedback_id} -> {status}")
            return True
        except Exception as e:
            logging.error(f"反馈状态更新失败: {e}")
            return False
    
    def count_feedback(self, feedback_type=None, status=None, urgent=None):
        """统计反馈数量
        
        Args:
            feedback_type (str, optional): 反馈类型
            status (str, optional): 反馈状态
            urgent (bool, optional): 是否紧急
        
        Returns:
            int: 反馈数量
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM feedback WHERE 1=1"
            params = []
            
            if feedback_type:
                query += " AND feedback_type = ?"
                params.append(feedback_type)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if urgent is not None:
                query += " AND urgent = ?"
                params.append(1 if urgent else 0)
            
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
        except Exception as e:
            logging.error(f"统计反馈失败: {e}")
            return 0 

    def merge_databases(self):
        """合并所有来源数据库到主数据库"""
        try:
            # 获取所有数据库文件
            db_files = [f for f in os.listdir(self.db_dir) if f.endswith('_news.db') and f != 'finance_news.db']
            
            if not db_files:
                logging.info("没有找到需要合并的数据库文件")
                return True
            
            # 主数据库路径
            main_db_path = os.path.join(self.db_dir, 'finance_news.db')
            
            # 连接主数据库
            main_conn = sqlite3.connect(main_db_path)
            main_cursor = main_conn.cursor()
            
            # 获取主数据库中的所有新闻ID
            main_cursor.execute("SELECT id FROM news")
            existing_ids = {row[0] for row in main_cursor.fetchall()}
            
            merged_count = 0
            
            # 遍历每个来源数据库
            for db_file in db_files:
                source_db_path = os.path.join(self.db_dir, db_file)
                source_conn = sqlite3.connect(source_db_path)
                source_cursor = source_conn.cursor()
                
                # 获取来源数据库中的所有新闻
                source_cursor.execute("SELECT * FROM news")
                columns = [col[0] for col in source_cursor.description]
                news_items = [dict(zip(columns, row)) for row in source_cursor.fetchall()]
                
                # 将新闻插入主数据库
                for news_item in news_items:
                    if news_item['id'] not in existing_ids:
                        # 构建插入语句
                        fields = list(news_item.keys())
                        placeholders = ', '.join(['?'] * len(fields))
                        fields_str = ', '.join(fields)
                        values = list(news_item.values())
                        
                        sql = f"INSERT INTO news ({fields_str}) VALUES ({placeholders})"
                        main_cursor.execute(sql, values)
                        
                        existing_ids.add(news_item['id'])
                        merged_count += 1
                
                source_conn.close()
            
            main_conn.commit()
            main_conn.close()
            
            logging.info(f"数据库合并完成，共合并 {merged_count} 条新闻")
            return True
            
        except Exception as e:
            logging.error(f"合并数据库失败: {str(e)}")
            return False
    
    def backup_database(self, backup_dir=None):
        """备份数据库
        
        Args:
            backup_dir: 备份目录，默认为项目根目录下的backup文件夹
        
        Returns:
            str: 备份文件路径，失败返回None
        """
        try:
            if not backup_dir:
                backup_dir = os.path.join(self.base_dir, 'backup')
            
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            db_name = os.path.basename(self.db_path)
            backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.bak")
            
            # 复制数据库文件
            shutil.copy2(self.db_path, backup_file)
            
            logging.info(f"数据库备份成功: {backup_file}")
            return backup_file
            
        except Exception as e:
            logging.error(f"数据库备份失败: {str(e)}")
            return None 