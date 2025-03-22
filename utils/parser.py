import re
from bs4 import BeautifulSoup
from datetime import datetime

def extract_text(element):
    """从BeautifulSoup元素中提取文本"""
    if not element:
        return ""
        
    return element.get_text(strip=True)

def clean_html(element):
    """清理HTML内容，返回纯文本"""
    if not element:
        return ""
        
    # 获取HTML内容
    html = str(element)
    
    # 创建新的BeautifulSoup对象
    soup = BeautifulSoup(html, 'html.parser')
    
    # 移除script和style标签
    for script in soup(["script", "style"]):
        script.decompose()
        
    # 获取文本
    text = soup.get_text(separator="\n", strip=True)
    
    # 清理多余的空白字符
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    
    return text

def extract_date(text):
    """从文本中提取日期"""
    # 匹配常见的日期格式
    patterns = [
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)',  # 2023-03-16 或 2023年03月16日
        r'(\d{2}[-/]\d{1,2}[-/]\d{1,2})',         # 23-03-16
        r'(\d{1,2}月\d{1,2}日)',                   # 3月16日
        r'(\d{4}年\d{1,2}月\d{1,2}日)'             # 2023年3月16日
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            try:
                # 尝试转换为标准格式
                if '年' in date_str and '月' in date_str and '日' in date_str:
                    # 处理中文日期格式
                    date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                return date_str
            except:
                pass
            
    # 处理简单格式，如 "03-14"
    if re.search(r'\d{2}-\d{2}', text):
        match = re.search(r'(\d{2}-\d{2})', text)
        if match:
            # 添加当前年份
            current_year = datetime.now().year
            return f"{current_year}-{match.group(1)}"
    
    # 处理 "3月16日" 格式
    if re.search(r'\d+æ\x9c\x88\d+æ\x97¥', text):
        try:
            # 提取数字
            month_match = re.search(r'(\d+)æ\x9c\x88', text)
            day_match = re.search(r'(\d+)æ\x97¥', text)
            if month_match and day_match:
                month = month_match.group(1)
                day = day_match.group(1)
                current_year = datetime.now().year
                return f"{current_year}-{month}-{day}"
        except:
            pass
            
    return None

def extract_source(text):
    """从文本中提取来源"""
    # 匹配常见的来源格式
    patterns = [
        r'来源[:：]([^\s,，。；;]+)',  # 来源: xxx
        r'来自([^\s,，。；;]+)'        # 来自xxx
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
            
    return None 