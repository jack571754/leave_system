"""
通知序列化器
"""

from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """通知序列化器"""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient_email',
            'notification_type',
            'notification_type_display',
            'title',
            'content',
            'leave_request_id',
            'is_read',
            'created_at',
            'read_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at', 'notification_type_display']
