from django.apps import AppConfig


class LeaveApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leave_api'
    
    def ready(self):
        """
        应用就绪时的初始化操作
        导入信号处理器以确保它们被注册
        """
        import leave_api.signals  # noqa: F401
