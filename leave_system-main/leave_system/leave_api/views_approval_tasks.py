"""
审批任务 API 视图
处理审批任务相关的 REST API 请求
"""

import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import LeaveRequest, ApprovalHistory
from .serializers import ApprovalTaskSerializer, LeaveRequestSerializer
from .services.approval_service import ApprovalService

logger = logging.getLogger(__name__)


@api_view(['GET'])
def get_my_approval_tasks(request):
    """
    查询我的待办审批任务
    
    GET /api/approval-tasks/my-tasks/?user_email=xxx
    
    查询参数：
        user_email: 审批人邮箱（必填）
    
    返回：
        {
            "success": true,
            "tasks": [
                {
                    "task_id": "task_123",
                    "task_name": "审批任务",
                    "leave_request_id": 1,
                    "leave_request": {...},
                    "assignee_email": "approver@test.com",
                    "created_at": "2026-01-17T10:00:00Z"
                }
            ]
        }
    
    HTTP 状态码:
        200: 查询成功
        400: 请求参数错误
        500: 服务器内部错误
    """
    try:
        user_email = request.query_params.get('user_email')
        
        if not user_email:
            return Response({
                'success': False,
                'error': '缺少必填参数: user_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 查询待审批的申请
        pending_requests = LeaveRequest.objects.filter(status='pending')
        
        tasks = []
        for leave_request in pending_requests:
            # 获取最近的审批历史，判断当前审批人
            latest_history = ApprovalHistory.objects.filter(
                leave_request=leave_request
            ).order_by('-created_at').first()
            
            # 简化处理：如果有审批历史且审批人匹配，则添加到任务列表
            if latest_history and latest_history.operator_email == user_email:
                task_data = {
                    'task_id': f'task_{leave_request.id}',
                    'task_name': '审批任务',
                    'leave_request_id': leave_request.id,
                    'leave_request': LeaveRequestSerializer(leave_request).data,
                    'assignee_email': user_email,
                    'created_at': latest_history.created_at
                }
                tasks.append(task_data)
        
        logger.info(f"查询待办任务: 用户 {user_email}, 任务数 {len(tasks)}")
        
        return Response({
            'success': True,
            'tasks': tasks
        })
    
    except Exception as e:
        logger.error(f"查询待办任务失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def approve_task(request, task_id):
    """
    批准审批任务
    
    POST /api/approval-tasks/{task_id}/approve/
    
    请求体：
        {
            "approver_email": "approver@test.com",
            "approver_name": "审批人",
            "comment": "同意"
        }
    
    HTTP 状态码:
        200: 批准成功
        400: 请求参数错误
        404: 任务不存在
        500: 服务器内部错误
    """
    try:
        approver_email = request.data.get('approver_email')
        approver_name = request.data.get('approver_name', '')
        comment = request.data.get('comment', '')
        
        if not approver_email:
            return Response({
                'success': False,
                'error': '缺少必填字段: approver_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 从 task_id 中提取 leave_request_id（格式：task_{id}）
        if task_id.startswith('task_'):
            leave_request_id = int(task_id.replace('task_', ''))
        else:
            leave_request_id = int(task_id)
        
        # 获取请假申请
        try:
            leave_request = LeaveRequest.objects.get(id=leave_request_id)
        except LeaveRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': '任务不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 使用 ApprovalService 处理批准
        approval_service = ApprovalService()
        result = approval_service.approve_task(
            leave_request_id=leave_request_id,
            approver_email=approver_email,
            approver_name=approver_name,
            comment=comment
        )
        
        if result['success']:
            logger.info(f"批准任务成功: 任务 {task_id}, 审批人 {approver_email}")
            return Response({
                'success': True,
                'message': '批准成功',
                'leave_request': LeaveRequestSerializer(leave_request).data
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', '批准失败')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except ValueError:
        return Response({
            'success': False,
            'error': '无效的任务ID'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"批准任务失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def reject_task(request, task_id):
    """
    拒绝审批任务
    
    POST /api/approval-tasks/{task_id}/reject/
    
    请求体：
        {
            "approver_email": "approver@test.com",
            "approver_name": "审批人",
            "comment": "不同意"
        }
    
    HTTP 状态码:
        200: 拒绝成功
        400: 请求参数错误
        404: 任务不存在
        500: 服务器内部错误
    """
    try:
        approver_email = request.data.get('approver_email')
        approver_name = request.data.get('approver_name', '')
        comment = request.data.get('comment', '')
        
        if not approver_email:
            return Response({
                'success': False,
                'error': '缺少必填字段: approver_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 从 task_id 中提取 leave_request_id
        if task_id.startswith('task_'):
            leave_request_id = int(task_id.replace('task_', ''))
        else:
            leave_request_id = int(task_id)
        
        # 获取请假申请
        try:
            leave_request = LeaveRequest.objects.get(id=leave_request_id)
        except LeaveRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': '任务不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 使用 ApprovalService 处理拒绝
        approval_service = ApprovalService()
        result = approval_service.reject_task(
            leave_request_id=leave_request_id,
            approver_email=approver_email,
            approver_name=approver_name,
            comment=comment
        )
        
        if result['success']:
            logger.info(f"拒绝任务成功: 任务 {task_id}, 审批人 {approver_email}")
            return Response({
                'success': True,
                'message': '拒绝成功',
                'leave_request': LeaveRequestSerializer(leave_request).data
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', '拒绝失败')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except ValueError:
        return Response({
            'success': False,
            'error': '无效的任务ID'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"拒绝任务失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def return_task(request, task_id):
    """
    退回审批任务
    
    POST /api/approval-tasks/{task_id}/return/
    
    请求体：
        {
            "approver_email": "approver@test.com",
            "approver_name": "审批人",
            "comment": "需要补充材料",
            "return_to": "applicant"  # 可选：applicant（申请人）或 previous（上一级）
        }
    
    HTTP 状态码:
        200: 退回成功
        400: 请求参数错误
        404: 任务不存在
        500: 服务器内部错误
    """
    try:
        approver_email = request.data.get('approver_email')
        approver_name = request.data.get('approver_name', '')
        comment = request.data.get('comment', '')
        return_to = request.data.get('return_to', 'applicant')
        
        if not approver_email:
            return Response({
                'success': False,
                'error': '缺少必填字段: approver_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 从 task_id 中提取 leave_request_id
        if task_id.startswith('task_'):
            leave_request_id = int(task_id.replace('task_', ''))
        else:
            leave_request_id = int(task_id)
        
        # 获取请假申请
        try:
            leave_request = LeaveRequest.objects.get(id=leave_request_id)
        except LeaveRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': '任务不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 使用 ApprovalService 处理退回
        approval_service = ApprovalService()
        result = approval_service.return_task(
            leave_request_id=leave_request_id,
            approver_email=approver_email,
            approver_name=approver_name,
            comment=comment,
            return_to=return_to
        )
        
        if result['success']:
            logger.info(f"退回任务成功: 任务 {task_id}, 审批人 {approver_email}")
            return Response({
                'success': True,
                'message': '退回成功',
                'leave_request': LeaveRequestSerializer(leave_request).data
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', '退回失败')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except ValueError:
        return Response({
            'success': False,
            'error': '无效的任务ID'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"退回任务失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def add_sign_task(request, task_id):
    """
    加签审批任务（添加额外审批人）
    
    POST /api/approval-tasks/{task_id}/add-sign/
    
    请求体：
        {
            "approver_email": "approver@test.com",
            "approver_name": "审批人",
            "add_sign_to_email": "new_approver@test.com",
            "add_sign_to_name": "新审批人",
            "comment": "需要额外审批"
        }
    
    HTTP 状态码:
        200: 加签成功
        400: 请求参数错误
        404: 任务不存在
        500: 服务器内部错误
    """
    try:
        approver_email = request.data.get('approver_email')
        approver_name = request.data.get('approver_name', '')
        add_sign_to_email = request.data.get('add_sign_to_email')
        add_sign_to_name = request.data.get('add_sign_to_name', '')
        comment = request.data.get('comment', '')
        
        if not approver_email or not add_sign_to_email:
            return Response({
                'success': False,
                'error': '缺少必填字段: approver_email, add_sign_to_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 从 task_id 中提取 leave_request_id
        if task_id.startswith('task_'):
            leave_request_id = int(task_id.replace('task_', ''))
        else:
            leave_request_id = int(task_id)
        
        # 获取请假申请
        try:
            leave_request = LeaveRequest.objects.get(id=leave_request_id)
        except LeaveRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': '任务不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 记录加签操作
        ApprovalHistory.objects.create(
            leave_request=leave_request,
            action='add_sign',
            operator_email=approver_email,
            operator_name=approver_name,
            operator_role='审批人',
            comment=f'加签给 {add_sign_to_name or add_sign_to_email}: {comment}'
        )
        
        # 创建新的审批任务（简化处理）
        ApprovalHistory.objects.create(
            leave_request=leave_request,
            action='submit',
            operator_email=add_sign_to_email,
            operator_name=add_sign_to_name,
            operator_role='审批人',
            comment='加签任务'
        )
        
        logger.info(f"加签任务成功: 任务 {task_id}, 加签给 {add_sign_to_email}")
        
        return Response({
            'success': True,
            'message': '加签成功',
            'leave_request': LeaveRequestSerializer(leave_request).data
        })
    
    except ValueError:
        return Response({
            'success': False,
            'error': '无效的任务ID'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"加签任务失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def transfer_task(request, task_id):
    """
    转签审批任务（转给其他审批人）
    
    POST /api/approval-tasks/{task_id}/transfer/
    
    请求体：
        {
            "approver_email": "approver@test.com",
            "approver_name": "审批人",
            "transfer_to_email": "new_approver@test.com",
            "transfer_to_name": "新审批人",
            "comment": "转给其他人审批"
        }
    
    HTTP 状态码:
        200: 转签成功
        400: 请求参数错误
        404: 任务不存在
        500: 服务器内部错误
    """
    try:
        approver_email = request.data.get('approver_email')
        approver_name = request.data.get('approver_name', '')
        transfer_to_email = request.data.get('transfer_to_email')
        transfer_to_name = request.data.get('transfer_to_name', '')
        comment = request.data.get('comment', '')
        
        if not approver_email or not transfer_to_email:
            return Response({
                'success': False,
                'error': '缺少必填字段: approver_email, transfer_to_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 从 task_id 中提取 leave_request_id
        if task_id.startswith('task_'):
            leave_request_id = int(task_id.replace('task_', ''))
        else:
            leave_request_id = int(task_id)
        
        # 获取请假申请
        try:
            leave_request = LeaveRequest.objects.get(id=leave_request_id)
        except LeaveRequest.DoesNotExist:
            return Response({
                'success': False,
                'error': '任务不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 记录转签操作
        ApprovalHistory.objects.create(
            leave_request=leave_request,
            action='transfer',
            operator_email=approver_email,
            operator_name=approver_name,
            operator_role='审批人',
            comment=f'转签给 {transfer_to_name or transfer_to_email}: {comment}'
        )
        
        # 创建新的审批任务（简化处理）
        ApprovalHistory.objects.create(
            leave_request=leave_request,
            action='submit',
            operator_email=transfer_to_email,
            operator_name=transfer_to_name,
            operator_role='审批人',
            comment='转签任务'
        )
        
        logger.info(f"转签任务成功: 任务 {task_id}, 转签给 {transfer_to_email}")
        
        return Response({
            'success': True,
            'message': '转签成功',
            'leave_request': LeaveRequestSerializer(leave_request).data
        })
    
    except ValueError:
        return Response({
            'success': False,
            'error': '无效的任务ID'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"转签任务失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
