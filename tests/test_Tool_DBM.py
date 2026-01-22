import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.Tool_DBM import get_tables_from_db
from config import settings
import pytest


def test_get_tables_from_db_success():
    """测试成功获取数据库表列表"""
    host = settings.db_host
    port = settings.db_port
    user = settings.db_user
    password = settings.db_password
    database = settings.db_name

    # 使用 .invoke() 方法调用 LangChain tool
    result = get_tables_from_db.invoke({
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database
    })

    assert "数据库中包含以下表" in result or "数据库中没有找到任何表" in result or "查询失败" in result


def test_get_tables_from_db_invalid_credentials():
    """测试使用无效凭据连接数据库"""
    result = get_tables_from_db.invoke({
        "host": settings.db_host,
        "port": settings.db_port,
        "user": "invalid_user",
        "password": "wrong_password",
        "database": settings.db_name
    })

    assert "查询失败" in result


def test_get_tables_from_db_invalid_host():
    """测试使用无效主机连接数据库"""
    result = get_tables_from_db.invoke({
        "host": "invalid_host_12345",
        "port": settings.db_port,
        "user": settings.db_user,
        "password": settings.db_password,
        "database": settings.db_name
    })

    assert "查询失败" in result


def test_get_tables_from_db_invalid_port():
    """测试使用无效端口连接数据库"""
    result = get_tables_from_db.invoke({
        "host": settings.db_host,
        "port": 9999,
        "user": settings.db_user,
        "password": settings.db_password,
        "database": settings.db_name
    })

    assert "查询失败" in result


def test_get_tables_from_db_nonexistent_database():
    """测试连接不存在的数据库"""
    result = get_tables_from_db.invoke({
        "host": settings.db_host,
        "port": settings.db_port,
        "user": settings.db_user,
        "password": settings.db_password,
        "database": "nonexistent_db_12345"
    })

    assert "查询失败" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])