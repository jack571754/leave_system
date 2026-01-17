"""
Celery 异步任务
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from leave_api.models import LeaveRequest, WorkflowEventLog
from notifications.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


@shared_task
def check_timeout_tasks():
    """
    检查超时任务并发送提醒
    
    定时任务，每小时执行一次
    检查所有待审批的任务，如果超过24小时未处理，发送超时提醒
    """
    try:
        from leave_api.models import ApprovalHistory
        
        # 查询所有待审批的申请
        pending_requests = LeaveRequest.objects.filter(status='pending')
        
        timeout_threshold = timezone.now() - timedelta(hours=24)
        timeout_count = 0
        checked_count = 0
        
        for leave_request in pending_requests:
            checked_count += 1
            
            # 获取最近的审批历史记录
            latest_history = ApprovalHistory.objects.filter(
                leave_request=leave_request
            ).order_by('-created_at').first()
            
            if latest_history and latest_history.created_at < timeout_threshold:
                # 检查是否已经发送过超时提醒（避免重复发送）
                recent_timeout_log = None
                if leave_request.process_instance_id:
                    recent_timeout_log = WorkflowEventLog.objects.filter(
                        workflow_instance_id=leave_request.process_instance_id,
                        event_type='timeout_reminder',
                        created_at__gte=timezone.now() - timedelta(hours=24)
                    ).exists()
                
                if not recent_timeout_log:
                    # 记录超时事件（如果有 workflow_instance_id）
                    if leave_request.process_instance_id:
                        WorkflowEventLog.objects.create(
                            workflow_instance_id=leave_request.process_instance_id,
                            event_type='timeout_reminder',
                            event_data={
                                'leave_request_id': leave_request.id,
                                'timeout_hours': 24
                            },
                            status='success'
                        )
                    
                    # 发送超时提醒通知给最近的审批人
                    NotificationService.send_in_app_notification(
                        recipient_email=latest_history.operator_email,
                        notification_type='timeout_reminder',
                        title='审批超时提醒',
                        content=f'您有一个审批任务已超时24小时，请尽快处理。申请人：{leave_request.staff_full_name or leave_request.user_email}',
                        leave_request_id=leave_request.id
                    )
                    
                    timeout_count += 1
                    logger.info(f"发送超时提醒: 申请 {leave_request.id}")
        
        logger.info(f"超时检查完成，发送 {timeout_count} 条提醒")
        return {'success': True, 'checked': checked_count, 'timeout_count': timeout_count}
        
    except Exception as e:
        logger.error(f"检查超时任务失败: {e}", exc_info=True)
        return {'success': False, 'checked': 0, 'timeout_count': 0, 'error': str(e)}


@shared_task
def send_urge_notification(leave_request_id, urge_by_email, urge_by_name='', message=''):
    """
    发送催办通知
    
    Args:
        leave_request_id: 请假申请 ID
        urge_by_email: 催办人邮箱
        urge_by_name: 催办人姓名
        message: 催办消息
    """
    try:
        from leave_api.models import LeaveRequest, ApprovalHistory
        
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        
        # 获取最近的审批人
        latest_history = ApprovalHistory.objects.filter(
            leave_request=leave_request
        ).order_by('-created_at').first()
        
        if not latest_history:
            return {'success': False, 'error': '未找到审批历史'}
        
        approver_email = latest_history.operator_email
        
        # 记录催办事件（如果有 workflow_instance_id）
        if leave_request.process_instance_id:
            WorkflowEventLog.objects.create(
                workflow_instance_id=leave_request.process_instance_id,
                event_type='urge',
                event_data={
                    'leave_request_id': leave_request_id,
                    'urge_by_email': urge_by_email,
                    'urge_by_name': urge_by_name,
                    'message': message
                },
                status='success'
            )
        
        # 发送催办通知
        title = f"催办提醒：{urge_by_name or urge_by_email} 催办了您的审批任务"
        content = (
            f"催办人：{urge_by_name or urge_by_email}\n"
            f"催办消息：{message or '请尽快处理'}\n\n"
            f"申请人：{leave_request.staff_full_name or leave_request.user_email}\n"
            f"部门：{leave_request.staff_dept}\n"
            f"请假类型：{leave_request.get_leave_type_display()}\n"
            f"请假时长：{leave_request.leave_hours}小时\n"
        )
        
        NotificationService.send_in_app_notification(
            recipient_email=approver_email,
            notification_type='urge',
            title=title,
            content=content,
            leave_request_id=leave_request_id
        )
        
        logger.info(f"发送催办通知: 申请 {leave_request_id}, 审批人 {approver_email}")
        return {'success': True}
        
    except Exception as e:
        logger.error(f"发送催办通知失败: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}
