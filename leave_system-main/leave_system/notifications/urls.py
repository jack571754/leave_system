"""
通知 URL 路由配置
"""

from django.urls import path
from . import views

urlpatterns = [
    # 查询我的通知列表
    path('my-notifications/', views.get_my_notifications, name='get_my_notifications'),
    
    # 标记通知已读
    path('<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    
    # 标记所有通知已读
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
]
