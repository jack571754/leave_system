"""
工作流事件处理信号
使用 Django 信号机制处理工作流事件
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.dispatch import Signal, receiver
from leave_api.models import LeaveRequest, WorkflowEventLog

logger = logging.getLogger(__name__)

# 定义自定义信号
workflow_completed = Signal()  # 工作流完成信号
task_ready = Signal()  # 任务就绪信号


@receiver(workflow_completed)
@transaction.atomic
def handle_workflow_completed(sender, workflow_instance_id, workflow_data, **kwargs):
    """
    处理工作流完成事件
    
    当工作流完成时触发此信号处理器，更新业务状态并记录事件日志
    
    Args:
        sender: 信号发送者
        workflow_instance_id: 工作流实例 ID
        workflow_data: 工作流数据字典
        **kwargs: 其他参数
    """
    try:
        # 1. 幂等性检查 - 检查是否已处理过此事件
        event_key = f"workflow_completed_{workflow_instance_id}"
        existing_log = WorkflowEventLog.objects.filter(
            workflow_instance_id=workflow_instance_id,
            event_type='workflow_completed',
            status='success'
        ).first()
        
        if existing_log:
            logger.info(f"工作流完成事件已处理，跳过: {workflow_instance_id}")
            return
        
        # 2. 创建事件日志（待处理状态）
        event_log = WorkflowEventLog.objects.create(
            workflow_instance_id=workflow_instance_id,
            event_type='workflow_completed',
            event_data={
                'workflow_data': workflow_data,
                'timestamp': timezone.now().isoformat()
            },
            status='pending'
        )
        
        # 3. 查找对应的请假申请
        try:
            leave_request = LeaveRequest.objects.get(
                process_instance_id=workflow_instance_id
            )
        except LeaveRequest.DoesNotExist:
            error_msg = f"未找到对应的请假申请: {workflow_instance_id}"
            logger.error(error_msg)
            event_log.status = 'failed'
            event_log.error_message = error_msg
            event_log.processed_at = timezone.now()
            event_log.save()
            return
        
        # 4. 更新业务状态
        final_result = workflow_data.get('final_result', 'approved')
        
        # 状态合法性检查
        if leave_request.status in ['approved', 'rejected', 'cancelled']:
            logger.warning(
                f"请假申请 {leave_request.id} 已处于最终状态 {leave_request.status}，"
                f"不能更新为 {final_result}"
            )
            event_log.status = 'failed'
            event_log.error_message = f"状态冲突: 当前状态 {leave_request.status}"
            event_log.processed_at = timezone.now()
            event_log.save()
            return
        
        # 更新状态
        leave_request.status = final_result
        leave_request.completed_at = timezone.now()
        leave_request.save()
        
        # 5. 标记事件处理成功
        event_log.status = 'success'
        event_log.processed_at = timezone.now()
        event_log.save()
        
        logger.info(
            f"工作流完成事件处理成功: {workflow_instance_id}, "
            f"申请 {leave_request.id} 状态更新为 {final_result}"
        )
        
        # 6. 发送通知（可选，如果有通知服务）
        # TODO: 集成通知服务
        # from notifications.services import NotificationService
        # notification_service = NotificationService()
        # notification_service.send_approval_result_notification(leave_request, final_result)
        
    except Exception as e:
        logger.error(f"处理工作流完成事件失败: {e}", exc_info=True)
        if 'event_log' in locals():
            event_log.status = 'failed'
            event_log.error_message = str(e)
            event_log.processed_at = timezone.now()
            event_log.save()
        raise


@receiver(task_ready)
@transaction.atomic
def handle_task_ready(sender, workflow_instance_id, task_id, task_data, **kwargs):
    """
    处理任务就绪事件
    
    当新任务就绪时触发此信号处理器，记录事件日志并发送通知
    
    Args:
        sender: 信号发送者
        workflow_instance_id: 工作流实例 ID
        task_id: 任务 ID
        task_data: 任务数据字典
        **kwargs: 其他参数
    """
    try:
        # 1. 幂等性检查 - 检查是否已处理过此任务
        existing_log = WorkflowEventLog.objects.filter(
            workflow_instance_id=workflow_instance_id,
            task_id=task_id,
            event_type='task_ready',
            status='success'
        ).first()
        
        if existing_log:
            logger.info(f"任务就绪事件已处理，跳过: {task_id}")
            return
        
        # 2. 创建事件日志（待处理状态）
        event_log = WorkflowEventLog.objects.create(
            workflow_instance_id=workflow_instance_id,
            task_id=task_id,
            event_type='task_ready',
            event_data={
                'task_data': task_data,
                'timestamp': timezone.now().isoformat()
            },
            status='pending'
        )
        
        # 3. 查找对应的请假申请
        try:
            leave_request = LeaveRequest.objects.get(
                process_instance_id=workflow_instance_id
            )
        except LeaveRequest.DoesNotExist:
            error_msg = f"未找到对应的请假申请: {workflow_instance_id}"
            logger.error(error_msg)
            event_log.status = 'failed'
            event_log.error_message = error_msg
            event_log.processed_at = timezone.now()
            event_log.save()
            return
        
        # 4. 提取任务信息
        assigned_to = task_data.get('assigned_to')
        task_name = task_data.get('name', '未命名任务')
        
        if not assigned_to:
            logger.warning(f"任务 {task_id} 未分配审批人")
            event_log.status = 'failed'
            event_log.error_message = "任务未分配审批人"
            event_log.processed_at = timezone.now()
            event_log.save()
            return
        
        # 5. 标记事件处理成功
        event_log.status = 'success'
        event_log.processed_at = timezone.now()
        event_log.save()
        
        logger.info(
            f"任务就绪事件处理成功: {task_id}, "
            f"申请 {leave_request.id}, 分配给 {assigned_to}"
        )
        
        # 6. 发送任务通知（可选，如果有通知服务）
        # TODO: 集成通知服务
        # from notifications.services import NotificationService
        # notification_service = NotificationService()
        # notification_service.send_task_assigned_notification(
        #     task={'id': task_id, 'name': task_name, 'leave_request_id': leave_request.id},
        #     assignee_email=assigned_to
        # )
        
    except Exception as e:
        logger.error(f"处理任务就绪事件失败: {e}", exc_info=True)
        if 'event_log' in locals():
            event_log.status = 'failed'
            event_log.error_message = str(e)
            event_log.processed_at = timezone.now()
            event_log.save()
        raise


def trigger_workflow_completed(workflow_instance_id, workflow_data):
    """
    触发工作流完成信号
    
    这是一个辅助函数，用于在工作流完成时触发信号
    
    Args:
        workflow_instance_id: 工作流实例 ID
        workflow_data: 工作流数据字典
    """
    workflow_completed.send(
        sender=None,
        workflow_instance_id=workflow_instance_id,
        workflow_data=workflow_data
    )


def trigger_task_ready(workflow_instance_id, task_id, task_data):
    """
    触发任务就绪信号
    
    这是一个辅助函数，用于在任务就绪时触发信号
    
    Args:
        workflow_instance_id: 工作流实例 ID
        task_id: 任务 ID
        task_data: 任务数据字典
    """
    task_ready.send(
        sender=None,
        workflow_instance_id=workflow_instance_id,
        task_id=task_id,
        task_data=task_data
    )
