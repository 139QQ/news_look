#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 数据接入适配器模块
支持API、CSV、流式数据等多种数据源的统一接入
"""

from .data_adapters import (
    DataIngestionAdapter,
    APIIngestionAdapter,
    CSVIngestionAdapter,
    StreamIngestionAdapter,
    AdapterFactory
)

__all__ = [
    'DataIngestionAdapter',
    'APIIngestionAdapter',
    'CSVIngestionAdapter',
    'StreamIngestionAdapter',
    'AdapterFactory'
] 