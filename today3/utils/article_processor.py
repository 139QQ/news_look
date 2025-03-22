import re
from bs4 import BeautifulSoup
from datetime import datetime

class ArticleProcessor:
    """文章处理器，用于提取和处理文章内容"""
    
    @staticmethod
    def extract_images(html_content):
        """从HTML内容中提取图片链接"""
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        img_links = []
        
        for img in soup.find_all('img'):
            if img.get('src'):
                img_links.append(img['src'])
                
        return img_links
    
    @staticmethod
    def clean_html_with_images(element):
        """清理HTML内容，但保留图片链接"""
        if not element:
            return ""
            
        # 获取HTML内容
        html = str(element)
        
        # 创建新的BeautifulSoup对象
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除script和style标签
        for script in soup(["script", "style"]):
            script.decompose()
            
        # 提取图片链接
        img_links = []
        for img in soup.find_all('img'):
            if img.get('src'):
                img_links.append(img['src'])
                
        # 获取文本
        text = soup.get_text(separator="\n", strip=True)
        
        # 清理多余的空白字符
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        
        # 添加图片链接到文本末尾
        if img_links:
            text += "\n\n图片链接:\n" + "\n".join(img_links)
            
        return text
    
    @staticmethod
    def extract_keywords(text, top_n=5):
        """从文本中提取关键词"""
        # 简单实现，实际可以使用更复杂的算法
        if not text:
            return ""
            
        # 移除标点符号
        text = re.sub(r'[^\w\s]', '', text)
        
        # 分词
        words = text.split()
        
        # 统计词频
        word_freq = {}
        for word in words:
            if len(word) > 1:  # 忽略单字符
                word_freq[word] = word_freq.get(word, 0) + 1
                
        # 排序并取前N个
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        top_words = [word for word, freq in sorted_words[:top_n]]
        
        return ", ".join(top_words) 