import jieba
import jieba.analyse
import re

class SentimentAnalyzer:
    """情感分析工具类"""
    
    def __init__(self):
        """初始化情感词典"""
        # 简单的情感词典
        self.positive_words = [
            '上涨', '利好', '增长', '盈利', '看好', '机会', '突破', '反弹',
            '强势', '利润', '增加', '提高', '优质', '成功', '稳定', '回升',
            '向好', '积极', '改善', '扩大', '领先', '创新', '突破', '优势'
        ]
        
        self.negative_words = [
            '下跌', '利空', '下滑', '亏损', '风险', '跌破', '低迷', '下挫',
            '弱势', '亏损', '减少', '下降', '失败', '不稳', '担忧', '萎缩',
            '恶化', '危机', '困难', '问题', '挑战', '压力', '下行', '衰退'
        ]
        
    def extract_keywords(self, text, top_n=5):
        """提取文本关键词"""
        if not text:
            return ""
            
        # 清理文本
        text = self._clean_text(text)
        
        # 使用jieba提取关键词
        keywords = jieba.analyse.extract_tags(text, topK=top_n)
        return ','.join(keywords)
        
    def analyze(self, text):
        """分析文本情感，返回-1到1之间的值，负值表示负面，正值表示正面"""
        if not text:
            return 0
            
        # 清理文本
        text = self._clean_text(text)
        
        # 分词
        words = jieba.lcut(text)
        
        # 计算情感得分
        pos_count = sum(1 for word in words if word in self.positive_words)
        neg_count = sum(1 for word in words if word in self.negative_words)
        
        # 计算情感值
        total = pos_count + neg_count
        if total == 0:
            return 0
            
        return (pos_count - neg_count) / total
        
    def _clean_text(self, text):
        """清理文本"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除URL
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # 移除特殊字符
        text = re.sub(r'[^\w\s]', '', text)
        
        return text 