#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财经新闻爬虫系统 - 相关股票解析器
提供从不同网站解析相关股票信息的功能
"""

import re
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List, Pattern, Set, Tuple

class StockParser:
    """股票解析器，负责从不同网站的页面中提取相关股票信息"""

    # 常用股票区域选择器
    DEFAULT_SELECTORS = [
        'div.stock-info', 'div.related-stocks', 'div.stock-list',
        'div.concept-stocks', 'div.stocks', 'div.stock-container',
        'div.related-concept', 'div.block-stocks'
    ]
    
    # 网站特定的股票区域选择器
    SITE_SELECTORS = {
        '新浪财经': ['div.category_stock', 'div.hq_related_stock'],
        '东方财富': ['div.stock_relate', 'div.relate_stock'],
        '网易财经': ['div.topbar_stock', 'div.relate_stock'],
        '凤凰财经': ['div.stock-list', 'div.stockrelation']
    }
    
    # 股票代码正则表达式
    STOCK_CODE_PATTERNS = [
        # A股代码模式
        r'(\d{6})[\.，,.]*([^\d]{1,4})',  # 例如: 600001,平安银行 或 600001.上证
        r'(\d{6})',                      # 仅股票代码
        # 港股代码模式
        r'(HK|hk)?\.?(\d{1,5})',         # 例如: HK.00700 或 hk00700
        # 美股代码模式
        r'(NYSE|NASDAQ|US|nasdaq|nyse)?[:：]?([A-Za-z.]{1,5})',  # 例如: NASDAQ:AAPL
    ]
    
    # 常见股票指数代码
    INDEX_CODES = {
        '上证指数': 'sh000001', '深证指数': 'sz399001', '创业板指': 'sz399006',
        '沪深300': 'sh000300', '中证500': 'sh000905', '上证50': 'sh000016',
        '恒生指数': 'hkHSI', '恒生科技指数': 'hkHSTECH', '国企指数': 'hkHSCEI',
        '道琼斯指数': 'usDJI', '纳斯达克指数': 'usNDX', '标普500': 'usSPX'
    }
    
    # 交易所映射
    EXCHANGE_MAPPING = {
        '上': 'sh', '深': 'sz', '沪': 'sh',
        '上证': 'sh', '深证': 'sz', '上交所': 'sh', '深交所': 'sz',
        '港': 'hk', '港股': 'hk', '香港': 'hk',
        '美': 'us', '美股': 'us', '纳斯达克': 'us', '纽约': 'us'
    }
    
    def __init__(self, site: str = None, custom_selectors: List[str] = None):
        """
        初始化股票解析器
        
        Args:
            site: 网站名称，用于选择特定选择器
            custom_selectors: 自定义选择器列表
        """
        self.site = site
        self.custom_selectors = custom_selectors or []
        
    def parse(self, html: str, content: str = None) -> List[Dict[str, Any]]:
        """
        从HTML中解析相关股票
        
        Args:
            html: HTML内容
            content: 正文内容，用于从正文中提取相关股票
            
        Returns:
            List[Dict[str, Any]]: 相关股票信息列表，每个字典包含code, name, exchange等字段
        """
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        stocks = []
        
        # 1. 尝试从专门的相关股票区域获取
        stocks_from_elements = self._extract_stocks_from_selectors(soup)
        stocks.extend(stocks_from_elements)
        
        # 2. 尝试从A标签获取
        stocks_from_links = self._extract_stocks_from_links(soup)
        stocks.extend(stocks_from_links)
        
        # 3. 如果提供了正文内容，尝试从正文中提取
        if content:
            stocks_from_content = self._extract_stocks_from_content(content)
            stocks.extend(stocks_from_content)
            
        # 4. 从整个HTML文本提取
        stocks_from_text = self._extract_stocks_from_text(soup.get_text())
        stocks.extend(stocks_from_text)
        
        # 去重和标准化
        return self._normalize_stocks(stocks)
        
    def _extract_stocks_from_selectors(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """从专门的股票区域提取股票信息"""
        stocks = []
        
        # 构建选择器列表
        selectors = self.custom_selectors.copy()
        
        if self.site and self.site in self.SITE_SELECTORS:
            selectors.extend(self.SITE_SELECTORS[self.site])
            
        selectors.extend(self.DEFAULT_SELECTORS)
        
        # 使用选择器尝试获取股票区域
        for selector in selectors:
            stock_elems = soup.select(selector)
            for elem in stock_elems:
                # 提取区域内的所有文本
                text = elem.get_text()
                
                # 从文本中提取股票信息
                stocks_from_text = self._extract_stocks_from_text(text)
                stocks.extend(stocks_from_text)
                
                # 查找区域内的链接
                stocks_from_links = self._extract_stocks_from_links(elem)
                stocks.extend(stocks_from_links)
                
        return stocks
        
    def _extract_stocks_from_links(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """从A标签提取股票信息"""
        stocks = []
        
        # 查找所有链接
        for a in soup.find_all('a'):
            href = a.get('href', '')
            text = a.get_text().strip()
            
            # 忽略空链接或没有文本的链接
            if not href or not text:
                continue
                
            # 检查链接中是否包含股票代码 - 常见的链接模式
            stock_code_patterns = [
                r'/stock/(\d{6})\.', # 例如: /stock/600001.html
                r'code=(\d{6})',     # 例如: stock.html?code=600001
                r's[hz](\d{6})',     # 例如: sh600001或sz000001
                r'(\d{6})\.',        # 例如: 600001.html
                r'hk(\d{5})',        # 例如: hk00700
                r'hk0*(\d{1,4})',    # 例如: hk700
                r'us([A-Za-z.]{1,5})' # 例如: usAAPL
            ]
            
            for pattern in stock_code_patterns:
                match = re.search(pattern, href)
                if match:
                    code = match.group(1)
                    
                    # 尝试从链接文本中提取股票名称
                    name = text
                    # 清理文本中的股票代码
                    name = re.sub(r'\d{6}', '', name)
                    name = re.sub(r'\(\s*\)', '', name)  # 移除空括号
                    name = name.strip()
                    
                    # 确定交易所
                    exchange = self._determine_exchange(href, code)
                    
                    stocks.append({
                        'code': code,
                        'name': name,
                        'exchange': exchange,
                        'source': 'link'
                    })
                    break
                    
        return stocks
        
    def _extract_stocks_from_content(self, content: str) -> List[Dict[str, Any]]:
        """从正文内容中提取股票信息"""
        if not content:
            return []
            
        # 提取可能包含股票的段落
        paragraphs = content.split('\n')
        stocks = []
        
        for paragraph in paragraphs:
            # 检查段落是否可能包含股票信息
            if '股' in paragraph or '证券' in paragraph or '代码' in paragraph:
                stocks_in_para = self._extract_stocks_from_text(paragraph)
                stocks.extend(stocks_in_para)
                
        return stocks
        
    def _extract_stocks_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取股票信息"""
        if not text:
            return []
            
        stocks = []
        
        # 使用正则表达式查找可能的股票代码和名称
        # 1. 查找"股票名称（股票代码）"格式
        name_code_pattern = r'([^（）()\d]{2,10})(?:（|\(|【)(\d{6})(?:）|\)|】)'
        for match in re.finditer(name_code_pattern, text):
            name = match.group(1).strip()
            code = match.group(2).strip()
            
            # 确定交易所
            exchange = self._determine_exchange_from_code(code)
            
            stocks.append({
                'code': code,
                'name': name,
                'exchange': exchange,
                'source': 'text_name_code'
            })
        
        # 2. 查找"股票代码 股票名称"格式
        for pattern in self.STOCK_CODE_PATTERNS:
            for match in re.finditer(pattern, text):
                if len(match.groups()) >= 2:
                    # 可能包含交易所前缀
                    prefix = match.group(1) if match.group(1) else ''
                    code_or_name = match.group(2).strip()
                    
                    # 根据组合判断是代码还是名称
                    if prefix.isdigit():
                        code = prefix
                        name = code_or_name
                    else:
                        # 处理包含交易所的情况
                        if prefix.lower() in ['hk', 'us', 'nyse', 'nasdaq']:
                            exchange = 'hk' if prefix.lower() == 'hk' else 'us'
                            code = code_or_name
                            name = ''  # 没有名称信息
                        else:
                            code = code_or_name if code_or_name.isdigit() else ''
                            name = prefix
                    
                    if code:
                        exchange = self._determine_exchange_from_code(code)
                        stocks.append({
                            'code': code,
                            'name': name,
                            'exchange': exchange,
                            'source': 'text_code_name'
                        })
                else:
                    # 只有代码，没有名称
                    code = match.group(1).strip()
                    exchange = self._determine_exchange_from_code(code)
                    stocks.append({
                        'code': code,
                        'name': '',
                        'exchange': exchange,
                        'source': 'text_code_only'
                    })
        
        # 3. 查找指数名称
        for index_name, index_code in self.INDEX_CODES.items():
            if index_name in text:
                code_parts = re.match(r'([a-z]+)(.+)', index_code)
                if code_parts:
                    exchange = code_parts.group(1)
                    code = code_parts.group(2)
                    stocks.append({
                        'code': code,
                        'name': index_name,
                        'exchange': exchange,
                        'is_index': True,
                        'source': 'text_index'
                    })
                    
        return stocks
        
    def _determine_exchange(self, href: str, code: str) -> str:
        """根据链接和代码确定交易所"""
        # 从链接中判断
        if 'sh' in href or 'sh' + code in href:
            return 'sh'
        elif 'sz' in href or 'sz' + code in href:
            return 'sz'
        elif 'hk' in href.lower():
            return 'hk'
        elif any(us in href.lower() for us in ['us', 'nasdaq', 'nyse']):
            return 'us'
        
        # 从代码判断
        return self._determine_exchange_from_code(code)
        
    def _determine_exchange_from_code(self, code: str) -> str:
        """根据股票代码确定交易所"""
        if not code:
            return ''
            
        # 纯数字代码
        if code.isdigit():
            code_num = int(code)
            # A股规则
            if len(code) == 6:
                if code.startswith(('6')):
                    return 'sh'  # 上证
                elif code.startswith(('0', '3')):
                    return 'sz'  # 深证
            # 港股规则
            elif len(code) <= 5:
                return 'hk'
                
        # 字母代码，大概率是美股
        elif re.match(r'^[A-Za-z.]+$', code):
            return 'us'
            
        return ''
        
    def _normalize_stocks(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """标准化和去重股票信息"""
        if not stocks:
            return []
            
        # 去重，优先保留有名称的记录
        normalized = {}
        
        for stock in stocks:
            code = stock.get('code', '')
            exchange = stock.get('exchange', '')
            
            if not code:
                continue
                
            # 生成标准化的键
            key = f"{exchange}{code}" if exchange else code
            
            # 如果是新股票或者当前记录比已存在的更完整（有名称），则更新
            if key not in normalized or (not normalized[key].get('name') and stock.get('name')):
                normalized[key] = stock
                
        # 过滤无效数据并排序
        result = []
        for key, stock in normalized.items():
            # 移除临时字段
            if 'source' in stock:
                del stock['source']
                
            # 确保基本字段存在
            if not stock.get('code'):
                continue
                
            result.append(stock)
            
        # 按交易所和代码排序
        result.sort(key=lambda x: (x.get('exchange', ''), x.get('code', '')))
        
        return result 