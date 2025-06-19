#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
广告过滤模块 - 用于过滤各爬虫中的广告内容
"""

import re
import logging

# 获取日志记录器
logger = logging.getLogger('ad_filter')

class AdFilter:
    """广告过滤器类，用于检测和过滤广告内容"""
    
    def __init__(self, source_name, ad_url_patterns=None, ad_content_keywords=None):
        """
        初始化广告过滤器
        
        Args:
            source_name: 来源名称，如"新浪财经"、"网易财经"等
            ad_url_patterns: 广告URL特征列表，如果为None则使用默认特征
            ad_content_keywords: 广告内容关键词列表，如果为None则使用默认关键词
        """
        self.source_name = source_name
        self.ad_filtered_count = 0
        
        # 通用广告URL特征
        self.DEFAULT_AD_URL_PATTERNS = [
            'download', 
            'app',
            'promotion',
            'activity',
            'zhuanti',
            'special',
            'advert',
            'subscribe',
            'vip',
            'client',
            'topic',
            'hot'
        ]
        
        # 通用广告内容关键词
        self.DEFAULT_AD_CONTENT_KEYWORDS = [
            '下载APP',
            '扫描下载',
            '立即下载',
            '扫码下载',
            '专属福利',
            '点击下载',
            '独家活动',
            '活动详情',
            '注册即送',
            '点击安装',
            '官方下载',
            'APP专享',
            '扫一扫下载',
            '新人专享',
            '首次下载',
            '注册有礼'
        ]
        
        # 源特定的广告URL模式
        self.SOURCE_SPECIFIC_URL_PATTERNS = {
            '新浪财经': [
                'app/sfa_download', 
                'focus/app',
                'download.shtml',
                'app.sina.com',
                'k.sina.com.cn'
            ],
            '网易财经': [
                'special',
                'app.163.com'
            ],
            '腾讯财经': [
                'apk', 
                'store.qq.com'
            ],
            '凤凰财经': [
                'apk', 
                'store.ifeng.com'
            ],
            '东方财富': [
                'download.eastmoney.com',
                'zqt.eastmoney.com'
            ]
        }
        
        # 源特定的广告内容关键词
        self.SOURCE_SPECIFIC_CONTENT_KEYWORDS = {
            '新浪财经': [
                '新浪财经APP',
                '下载新浪',
                '安装新浪',
                '新浪财经客户端'
            ],
            '网易财经': [
                '网易财经APP',
                '下载网易',
                '安装网易',
                '网易财经客户端'
            ],
            '腾讯财经': [
                '腾讯财经APP',
                '腾讯新闻APP',
                '下载腾讯',
                '腾讯财经客户端'
            ],
            '凤凰财经': [
                '凤凰财经APP',
                '凤凰新闻APP',
                '下载凤凰',
                '凤凰财经客户端'
            ],
            '东方财富': [
                '东方财富APP',
                '下载东方财富',
                '东方财富客户端',
                '天天基金APP'
            ]
        }
        
        # 设置广告URL特征
        self.ad_url_patterns = ad_url_patterns if ad_url_patterns is not None else self.DEFAULT_AD_URL_PATTERNS.copy()
        
        # 添加源特定的URL特征
        if source_name in self.SOURCE_SPECIFIC_URL_PATTERNS:
            self.ad_url_patterns.extend(self.SOURCE_SPECIFIC_URL_PATTERNS[source_name])
        
        # 设置广告内容关键词
        self.ad_content_keywords = ad_content_keywords if ad_content_keywords is not None else self.DEFAULT_AD_CONTENT_KEYWORDS.copy()
        
        # 添加源特定的内容关键词
        if source_name in self.SOURCE_SPECIFIC_CONTENT_KEYWORDS:
            self.ad_content_keywords.extend(self.SOURCE_SPECIFIC_CONTENT_KEYWORDS[source_name])
        
        # 白名单内容类型
        self.WHITELIST_CATEGORIES = [
            '艺术展览', '新书发布', '文化活动', '公司公告',
            '行业会议', '政策解读', '专家观点', '研究报告'
        ]
        
        # 重要栏目白名单
        self.WHITELIST_SECTIONS = [
            '独家报道', '深度分析', '专题报道', '权威发布',
            '要闻', '头条', '重要公告'
        ]
        
        # 行业术语词典 - 这些词在特定语境下不应被视为广告特征
        self.INDUSTRY_TERMS = {
            'APP': ['APP开发', 'APP功能', 'APP市场', 'APP行业', 'APP体验', 'APP测评'],
            '下载': ['数据下载', '报告下载', '软件下载量', '下载统计', '下载排行'],
            '客户端': ['客户端软件', '客户端市场', '客户端更新', '客户端开发'],
            '促销': ['促销活动分析', '促销效果研究', '促销策略', '促销期间'],
            '活动': ['活动策划', '活动举办', '活动分析', '活动市场', '活动效果']
        }
        
        logger.info(f"初始化广告过滤器：{source_name}")
    
    def is_ad_url(self, url):
        """
        判断URL是否为广告URL
        
        Args:
            url: URL地址
            
        Returns:
            bool: 是否为广告URL
        """
        if not url:
            return False
            
        # 检查URL是否包含广告特征
        for pattern in self.ad_url_patterns:
            if pattern in url:
                logger.debug(f"检测到广告URL: {url}, 匹配模式: {pattern}")
                self.ad_filtered_count += 1
                return True
                
        return False
    
    def is_ad_content(self, text, title=None, section=None, category=None):
        """
        判断文本内容是否包含广告关键词（优化版）
        
        Args:
            text: 文本内容
            title: 文章标题
            section: 文章所属栏目
            category: 文章所属类别
            
        Returns:
            bool: 是否包含广告关键词
        """
        # 空内容或极短内容直接返回
        if not text or len(text) < 50:
            return False
        
        # 1. 白名单检查
        if self._is_in_whitelist(title, section, category):
            logger.debug(f"文章在白名单中，跳过广告检查: {title}")
            return False
        
        # 2. 媒体报道检查
        if title and self._is_media_report(text, title):
            logger.debug(f"识别为媒体报道，跳过广告检查: {title}")
            return False
        
        # 3. 关键词分析与分类
        ad_indicators = {
            'clear_ad': [],       # 明确广告特征
            'ambiguous': [],      # 模糊广告特征
            'industry_term': []   # 行业术语特征
        }
        
        for keyword in self.ad_content_keywords:
            if keyword not in text:
                continue
                
            # 检查行业术语上下文
            if self._check_industry_context(text, keyword):
                ad_indicators['industry_term'].append(keyword)
                continue
                
            # 分析关键词上下文
            context_result = self._analyze_keyword_context(text, keyword)
            if context_result is True:
                ad_indicators['clear_ad'].append(keyword)
                logger.debug(f"检测到明确广告关键词: {keyword}")
            elif context_result is False:
                continue
            else:
                ad_indicators['ambiguous'].append(keyword)
                logger.debug(f"检测到模糊广告关键词: {keyword}")
        
        # 4. 决策逻辑
        total_words = len(re.findall(r'\w+', text))
        
        # 如果有多个明确广告特征，直接判定为广告
        if len(ad_indicators['clear_ad']) >= 2:
            logger.info(f"检测到多个明确广告特征: {ad_indicators['clear_ad']}")
            return True
            
        # 如果只有一个明确广告特征，需要其他佐证
        elif len(ad_indicators['clear_ad']) == 1:
            # 计算模糊特征的权重
            ambiguous_weight = min(len(ad_indicators['ambiguous']) * 0.5, 2.0)
            # 减去行业术语的影响
            industry_discount = min(len(ad_indicators['industry_term']) * 0.5, 1.0)
            
            # 综合评分
            ad_score = 1.0 + ambiguous_weight - industry_discount
            
            # 根据文章长度设置不同阈值
            if total_words < 300:
                result = ad_score >= 1.5
                if result:
                    logger.info(f"短文本广告评分: {ad_score}，超过阈值1.5，判定为广告")
                return result
            else:
                result = ad_score >= 2.0
                if result:
                    logger.info(f"长文本广告评分: {ad_score}，超过阈值2.0，判定为广告")
                return result
        
        # 如果没有明确广告特征，只根据模糊特征和行业术语进行保守判断
        else:
            # 短文本更容易判断为非广告
            if total_words < 300:
                return False
                
            # 模糊特征相对较多，可能是广告
            if len(ad_indicators['ambiguous']) > 3 and len(ad_indicators['industry_term']) < 2:
                logger.info(f"检测到多个模糊广告特征: {ad_indicators['ambiguous']}")
                return True
                
            # 默认不是广告
            return False
        
        # 检查APP下载相关内容（兼容旧逻辑）
        source_term = self.source_name.replace('财经', '')
        app_download_patterns = [
            r'扫码下载.*app',
            r'扫码.*下载.*财经',
            f'下载.*{source_term}.*app',
            f'下载.*{source_term}.*客户端',
            f'{source_term}.*app.*下载',
            r'官方.*app.*下载',
            r'app.*扫码.*下载'
        ]
        
        for pattern in app_download_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"检测到APP下载正则匹配: {pattern}")
                return True
                
        return False
    
    def _analyze_keyword_context(self, text, keyword):
        """分析关键词上下文，判断是否为广告内容"""
        # 获取关键词所在句子
        sentences = re.split(r'[。！？.!?]', text)
        for sentence in sentences:
            if keyword in sentence:
                # 1. 检查是否在引号内（可能是报道内容）
                if re.search(r'["\'"""][^"\'""]*' + re.escape(keyword) + r'[^"\'""]*["\'"""]', sentence):
                    return False
                    
                # 2. 检查是否是新闻报道句式
                reporting_patterns = [
                    r'表示.*' + re.escape(keyword),
                    r'称.*' + re.escape(keyword), 
                    r'报道.*' + re.escape(keyword),
                    r'指出.*' + re.escape(keyword),
                    r'发布了.*' + re.escape(keyword),
                    r'推出了.*' + re.escape(keyword)
                ]
                
                for pattern in reporting_patterns:
                    if re.search(pattern, sentence):
                        return False
                
                # 3. 检查是否是典型广告句式
                ad_patterns = [
                    r'点击.*' + re.escape(keyword),
                    r'扫码.*' + re.escape(keyword),
                    r'下载.*' + re.escape(keyword) + r'.*即可',
                    r'立即.*' + re.escape(keyword)
                ]
                
                for pattern in ad_patterns:
                    if re.search(pattern, sentence):
                        return True
        
        # 默认返回中性评估，交由其他规则判断
        return None
    
    def _is_in_whitelist(self, title, section=None, category=None):
        """检查是否在白名单中"""
        if not title:
            return False
            
        # 检查栏目是否在白名单中
        if section and any(s in section for s in self.WHITELIST_SECTIONS):
            return True
            
        # 检查类别是否在白名单中
        if category and any(c in category for c in self.WHITELIST_CATEGORIES):
            return True
            
        # 检查标题是否包含白名单特征
        whitelist_title_patterns = [
            r'报告', r'研究', r'观点', r'解读', r'发布会',
            r'展览', r'展会', r'论坛', r'峰会', r'访谈',
            r'会议', r'政策', r'发布'
        ]
        
        for pattern in whitelist_title_patterns:
            if re.search(pattern, title):
                return True
                
        return False
    
    def _check_industry_context(self, text, keyword):
        """检查关键词是否在行业术语语境中"""
        for term_category, contexts in self.INDUSTRY_TERMS.items():
            if term_category in keyword:
                for context in contexts:
                    if context in text:
                        return True
        return False
    
    def _is_media_report(self, text, title):
        """识别是否为媒体行业相关报道"""
        media_report_patterns = [
            r'.*媒体.*报道',
            r'.*发布.*应用',
            r'.*推出.*客户端',
            r'.*上线.*平台',
            r'.*新版.*APP',
            r'.*更新.*功能'
        ]
        
        # 检查标题是否匹配媒体报道模式
        for pattern in media_report_patterns:
            if re.search(pattern, title):
                return True
        
        # 检查内容是否包含媒体报道特征词
        media_terms = ['用户体验', '功能介绍', '版本更新', '界面设计', '技术架构']
        matched_terms = [term for term in media_terms if term in text]
        
        # 如果匹配3个或更多特征词，可能是媒体报道
        return len(matched_terms) >= 3
    
    def reset_filter_count(self):
        """重置广告过滤计数器"""
        self.ad_filtered_count = 0
        
    def get_filter_count(self):
        """获取广告过滤计数"""
        return self.ad_filtered_count 