"""
notifications Celery 任务
定义通知相关的异步任务
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_notification(self, recipient_email, subject, message, html_message=None):
    """
    发送邮件通知
    
    Args:
        recipient_email: 收件人邮箱
        subject: 邮件主题
        message: 邮件内容（纯文本）
        html_message: 邮件内容（HTML）
    """
    try:
        logger.info(f"发送邮件通知到: {recipient_email}")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"邮件发送成功: {recipient_email}")
        return f"邮件已发送到 {recipient_email}"
        
    except Exception as exc:
        logger.error(f"邮件发送失败: {recipient_email}, 错误: {exc}")
        # 重试机制
        raise self.retry(exc=exc, countdown=60)  # 60秒后重试


@shared_task
def send_in_app_notification(user_email, notification_type, title, content):
    """
    发送站内通知
    
    Args:
        user_email: 用户邮箱
        notification_type: 通知类型
        title: 通知标题
        content: 通知内容
    """
    try:
        from notifications.models import Notification
        
        logger.info(f"发送站内通知到用户: {user_email}")
        
        # 创建站内通知记录
        notification = Notification.objects.create(
            recipient_email=user_email,
            notification_type=notification_type,
            title=title,
            content=content,
            is_read=False
        )
        
        logger.info(f"站内通知创建成功: ID {notification.id}")
        return f"站内通知已发送到用户 {user_email}"
        
    except Exception as e:
        logger.error(f"发送站内通知失败: {user_email}, 错误: {e}", exc_info=True)
        raise
