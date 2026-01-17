"""
leave_system 包初始化
加载 Celery 应用
"""

# 导入 Celery 应用，确保 Django 启动时加载
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery 未安装时跳过
    pass
