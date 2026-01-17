"""
通知服务
实现站内消息和邮件通知功能
"""

import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """
    通知服务类
    
    提供站内消息和邮件通知功能
    """
    
    @staticmethod
    def send_in_app_notification(recipient_email, notification_type, title, content, leave_request_id=None):
        """
        发送站内消息通知
        
        Args:
            recipient_email: 接收人邮箱
            notification_type: 通知类型
            title: 通知标题
            content: 通知内容
            leave_request_id: 关联的请假申请ID
            
        Returns:
            Notification: 创建的通知对象
        """
        try:
            notification = Notification.objects.create(
                recipient_email=recipient_email,
                notification_type=notification_type,
                title=title,
                content=content,
                leave_request_id=leave_request_id
            )
            
            logger.info(f"站内消息已创建: {notification.id} -> {recipient_email}")
            return notification
            
        except Exception as e:
            logger.error(f"创建站内消息失败: {e}", exc_info=True)
            raise
    
    @staticmethod
    def send_email_notification(recipient_email, subject, message, html_message=None):
        """
        发送邮件通知
        
        Args:
            recipient_email: 接收人邮箱
            subject: 邮件主题
            message: 邮件内容（纯文本）
            html_message: 邮件内容（HTML格式），可选
            
        Returns:
            bool: 是否发送成功
        """
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"邮件已发送: {subject} -> {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"发送邮件失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    def notify_task_assigned(recipient_email, leave_request, task_name):
        """
        通知任务分配
        
        Args:
            recipient_email: 审批人邮箱
            leave_request: 请假申请对象
            task_name: 任务名称
        """
        title = f"新的审批任务：{task_name}"
        content = (
            f"您有一个新的审批任务需要处理。\n\n"
            f"申请人：{leave_request.staff_full_name}\n"
            f"部门：{leave_request.staff_dept}\n"
            f"请假类型：{leave_request.get_leave_type_display()}\n"
            f"请假时长：{leave_request.leave_hours}小时\n"
            f"请假原因：{leave_request.reason}\n"
        )
        
        # 发送站内消息
        NotificationService.send_in_app_notification(
            recipient_email=recipient_email,
            notification_type='task_assigned',
            title=title,
            content=content,
            leave_request_id=leave_request.id
        )
        
        # 发送邮件
        email_subject = title
        email_message = content
        NotificationService.send_email_notification(
            recipient_email=recipient_email,
            subject=email_subject,
            message=email_message
        )
    
    @staticmethod
    def notify_request_approved(recipient_email, leave_request, approver_name, comment=''):
        """
        通知申请已批准
        
        Args:
            recipient_email: 申请人邮箱
            leave_request: 请假申请对象
            approver_name: 审批人姓名
            comment: 审批意见
        """
        title = "您的请假申请已批准"
        content = (
            f"您的请假申请已被批准。\n\n"
            f"审批人：{approver_name}\n"
            f"审批意见：{comment or '无'}\n"
            f"请假类型：{leave_request.get_leave_type_display()}\n"
            f"请假时长：{leave_request.leave_hours}小时\n"
        )
        
        NotificationService.send_in_app_notification(
            recipient_email=recipient_email,
            notification_type='request_approved',
            title=title,
            content=content,
            leave_request_id=leave_request.id
        )
        
        NotificationService.send_email_notification(
            recipient_email=recipient_email,
            subject=title,
            message=content
        )
    
    @staticmethod
    def notify_request_rejected(recipient_email, leave_request, approver_name, comment=''):
        """
        通知申请已拒绝
        
        Args:
            recipient_email: 申请人邮箱
            leave_request: 请假申请对象
            approver_name: 审批人姓名
            comment: 拒绝理由
        """
        title = "您的请假申请已被拒绝"
        content = (
            f"您的请假申请已被拒绝。\n\n"
            f"审批人：{approver_name}\n"
            f"拒绝理由：{comment or '无'}\n"
            f"请假类型：{leave_request.get_leave_type_display()}\n"
            f"请假时长：{leave_request.leave_hours}小时\n"
        )
        
        NotificationService.send_in_app_notification(
            recipient_email=recipient_email,
            notification_type='request_rejected',
            title=title,
            content=content,
            leave_request_id=leave_request.id
        )
        
        NotificationService.send_email_notification(
            recipient_email=recipient_email,
            subject=title,
            message=content
        )
    
    @staticmethod
    def notify_request_returned(recipient_email, leave_request, approver_name, comment=''):
        """
        通知申请已退回
        
        Args:
            recipient_email: 申请人邮箱
            leave_request: 请假申请对象
            approver_name: 审批人姓名
            comment: 退回理由
        """
        title = "您的请假申请已被退回"
        content = (
            f"您的请假申请已被退回，请修改后重新提交。\n\n"
            f"审批人：{approver_name}\n"
            f"退回理由：{comment or '无'}\n"
            f"请假类型：{leave_request.get_leave_type_display()}\n"
            f"请假时长：{leave_request.leave_hours}小时\n"
        )
        
        NotificationService.send_in_app_notification(
            recipient_email=recipient_email,
            notification_type='request_returned',
            title=title,
            content=content,
            leave_request_id=leave_request.id
        )
        
        NotificationService.send_email_notification(
            recipient_email=recipient_email,
            subject=title,
            message=content
        )
    
    @staticmethod
    def notify_timeout_reminder(recipient_email, leave_request, task_name):
        """
        通知超时提醒
        
        Args:
            recipient_email: 审批人邮箱
            leave_request: 请假申请对象
            task_name: 任务名称
        """
        title = f"审批任务超时提醒：{task_name}"
        content = (
            f"您有一个审批任务已超时，请尽快处理。\n\n"
            f"申请人：{leave_request.staff_full_name}\n"
            f"部门：{leave_request.staff_dept}\n"
            f"请假类型：{leave_request.get_leave_type_display()}\n"
            f"请假时长：{leave_request.leave_hours}小时\n"
        )
        
        NotificationService.send_in_app_notification(
            recipient_email=recipient_email,
            notification_type='timeout_reminder',
            title=title,
            content=content,
            leave_request_id=leave_request.id
        )
        
        NotificationService.send_email_notification(
            recipient_email=recipient_email,
            subject=title,
            message=content
        )
    
    @staticmethod
    def notify_cc_users(cc_emails, leave_request, status_change):
        """
        通知抄送人
        
        Args:
            cc_emails: 抄送人邮箱列表
            leave_request: 请假申请对象
            status_change: 状态变化描述
        """
        title = f"请假申请状态更新：{status_change}"
        content = (
            f"您抄送的请假申请状态已更新。\n\n"
            f"申请人：{leave_request.staff_full_name}\n"
            f"部门：{leave_request.staff_dept}\n"
            f"请假类型：{leave_request.get_leave_type_display()}\n"
            f"请假时长：{leave_request.leave_hours}小时\n"
            f"当前状态：{leave_request.get_status_display()}\n"
        )
        
        for email in cc_emails:
            NotificationService.send_in_app_notification(
                recipient_email=email,
                notification_type='task_completed',
                title=title,
                content=content,
                leave_request_id=leave_request.id
            )
