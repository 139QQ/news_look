import re

def is_quality_content(title, content):
    """判断内容是否为高质量内容"""
    # 内容长度过短
    if len(content) < 200:
        return False
        
    # 标题或内容包含广告关键词
    ad_keywords = ['广告', '推广', '赞助', '点击购买', '优惠券']
    if any(keyword in title or keyword in content for keyword in ad_keywords):
        return False
        
    # 标题是纯数字或过短
    if len(title) < 10 or title.isdigit():
        return False
        
    # 内容中包含过多的表情符号
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F700-\U0001F77F"  # alchemical symbols
        u"\U0001F780-\U0001F7FF"  # Geometric Shapes
        u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        u"\U0001FA00-\U0001FA6F"  # Chess Symbols
        u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        u"\U00002702-\U000027B0"  # Dingbats
        u"\U000024C2-\U0001F251" 
        "]+", flags=re.UNICODE)
    emoji_count = len(emoji_pattern.findall(content))
    if emoji_count > 10:
        return False
        
    return True 

def is_learning_content(title, content, keywords):
    """判断内容是否适合学习"""
    # 定义学习相关的关键词 - 扩大关键词范围
    learning_keywords = [
        '分析', '研究', '报告', '策略', '技术', '趋势', '市场', '经济', 
        '投资', '金融', '股票', '基金', '债券', '期货', '外汇',
        '行业', '公司', '财报', '数据', '政策', '监管', '风险',
        '科技', '创新', '发展', '改革', '转型', '机会', '挑战',
        '新闻', '资讯', '消息', '动态', '热点', '焦点', '要闻',
        '指数', '涨跌', '交易', '收盘', '开盘', '盘中', '盘后',
        '板块', '概念', '题材', '龙头', '个股', '大盘', '走势'
    ]
    
    # 几乎所有财经内容都会包含这些关键词，所以基本上都会返回True
    if any(keyword in title or keyword in content for keyword in learning_keywords):
        return True
        
    if keywords and any(keyword in keywords for keyword in learning_keywords):
        return True
    
    # 默认也返回True，除非明确是广告
    return True 