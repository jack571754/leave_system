"""
Celery 配置文件
配置异步任务队列和定时任务
"""

import os
from celery import Celery
from celery.schedules import crontab

# 设置 Django settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')

app = Celery('leave_system')

# 从 Django settings 加载配置，使用 CELERY 命名空间
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有已注册 app 中的 tasks.py
app.autodiscover_tasks()

# 配置 Celery Beat 定时任务
app.conf.beat_schedule = {
    'check-timeout-tasks-every-hour': {
        'task': 'leave_api.tasks.check_timeout_tasks',
        'schedule': crontab(minute=0),  # 每小时执行一次
    },
}


@app.task(bind=True)
def debug_task(self):
    """调试任务"""
    print(f'Request: {self.request!r}')
