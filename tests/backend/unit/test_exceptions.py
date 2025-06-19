#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常处理系统测试
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.newslook.core.exceptions import (
    NewsLookException, ConfigurationError, DatabaseError, 
    CrawlerError, ValidationError, APIError, create_exception
)


class TestNewsLookException:
    """NewsLook基础异常测试"""
    
    def test_basic_exception_creation(self):
        """测试基础异常创建"""
        message = "测试异常消息"
        error_code = "TEST_ERROR"
        context = {"key": "value"}
        
        exception = NewsLookException(message, error_code, context)
        
        assert exception.message == message
        assert exception.error_code == error_code
        assert exception.context == context
        assert isinstance(exception.timestamp, datetime)
        assert exception.traceback is not None
    
    def test_exception_to_dict(self):
        """测试异常转换为字典"""
        exception = NewsLookException("测试消息", "TEST_CODE", {"data": "test"})
        result = exception.to_dict()
        
        assert result['error_type'] == 'NewsLookException'
        assert result['error_code'] == 'TEST_CODE'
        assert result['message'] == '测试消息'
        assert result['context'] == {"data": "test"}
        assert 'timestamp' in result
        assert 'traceback' in result
    
    def test_exception_str_representation(self):
        """测试异常字符串表示"""
        exception = NewsLookException("测试消息", "TEST_CODE", {"key": "value"})
        str_repr = str(exception)
        
        assert "[TEST_CODE]" in str_repr
        assert "测试消息" in str_repr
        assert "Context:" in str_repr


class TestSpecificExceptions:
    """特定异常类型测试"""
    
    def test_configuration_error(self):
        """测试配置异常"""
        error = ConfigurationError("配置错误", config_key="database.host")
        
        assert error.error_code == "CONFIG_ERROR"
        assert error.context['config_key'] == "database.host"
        assert isinstance(error, NewsLookException)
    
    def test_database_error(self):
        """测试数据库异常"""
        error = DatabaseError("数据库连接失败", database_name="test.db", operation="connect")
        
        assert error.error_code == "DATABASE_ERROR"
        assert error.context['database_name'] == "test.db"
        assert error.context['operation'] == "connect"
    
    def test_crawler_error(self):
        """测试爬虫异常"""
        error = CrawlerError("爬取失败", source="sina", url="http://example.com")
        
        assert error.error_code == "CRAWLER_ERROR"
        assert error.context['source'] == "sina"
        assert error.context['url'] == "http://example.com"
    
    def test_validation_error(self):
        """测试验证异常"""
        error = ValidationError("字段验证失败", field="email", value="invalid-email")
        
        assert error.error_code == "VALIDATION_ERROR"
        assert error.context['field'] == "email"
        assert error.context['value'] == "invalid-email"
    
    def test_api_error(self):
        """测试API异常"""
        error = APIError("API调用失败", endpoint="/api/news", method="GET")
        
        assert error.error_code == "API_ERROR"
        assert error.context['endpoint'] == "/api/news"
        assert error.context['method'] == "GET"


class TestExceptionFactory:
    """异常工厂函数测试"""
    
    def test_create_known_exception(self):
        """测试创建已知异常类型"""
        exception = create_exception("CONFIG_ERROR", "配置错误")
        
        assert isinstance(exception, ConfigurationError)
        assert exception.error_code == "CONFIG_ERROR"
        assert exception.message == "配置错误"
    
    def test_create_unknown_exception(self):
        """测试创建未知异常类型"""
        exception = create_exception("UNKNOWN_ERROR", "未知错误")
        
        assert isinstance(exception, NewsLookException)
        assert exception.error_code == "UNKNOWN_ERROR"
        assert exception.message == "未知错误"
    
    def test_create_exception_with_context(self):
        """测试创建带上下文的异常"""
        context = {"module": "test", "line": 100}
        exception = create_exception("DATABASE_ERROR", "数据库错误", context=context)
        
        assert isinstance(exception, DatabaseError)
        assert exception.context == context


class TestExceptionHierarchy:
    """异常继承层次测试"""
    
    def test_inheritance_chain(self):
        """测试异常继承链"""
        # 测试所有异常都继承自NewsLookException
        config_error = ConfigurationError("配置错误")
        db_error = DatabaseError("数据库错误")
        crawler_error = CrawlerError("爬虫错误")
        
        assert isinstance(config_error, NewsLookException)
        assert isinstance(db_error, NewsLookException)
        assert isinstance(crawler_error, NewsLookException)
        
        # 测试特定继承关系
        from backend.newslook.core.exceptions import (
            DatabaseConnectionError, NetworkError, ParsingError
        )
        
        conn_error = DatabaseConnectionError("连接错误")
        net_error = NetworkError("网络错误")
        parse_error = ParsingError("解析错误")
        
        assert isinstance(conn_error, DatabaseError)
        assert isinstance(net_error, CrawlerError)
        assert isinstance(parse_error, CrawlerError)


class TestExceptionSerialization:
    """异常序列化测试"""
    
    def test_json_serialization(self):
        """测试JSON序列化"""
        exception = NewsLookException(
            "测试异常",
            "TEST_ERROR",
            {"data": "test", "number": 123}
        )
        
        # 转换为字典
        data = exception.to_dict()
        
        # 测试JSON序列化
        json_str = json.dumps(data, ensure_ascii=False, default=str)
        parsed_data = json.loads(json_str)
        
        assert parsed_data['error_type'] == 'NewsLookException'
        assert parsed_data['error_code'] == 'TEST_ERROR'
        assert parsed_data['message'] == '测试异常'
        assert parsed_data['context']['data'] == 'test'
        assert parsed_data['context']['number'] == 123


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 