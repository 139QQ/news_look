#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest配置文件
统一测试环境设置和公共fixtures
"""

import os
import sys
import pytest
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# 添加项目路径到sys.path
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

# 设置工作目录为项目根目录
os.chdir(PROJECT_ROOT)

@pytest.fixture(scope="session")
def project_root():
    """项目根目录fixture"""
    return PROJECT_ROOT

@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录fixture"""
    return PROJECT_ROOT / 'tests' / 'backend' / 'fixtures'

@pytest.fixture(scope="session")
def db_dir():
    """数据库目录fixture"""
    return PROJECT_ROOT / 'data' / 'db'

@pytest.fixture(scope="function")
def sample_db():
    """样例数据库fixture"""
    # 可以在这里创建测试专用的数据库
    pass

# 设置测试标记
def pytest_configure(config):
    """Pytest配置"""
    config.addinivalue_line(
        "markers", "unit: 单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试"
    )
    config.addinivalue_line(
        "markers", "slow: 耗时测试"
    )

# 收集测试时的配置
def pytest_collection_modifyitems(config, items):
    """修改测试收集配置"""
    for item in items:
        # 为不同目录的测试添加标记
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance) 