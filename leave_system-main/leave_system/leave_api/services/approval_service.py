"""
审批核心服务
实现审批流程的核心业务逻辑
"""

import logging
from django.db import transaction
from django.utils import timezone
from leave_api.models import LeaveRequest, ApprovalHistory
from leave_api.services.rule_service import ApprovalRuleService
from leave_api.spiff_client_v2 import spiff_client
from leave_api.signals import trigger_workflow_completed, trigger_task_ready
from notifications.tasks import send_email_notification, send_in_app_notification

logger = logging.getLogger(__name__)


class ApprovalService:
    """
    审批服务类
    
    封装审批流程的核心业务逻辑，包括：
    - 提交请假申请
    - 批准任务
    - 拒绝任务
    - 退回任务
    """
    
    def __init__(self):
        self.rule_service = ApprovalRuleService()
    
    @transaction.atomic
    def submit_leave_request(self, leave_request):
        """
        提交请假申请
        
        Args:
            leave_request: LeaveRequest 实例（已保存到数据库）
            
        Returns:
            LeaveRequest: 更新后的请假申请
        """
        try:
            # 1. 根据规则选择流程规范
            workflow_spec_name = self.rule_service.select_workflow_spec(leave_request)
            
            # 2. 准备流程变量
            workflow_data = {
                'leave_request_id': leave_request.id,
                'user_email': leave_request.user_email,
                'staff_full_name': leave_request.staff_full_name,
                'staff_dept': leave_request.staff_dept,
                'leave_type': leave_request.leave_type,
                'duration': float(leave_request.duration) if leave_request.duration else 0,
                'leave_hours': leave_request.leave_hours,
                'reason': leave_request.reason,
            }
            
            # 3. 启动 SpiffWorkflow 流程
            result = spiff_client.start_process(workflow_spec_name, workflow_data)
            
            if not result:
                raise Exception("启动工作流失败")
            
            # 4. 更新申请状态
            leave_request.process_instance_id = result['id']
            leave_request.workflow_spec_name = workflow_spec_name
            leave_request.workflow_state = result['workflow_state']
            leave_request.status = result['status']
            leave_request.submitted_at = timezone.now()
            leave_request.save()
            
            # 5. 记录历史
            ApprovalHistory.objects.create(
                leave_request=leave_request,
                action='submit',
                operator_email=leave_request.user_email,
                operator_name=leave_request.staff_full_name,
                operator_role='申请人',
                comment='提交申请'
            )
            
            # 6. 处理工作流事件
            self._handle_workflow_events(leave_request, result)
            
            logger.info(f"请假申请提交成功: {leave_request.id}, 流程实例: {result['id']}")
            
            return leave_request
            
        except Exception as e:
            logger.error(f"提交请假申请失败: {e}", exc_info=True)
            raise
    
    @transaction.atomic
    def approve_task(self, leave_request, task_id, approver_email, approver_name, comment=''):
        """
        批准任务
        
        Args:
            leave_request: LeaveRequest 实例
            task_id: 任务 ID
            approver_email: 审批人邮箱
            approver_name: 审批人姓名
            comment: 审批意见
            
        Returns:
            LeaveRequest: 更新后的请假申请
        """
        try:
            # 1. 准备任务数据
            task_data = {
                'action': 'approve',
                'approver_email': approver_email,
                'approver_name': approver_name,
                'comment': comment,
                'timestamp': timezone.now().isoformat()
            }
            
            # 2. 完成任务
            result = spiff_client.complete_task(
                leave_request.workflow_state,
                leave_request.workflow_spec_name or leave_request.process_model_id,
                task_id,
                task_data
            )
            
            if not result:
                raise Exception("完成任务失败")
            
            # 3. 更新申请状态
            leave_request.workflow_state = result['workflow_state']
            leave_request.status = result['status']
            
            if result['completed']:
                leave_request.completed_at = timezone.now()
                # 从工作流数据中获取最终结果
                final_result = result.get('data', {}).get('final_result', 'approved')
                leave_request.status = final_result
            
            leave_request.save()
            
            # 4. 记录历史
            ApprovalHistory.objects.create(
                leave_request=leave_request,
                action='approve',
                operator_email=approver_email,
                operator_name=approver_name,
                operator_role='审批人',
                comment=comment,
                task_id=task_id
            )
            
            # 5. 处理工作流事件
            self._handle_workflow_events(leave_request, result)
            
            logger.info(f"任务批准成功: {task_id}, 申请: {leave_request.id}")
            
            return leave_request
            
        except Exception as e:
            logger.error(f"批准任务失败: {e}", exc_info=True)
            raise
    
    @transaction.atomic
    def reject_task(self, leave_request, task_id, approver_email, approver_name, comment=''):
        """
        拒绝任务
        
        Args:
            leave_request: LeaveRequest 实例
            task_id: 任务 ID
            approver_email: 审批人邮箱
            approver_name: 审批人姓名
            comment: 拒绝理由
            
        Returns:
            LeaveRequest: 更新后的请假申请
        """
        try:
            # 1. 准备任务数据
            task_data = {
                'action': 'reject',
                'approver_email': approver_email,
                'approver_name': approver_name,
                'comment': comment,
                'timestamp': timezone.now().isoformat()
            }
            
            # 2. 完成任务
            result = spiff_client.complete_task(
                leave_request.workflow_state,
                leave_request.workflow_spec_name or leave_request.process_model_id,
                task_id,
                task_data
            )
            
            if not result:
                raise Exception("完成任务失败")
            
            # 3. 更新申请状态
            leave_request.workflow_state = result['workflow_state']
            leave_request.status = 'rejected'
            leave_request.completed_at = timezone.now()
            leave_request.save()
            
            # 4. 记录历史
            ApprovalHistory.objects.create(
                leave_request=leave_request,
                action='reject',
                operator_email=approver_email,
                operator_name=approver_name,
                operator_role='审批人',
                comment=comment,
                task_id=task_id
            )
            
            # 5. 处理工作流事件
            self._handle_workflow_events(leave_request, result)
            
            logger.info(f"任务拒绝成功: {task_id}, 申请: {leave_request.id}")
            
            return leave_request
            
        except Exception as e:
            logger.error(f"拒绝任务失败: {e}", exc_info=True)
            raise
    
    @transaction.atomic
    def return_task(self, leave_request, task_id, approver_email, approver_name, return_to='applicant', comment=''):
        """
        退回任务
        
        Args:
            leave_request: LeaveRequest 实例
            task_id: 任务 ID
            approver_email: 审批人邮箱
            approver_name: 审批人姓名
            return_to: 退回目标（'applicant' 或 'previous'）
            comment: 退回理由
            
        Returns:
            LeaveRequest: 更新后的请假申请
        """
        try:
            # 1. 准备任务数据
            task_data = {
                'action': 'return',
                'return_to': return_to,
                'approver_email': approver_email,
                'approver_name': approver_name,
                'comment': comment,
                'timestamp': timezone.now().isoformat()
            }
            
            # 2. 完成任务
            result = spiff_client.complete_task(
                leave_request.workflow_state,
                leave_request.workflow_spec_name or leave_request.process_model_id,
                task_id,
                task_data
            )
            
            if not result:
                raise Exception("完成任务失败")
            
            # 3. 更新申请状态
            leave_request.workflow_state = result['workflow_state']
            leave_request.status = result['status']
            leave_request.save()
            
            # 4. 记录历史
            ApprovalHistory.objects.create(
                leave_request=leave_request,
                action='return',
                operator_email=approver_email,
                operator_name=approver_name,
                operator_role='审批人',
                comment=comment,
                task_id=task_id
            )
            
            # 5. 处理工作流事件
            self._handle_workflow_events(leave_request, result)
            
            logger.info(f"任务退回成功: {task_id}, 申请: {leave_request.id}")
            
            return leave_request
            
        except Exception as e:
            logger.error(f"退回任务失败: {e}", exc_info=True)
            raise
    
    def get_user_tasks(self, user_email):
        """
        获取用户的待办任务
        
        Args:
            user_email: 用户邮箱
            
        Returns:
            list: 任务列表
        """
        tasks = []
        
        # 查询所有 pending 状态的申请
        pending_requests = LeaveRequest.objects.filter(status='pending')
        
        for leave_request in pending_requests:
            if not leave_request.workflow_state:
                continue
            
            # 从工作流中获取任务
            workflow_tasks = spiff_client.get_user_tasks(
                leave_request.workflow_state,
                leave_request.workflow_spec_name or leave_request.process_model_id,
                user_email
            )
            
            # 添加申请信息
            for task in workflow_tasks:
                task['leave_request'] = {
                    'id': leave_request.id,
                    'user_email': leave_request.user_email,
                    'staff_full_name': leave_request.staff_full_name,
                    'staff_dept': leave_request.staff_dept,
                    'leave_type': leave_request.leave_type,
                    'duration': float(leave_request.duration) if leave_request.duration else 0,
                    'reason': leave_request.reason,
                    'submitted_at': leave_request.submitted_at.isoformat() if leave_request.submitted_at else None
                }
                tasks.append(task)
        
        return tasks
    
    def _handle_workflow_events(self, leave_request, result):
        """
        处理工作流事件
        
        根据工作流执行结果触发相应的信号和通知
        
        Args:
            leave_request: LeaveRequest 实例
            result: 工作流执行结果字典
        """
        try:
            # 检查工作流是否完成
            if result.get('completed', False):
                # 触发工作流完成信号
                workflow_data = result.get('data', {})
                trigger_workflow_completed(
                    workflow_instance_id=leave_request.process_instance_id,
                    workflow_data=workflow_data
                )
                logger.info(f"触发工作流完成信号: {leave_request.process_instance_id}")
                
                # 发送完成通知给申请人
                self._send_completion_notification(leave_request)
                
            else:
                # 触发任务就绪信号（如果有新的待办任务）
                ready_tasks = result.get('ready_tasks', [])
                for task in ready_tasks:
                    trigger_task_ready(
                        workflow_instance_id=leave_request.process_instance_id,
                        task_id=task.get('id'),
                        task_data=task
                    )
                    logger.info(
                        f"触发任务就绪信号: {task.get('id')}, "
                        f"分配给 {task.get('assigned_to')}"
                    )
                    
                    # 发送任务通知给审批人
                    self._send_task_notification(leave_request, task)
                    
        except Exception as e:
            logger.error(f"处理工作流事件失败: {e}", exc_info=True)
            # 不抛出异常，避免影响主流程
    
    def _send_task_notification(self, leave_request, task):
        """
        发送任务通知给审批人
        
        Args:
            leave_request: LeaveRequest 实例
            task: 任务信息字典
        """
        try:
            assigned_to = task.get('assigned_to')
            if not assigned_to:
                return
            
            # 准备通知内容
            subject = f"【待审批】{leave_request.staff_full_name}的请假申请"
            message = (
                f"您有一个新的审批任务：\n\n"
                f"申请人：{leave_request.staff_full_name}\n"
                f"部门：{leave_request.staff_dept}\n"
                f"请假类型：{leave_request.leave_type}\n"
                f"请假时长：{leave_request.duration}天\n"
                f"请假事由：{leave_request.reason}\n\n"
                f"请及时处理。"
            )
            
            # 异步发送邮件通知
            send_email_notification.delay(
                recipient_email=assigned_to,
                subject=subject,
                message=message
            )
            
            logger.info(f"已发送任务通知: {assigned_to}")
            
        except Exception as e:
            logger.error(f"发送任务通知失败: {e}", exc_info=True)
    
    def _send_completion_notification(self, leave_request):
        """
        发送完成通知给申请人
        
        Args:
            leave_request: LeaveRequest 实例
        """
        try:
            # 准备通知内容
            status_text = '已批准' if leave_request.status == 'approved' else '已拒绝'
            subject = f"【审批结果】您的请假申请{status_text}"
            message = (
                f"您的请假申请已完成审批：\n\n"
                f"申请编号：{leave_request.id}\n"
                f"请假类型：{leave_request.leave_type}\n"
                f"请假时长：{leave_request.duration}天\n"
                f"审批结果：{status_text}\n\n"
                f"感谢您的使用。"
            )
            
            # 异步发送邮件通知
            send_email_notification.delay(
                recipient_email=leave_request.user_email,
                subject=subject,
                message=message
            )
            
            logger.info(f"已发送完成通知: {leave_request.user_email}")
            
        except Exception as e:
            logger.error(f"发送完成通知失败: {e}", exc_info=True)
