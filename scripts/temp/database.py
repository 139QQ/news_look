import sqlite3
import json
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def get_news_by_id(self, news_id):
        """根据ID获取新闻详情
        
        Args:
            news_id: 新闻ID
            
        Returns:
            dict: 新闻数据，如果未找到则返回None
        """
        try:
            # 确保 news_id 不为空
            if not news_id:
                logger.error("新闻ID为空，无法查询")
                return None
                
            # 记录查询信息
            logger.info(f"开始查询新闻ID: {news_id}")
            
            # 检查 self.all_db_paths 是否存在
            if not hasattr(self, 'all_db_paths') or not self.all_db_paths:
                # 如果不存在，使用数据目录中的所有 .db 文件
                data_dir = os.path.join(os.getcwd(), 'data', 'db')
                if os.path.exists(data_dir):
                    db_paths = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.db')]
                    logger.info(f"从数据目录获取到 {len(db_paths)} 个数据库文件")
                else:
                    logger.error(f"数据目录不存在: {data_dir}")
                    return None
            else:
                db_paths = self.all_db_paths
                logger.info(f"使用已配置的数据库路径列表，共 {len(db_paths)} 个")
            
            # 确保 db_paths 不为空
            if not db_paths:
                logger.error("没有找到任何数据库文件")
                return None
                
            logger.info(f"开始查询新闻ID: {news_id}，将在 {len(db_paths)} 个数据库中搜索")
            
            # 检查数据库文件是否存在
            valid_db_paths = []
            for db_path in db_paths:
                if os.path.exists(db_path):
                    valid_db_paths.append(db_path)
                else:
                    logger.warning(f"数据库文件不存在: {db_path}")
            
            if not valid_db_paths:
                logger.error(f"没有找到有效的数据库文件")
                return None
            
            logger.info(f"将在 {len(valid_db_paths)} 个有效数据库中搜索新闻ID: {news_id}")
            
            # 尝试从所有数据库查询
            for db_path in valid_db_paths:
                try:
                    # 尝试从数据库文件名中提取来源
                    db_source = os.path.basename(db_path).replace('.db', '')
                    logger.info(f"在数据库 {db_path} 中查询新闻ID: {news_id}")
                    
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # 判断news表是否存在
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
                    if not cursor.fetchone():
                        # 表不存在，跳过此数据库
                        logger.warning(f"数据库 {db_path} 中news表不存在，跳过")
                        conn.close()
                        continue
                    
                    # 获取表中记录数量
                    cursor.execute("SELECT COUNT(*) FROM news")
                    count = cursor.fetchone()[0]
                    logger.info(f"数据库 {db_path} 中有 {count} 条新闻记录")
                    
                    if count == 0:
                        logger.warning(f"数据库 {db_path} 中没有新闻记录，跳过")
                        conn.close()
                        continue
                    
                    # 查询指定ID的新闻 - 先获取所有列名
                    cursor.execute("PRAGMA table_info(news)")
                    columns = [col[1] for col in cursor.fetchall()]
                    logger.info(f"新闻表列结构: {columns}")
                    
                    # 查询指定ID的新闻 - 精确匹配
                    logger.info(f"精确查询新闻ID: {news_id}")
                    cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
                    row = cursor.fetchone()
                    
                    if not row:
                        # 尝试使用字符串格式
                        logger.info(f"尝试将ID作为字符串查询: {news_id}")
                        cursor.execute("SELECT * FROM news WHERE id = ?", (str(news_id),))
                        row = cursor.fetchone()
                    
                    if not row:
                        # 尝试使用LIKE查询，可能存在ID格式不一致的情况
                        logger.info(f"在数据库 {db_path} 中未找到精确匹配的新闻ID: {news_id}，尝试模糊匹配")
                        cursor.execute("SELECT * FROM news WHERE id LIKE ?", (f"%{news_id}%",))
                        row = cursor.fetchone()
                    
                    if row:
                        # 转换为字典
                        news = {}
                        for i, column in enumerate(cursor.description):
                            news[column[0]] = row[i]
                        
                        logger.info(f"找到新闻记录，标题: {news.get('title', '无标题')}")
                        
                        # 处理JSON字段
                        try:
                            if 'keywords' in news and news['keywords']:
                                if isinstance(news['keywords'], str):
                                    try:
                                        news['keywords'] = json.loads(news['keywords'])
                                    except json.JSONDecodeError:
                                        # 如果不是有效的JSON，尝试按逗号分割
                                        news['keywords'] = [k.strip() for k in news['keywords'].split(',') if k.strip()]
                                        
                            if 'images' in news and news['images']:
                                if isinstance(news['images'], str):
                                    try:
                                        news['images'] = json.loads(news['images'])
                                    except json.JSONDecodeError:
                                        # 如果不是有效的JSON，尝试按逗号分割
                                        news['images'] = [img.strip() for img in news['images'].split(',') if img.strip()]
                                        
                            if 'related_stocks' in news and news['related_stocks']:
                                if isinstance(news['related_stocks'], str):
                                    try:
                                        news['related_stocks'] = json.loads(news['related_stocks'])
                                    except json.JSONDecodeError:
                                        # 如果不是有效的JSON，尝试按逗号分割
                                        news['related_stocks'] = [s.strip() for s in news['related_stocks'].split(',') if s.strip()]
                        except Exception as e:
                            # 如果处理JSON时出错，记录错误但继续执行
                            logger.error(f"处理新闻JSON字段失败: {str(e)}")
                        
                        conn.close()
                        logger.info(f"在数据库 {db_path} 中找到新闻ID: {news_id}，标题: {news.get('title', '无标题')}")
                        return news  # 找到后立即返回
                    
                    conn.close()
                    logger.warning(f"在数据库 {db_path} 中未找到新闻ID: {news_id}")
                    
                except Exception as e:
                    logger.error(f"查询新闻详情失败: {str(e)}, 数据库: {db_path}")
            
            # 移除自动查找腾讯替代新闻的逻辑，避免点击腾讯新闻时跳转到东方财富等其他来源
            # 原有逻辑在找不到腾讯新闻时会返回任何含"腾讯"的新闻，造成链接混乱
            
            logger.warning(f"在所有数据库中未找到新闻ID: {news_id}")
            # 返回一个特殊标记对象，让routes.py可以识别这是"新闻不存在"的情况
            return {"title": "新闻不存在", "content": "该新闻不存在或已被删除"}
        except Exception as e:
            logger.error(f"获取新闻详情失败: {str(e)}")
            return {"title": "新闻获取失败", "content": f"获取新闻时发生错误: {str(e)}"} 