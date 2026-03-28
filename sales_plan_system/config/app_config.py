"""
应用配置模块 - 使用 pydantic-settings 实现类型安全的环境变量管理

特性:
- 启动时验证必填项 (fail-fast)
- 类型转换自动处理
- 环境变量与 .env 文件支持
- 生产/开发环境自动适配
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取项目根目录 (config/settings.py 的父目录的父目录)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用配置 - 从环境变量加载"""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        env_prefix="",  # 不使用前缀
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter=None,
    )

    # ============================================
    # Django 核心配置
    # ============================================
    secret_key: str  # 必填 - 启动时验证
    debug: bool = False
    allowed_hosts: str = "localhost,127.0.0.1"

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """验证密钥安全性"""
        if not v or v == "your-secret-key-change-me-in-production":
            raise ValueError(
                "DJANGO_SECRET_KEY 未配置或使用了默认值！\n"
                "请设置环境变量或在 .env 文件中配置有效的密钥。\n"
                "生成方式: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
            )
        if len(v) < 32:
            raise ValueError("DJANGO_SECRET_KEY 长度必须至少 32 个字符")
        return v

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v) -> str:
        """处理列表输入"""
        if isinstance(v, list):
            return ",".join(v)
        return v

    def get_allowed_hosts(self) -> List[str]:
        """解析允许的主机列表"""
        hosts = [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]
        if self.debug:
            hosts.extend(["localhost", "127.0.0.1", "[::1]"])
            # 添加 Docker 内部网络
            hosts.append("0.0.0.0")
        return list(set(hosts))

    # ============================================
    # 数据库配置
    # ============================================
    database_url: str = "sqlite:///db_new.sqlite3"
    db_conn_max_age: int = 600  # 连接最大存活时间(秒)
    db_conn_health_checks: bool = True

    # ============================================
    # 安全配置
    # ============================================
    secure_ssl_redirect: bool = False
    secure_hsts_seconds: int = 0
    session_cookie_secure: bool = False
    csrf_cookie_secure: bool = False
    secure_proxy_ssl_header: bool = False

    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return not self.debug

    def get_security_settings(self) -> dict:
        """获取生产环境安全设置"""
        if not self.is_production():
            return {}

        return {
            "SECURE_SSL_REDIRECT": self.secure_ssl_redirect,
            "SECURE_HSTS_SECONDS": self.secure_hsts_seconds,
            "SESSION_COOKIE_SECURE": self.session_cookie_secure,
            "CSRF_COOKIE_SECURE": self.csrf_cookie_secure,
            "SECURE_CONTENT_TYPE_NOSNIFF": True,
            "SECURE_BROWSER_XSS_FILTER": True,
            "X_FRAME_OPTIONS": "DENY",
        }

    # ============================================
    # 其他配置
    # ============================================
    port: int = 8000
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"LOG_LEVEL 必须是: {', '.join(valid_levels)}")
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例 (带缓存)

    使用方式:
        from config.app_config import get_settings
        settings = get_settings()
        print(settings.secret_key)
    """
    return Settings()


# 注意: 不在模块级别创建 settings 实例
# 需要在 settings.py 中先调用 load_dotenv 后再调用 get_settings()

