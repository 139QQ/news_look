#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 数据接入适配器模块
支持API、CSV、流式数据等多种数据源的统一接入
"""

import json
import csv
import aiohttp
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, AsyncIterator, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataIngestionAdapter(ABC):
    """数据接入适配器基类"""
    
    def __init__(self, source_id: str, config: Dict[str, Any]):
        self.source_id = source_id
        self.config = config
        self.is_connected = False
        self.schema = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    async def fetch_data(self, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """获取数据"""
        pass
    
    @abstractmethod
    async def get_schema(self) -> Dict[str, Any]:
        """获取数据模式"""
        pass
    
    @abstractmethod
    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """验证数据"""
        pass


class APIIngestionAdapter(DataIngestionAdapter):
    """API接入适配器"""
    
    def __init__(self, source_id: str, config: Dict[str, Any]):
        super().__init__(source_id, config)
        self.base_url = config['base_url']
        self.headers = config.get('headers', {})
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self) -> bool:
        """建立HTTP会话连接"""
        try:
            self.session = aiohttp.ClientSession(headers=self.headers)
            self.is_connected = True
            logger.info(f"API适配器 {self.source_id} 连接成功")
            return True
        except Exception as e:
            logger.error(f"API适配器连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.close()
            self.session = None
            self.is_connected = False
    
    async def fetch_data(self, endpoint: str = '', **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """获取API数据"""
        if not self.is_connected:
            raise RuntimeError("API适配器未连接")
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}" if endpoint else self.base_url
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        for item in data:
                            yield self._normalize_data(item)
                    else:
                        yield self._normalize_data(data)
        except Exception as e:
            logger.error(f"API数据获取失败: {e}")
            raise
    
    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化数据格式"""
        return {
            'source_id': self.source_id,
            'raw_data': data,
            'ingested_at': datetime.now().isoformat(),
            **data
        }
    
    async def get_schema(self) -> Dict[str, Any]:
        """获取API数据模式"""
        return {
            'source_id': self.source_id, 
            'type': 'api',
            'base_url': self.base_url
        }
    
    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """验证数据"""
        return True


class CSVIngestionAdapter(DataIngestionAdapter):
    """CSV文件接入适配器"""
    
    def __init__(self, source_id: str, config: Dict[str, Any]):
        super().__init__(source_id, config)
        self.file_path = config['file_path']
        self.encoding = config.get('encoding', 'utf-8')
        self.delimiter = config.get('delimiter', ',')
    
    async def connect(self) -> bool:
        """连接CSV文件"""
        try:
            import os
            if os.path.exists(self.file_path):
                self.is_connected = True
                logger.info(f"CSV适配器 {self.source_id} 连接成功")
                return True
            else:
                logger.error(f"CSV文件不存在: {self.file_path}")
                return False
        except Exception as e:
            logger.error(f"CSV文件连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        self.is_connected = False
    
    async def fetch_data(self, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """获取CSV数据"""
        if not self.is_connected:
            raise RuntimeError("CSV适配器未连接")
        
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                for row in reader:
                    yield self._normalize_csv_row(row)
        except Exception as e:
            logger.error(f"CSV数据读取失败: {e}")
            raise
    
    def _normalize_csv_row(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化CSV行数据"""
        return {
            'source_id': self.source_id,
            'raw_data': row_data,
            'ingested_at': datetime.now().isoformat(),
            **row_data
        }
    
    async def get_schema(self) -> Dict[str, Any]:
        """获取CSV数据模式"""
        return {
            'source_id': self.source_id, 
            'type': 'csv',
            'file_path': self.file_path
        }
    
    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """验证数据"""
        return True


class StreamIngestionAdapter(DataIngestionAdapter):
    """流式数据接入适配器"""
    
    def __init__(self, source_id: str, config: Dict[str, Any]):
        super().__init__(source_id, config)
        self.topic = config['topic']
        self.bootstrap_servers = config['bootstrap_servers']
        self.consumer = None
    
    async def connect(self) -> bool:
        """连接流"""
        try:
            # 这里可以添加实际的Kafka连接逻辑
            self.is_connected = True
            logger.info(f"流式适配器 {self.source_id} 连接成功")
            return True
        except Exception as e:
            logger.error(f"流式适配器连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.consumer:
            # 关闭consumer
            pass
        self.is_connected = False
    
    async def fetch_data(self, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """获取流数据"""
        if not self.is_connected:
            raise RuntimeError("流式适配器未连接")
        
        # 模拟流数据，实际应该从Kafka等消息队列获取
        for i in range(10):
            yield self._normalize_stream_data({
                'id': i, 
                'message': f'stream_data_{i}',
                'timestamp': datetime.now().isoformat()
            })
            await asyncio.sleep(1)
    
    def _normalize_stream_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化流数据"""
        return {
            'source_id': self.source_id,
            'topic': self.topic,
            'raw_data': data,
            'ingested_at': datetime.now().isoformat(),
            **data
        }
    
    async def get_schema(self) -> Dict[str, Any]:
        """获取流数据模式"""
        return {
            'source_id': self.source_id, 
            'type': 'stream',
            'topic': self.topic,
            'bootstrap_servers': self.bootstrap_servers
        }
    
    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """验证数据"""
        return True


class AdapterFactory:
    """适配器工厂类"""
    
    @staticmethod
    def create_adapter(source_id: str, adapter_type: str, config: Dict[str, Any]) -> DataIngestionAdapter:
        """创建数据接入适配器"""
        adapters = {
            'api': APIIngestionAdapter,
            'csv': CSVIngestionAdapter,
            'stream': StreamIngestionAdapter,
        }
        
        if adapter_type not in adapters:
            raise ValueError(f"不支持的适配器类型: {adapter_type}")
        
        adapter_class = adapters[adapter_type]
        return adapter_class(source_id, config) 