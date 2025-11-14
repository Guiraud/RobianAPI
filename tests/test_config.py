"""
Tests for configuration module
"""
import pytest
from api.config import settings, get_platform_info


def test_settings_loaded():
    """Test that settings are loaded correctly"""
    assert settings is not None
    assert settings.app is not None
    assert settings.database is not None
    assert settings.redis is not None
    assert settings.security is not None


def test_app_settings():
    """Test application settings"""
    assert settings.app.app_name == "RobianAPI"
    assert settings.app.app_version == "1.0.0"
    assert settings.app.environment in ["development", "staging", "production"]
    assert settings.app.host == "0.0.0.0"
    assert settings.app.port == 8000


def test_database_settings():
    """Test database settings"""
    assert settings.database.postgres_server is not None
    assert settings.database.postgres_port == 5432
    assert settings.database.postgres_db == "robian_db"
    assert settings.database.database_url is not None
    assert "postgresql+asyncpg://" in settings.database.database_url


def test_redis_settings():
    """Test Redis cache settings"""
    assert settings.redis.redis_host is not None
    assert settings.redis.redis_port == 6379
    assert settings.redis.cache_ttl_debates == 300
    assert settings.redis.cache_ttl_streaming == 3600


def test_security_settings():
    """Test security settings"""
    assert settings.security.secret_key is not None
    assert len(settings.security.secret_key) > 0
    assert settings.security.algorithm == "HS256"
    assert len(settings.security.cors_origins_list) > 0


def test_platform_info():
    """Test platform information detection"""
    info = get_platform_info()

    assert "system" in info
    assert "python_version" in info
    assert info["system"] in ["Linux", "Darwin", "Windows"]
