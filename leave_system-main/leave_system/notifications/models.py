"""
通知系统数据模型
"""

from django.db import models


class Notification(models.Model):
    """通知模型"""
    TYPE_CHOICES = [
        ('task_assigned', '任务分配'),
        ('task_completed', '任务完成'),
        ('request_approved', '申请批准'),
        ('request_rejected', '申请拒绝'),
        ('request_returned', '申请退回'),
        ('timeout_reminder', '超时提醒'),
        ('urge', '催办'),
    ]
    
    recipient_email = models.EmailField(
        verbose_name='接收人邮箱'
    )
    
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name='通知类型'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='通知标题'
    )
    
    content = models.TextField(
        verbose_name='通知内容'
    )
    
    leave_request_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='关联的请假申请ID'
    )
    
    is_read = models.BooleanField(
        default=False,
        verbose_name='是否已读'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='阅读时间'
    )
    
    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_email', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient_email}"
