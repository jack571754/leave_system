"""
API 视图模块
提供请假审批系统的 REST API 接口
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import render
from .models import LeaveRequest
from .spiff_client import spiff_client
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)


def index(request):
    """
    前端页面视图
    返回静态 HTML 文件作为前端界面
    
    Args:
        request: HTTP 请求对象
        
    Returns:
        FileResponse: 返回 index.html 文件
    """
    from django.http import FileResponse
    import os
    from django.conf import settings
    
    # 构建静态文件路径
    static_file = os.path.join(settings.BASE_DIR, 'static', 'index.html')
    return FileResponse(open(static_file, 'rb'), content_type='text/html')


@api_view(['POST'])
def create_leave_request(request):
    """
    创建请假申请并启动审批流程
    
    这是整个审批流程的入口，完成以下操作：
    1. 创建请假申请记录（状态：draft）
    2. 调用 SpiffWorkflow 启动工作流
    3. 保存工作流实例 ID 到数据库
    4. 更新申请状态为 pending
    
    请求参数:
        user_email (str): 申请人邮箱，必填
        reason (str): 请假原因，必填
        leave_hours (int): 请假时长（小时），必填
        
    返回数据:
        success (bool): 操作是否成功
        leave_request_id (int): 请假申请 ID
        process_instance_id (str): 工作流实例 ID（UUID）
        status (str): 申请状态
        message (str): 提示信息
        
    HTTP 状态码:
        201: 创建成功
        400: 请求参数错误
        500: 服务器内部错误
        
    示例:
        POST /api/leave/create/
        {
            "user_email": "user@example.com",
            "reason": "生病请假",
            "leave_hours": 8
        }
    """
    try:
        # 从请求中获取必填参数
        user_email = request.data['user_email']
        reason = request.data['reason']
        leave_hours = request.data['leave_hours']
        
        # ========== 步骤 1: 创建请假申请记录 ==========
        # 初始状态为 draft（草稿），表示尚未提交审批
        leave_request = LeaveRequest.objects.create(
            user_email=user_email,
            reason=reason,
            leave_hours=leave_hours,
            status='draft'  # 初始状态
        )
        logger.info(f"创建请假申请: ID={leave_request.id}, 用户={user_email}")
        
        # ========== 步骤 2: 启动 SpiffWorkflow 工作流 ==========
        # process_model_id 格式: "组/模型"，对应 BPMN 文件路径
        # 例如: "admin/admin" 对应 process_models/admin/admin/admin.bpmn
        process_model_id = "admin/admin"
        
        # 准备工作流变量，这些变量会传递给 BPMN 流程
        # 可以在 BPMN 的脚本任务、条件表达式中使用这些变量
        variables = {
            "leave_request_id": leave_request.id,  # 请假申请 ID，用于关联业务数据
            "user_email": user_email,              # 申请人邮箱
            "reason": reason,                      # 请假原因
            "leave_hours": leave_hours,            # 请假时长
        }
        
        # 调用 SpiffWorkflow 客户端启动流程
        # 返回值包含工作流实例 ID 和状态
        result = spiff_client.start_process(process_model_id, variables)
        
        # 检查工作流是否启动成功
        if not result:
            return Response({
                'success': False,
                'error': '启动工作流失败，请检查 BPMN 文件和配置'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # ========== 步骤 3: 保存工作流实例 ID ==========
        # process_instance_id 是关联业务数据和工作流的关键字段
        # 通过这个 ID 可以查询工作流状态、完成任务等
        leave_request.process_instance_id = str(result.get('id'))
        leave_request.process_model_id = process_model_id
        leave_request.status = 'pending'  # 更新状态为待审批
        leave_request.submitted_at = timezone.now()  # 记录提交时间
        leave_request.save()
        
        logger.info(f"流程启动成功: process_instance_id={leave_request.process_instance_id}")
        
        # 返回成功响应
        return Response({
            'success': True,
            'leave_request_id': leave_request.id,
            'process_instance_id': leave_request.process_instance_id,
            'status': leave_request.status,
            'message': '请假申请已提交，流程已启动'
        }, status=status.HTTP_201_CREATED)
    
    except KeyError as e:
        # 捕获缺少必填字段的错误
        return Response({
            'success': False,
            'error': f'缺少必填字段: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # 捕获其他异常
        logger.error(f"创建请假申请失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_my_leave_requests(request):
    """
    查询我的请假申请列表
    
    根据用户邮箱查询该用户的所有请假申请记录
    
    请求参数:
        user_email (str): 用户邮箱，必填，通过 URL 参数传递
        
    返回数据:
        success (bool): 操作是否成功
        requests (list): 请假申请列表，每项包含：
            - id: 申请 ID
            - reason: 请假原因
            - leave_hours: 请假时长
            - status: 状态（draft/pending/approved/rejected）
            - status_display: 状态中文显示
            - process_instance_id: 工作流实例 ID
            - created_at: 创建时间
            - submitted_at: 提交时间
            
    HTTP 状态码:
        200: 查询成功
        400: 缺少必填参数
        
    示例:
        GET /api/leave/my-requests/?user_email=user@example.com
    """
    # 从 URL 参数中获取用户邮箱
    user_email = request.query_params.get('user_email')
    
    # 验证必填参数
    if not user_email:
        return Response({
            'success': False,
            'error': '缺少 user_email 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 查询该用户的所有请假申请
    # 结果按创建时间倒序排列（最新的在前面）
    requests_list = LeaveRequest.objects.filter(user_email=user_email)
    
    # 构建返回数据
    return Response({
        'success': True,
        'requests': [{
            'id': r.id,
            'reason': r.reason,
            'leave_hours': r.leave_hours,
            'status': r.status,  # 状态代码
            'status_display': r.get_status_display(),  # 状态中文显示
            'process_instance_id': r.process_instance_id,
            'created_at': r.created_at.isoformat(),  # ISO 格式时间字符串
            'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None,
        } for r in requests_list]
    })


@api_view(['GET'])
def get_pending_approvals(request):
    """
    查询待审批任务列表
    
    这个接口完成两个关键操作：
    1. 从 SpiffWorkflow 获取所有就绪的用户任务
    2. 根据 process_instance_id 关联对应的请假申请数据
    
    这是工作流引擎和业务数据的关联点
    
    请求参数:
        user_id (str): 审批人 ID，可选，默认为 'admin'
        
    返回数据:
        success (bool): 操作是否成功
        count (int): 待审批任务数量
        pending_approvals (list): 待审批任务列表，每项包含：
            - task_guid: 任务 GUID（用于完成任务）
            - task_name: 任务名称（来自 BPMN）
            - process_instance_id: 工作流实例 ID
            - leave_request: 关联的请假申请信息
                - id: 申请 ID
                - user_email: 申请人邮箱
                - reason: 请假原因
                - leave_hours: 请假时长
                - status: 状态
                - created_at: 创建时间
                
    HTTP 状态码:
        200: 查询成功
        500: 服务器内部错误
        
    示例:
        GET /api/leave/pending-approvals/?user_id=admin
    """
    # 获取审批人 ID，默认为 admin
    user_id = request.query_params.get('user_id', 'admin')
    
    try:
        # ========== 步骤 1: 从工作流引擎获取待办任务 ==========
        # 调用 SpiffWorkflow 客户端查询所有就绪的用户任务
        # 这些任务是工作流执行到用户任务节点时产生的
        tasks = spiff_client.get_user_tasks(user_id)
        
        # ========== 步骤 2: 关联业务数据 ==========
        # 遍历每个任务，根据 process_instance_id 查找对应的请假申请
        pending_approvals = []
        for task in tasks:
            # 获取工作流实例 ID
            process_instance_id = task['process_instance_id']
            
            # 根据 process_instance_id 查找对应的请假申请
            # 这是工作流和业务数据的关联点
            try:
                leave_request = LeaveRequest.objects.get(
                    process_instance_id=process_instance_id
                )
                
                # 组合工作流任务信息和业务数据
                pending_approvals.append({
                    # 工作流任务信息
                    'task_guid': task['task_guid'],  # 任务唯一标识，用于完成任务
                    'task_name': task['name'],        # 任务名称，来自 BPMN 定义
                    'process_instance_id': process_instance_id,
                    
                    # 业务数据
                    'leave_request': {
                        'id': leave_request.id,
                        'user_email': leave_request.user_email,
                        'reason': leave_request.reason,
                        'leave_hours': leave_request.leave_hours,
                        'status': leave_request.status,
                        'created_at': leave_request.created_at.isoformat(),
                    }
                })
            except LeaveRequest.DoesNotExist:
                # 如果找不到对应的请假申请，记录警告并跳过
                # 这种情况可能发生在数据不一致时
                logger.warning(f"找不到流程实例 {process_instance_id} 对应的请假申请")
                continue
        
        # 返回待审批任务列表
        return Response({
            'success': True,
            'count': len(pending_approvals),
            'pending_approvals': pending_approvals
        })
    
    except Exception as e:
        # 捕获异常并记录日志
        logger.error(f"查询待审批任务失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def approve_leave_request(request):
    """
    审批请假申请
    
    这个接口完成审批流程的核心操作：
    1. 完成工作流中的用户任务
    2. 更新业务数据的状态
    
    注意：即使工作流未完全结束，也会立即更新业务状态
    这是因为当前 BPMN 流程缺少结束事件，工作流会保持 running 状态
    
    请求参数:
        task_guid (str): 任务 GUID，必填
        process_instance_id (str): 工作流实例 ID，必填
        leave_request_id (int): 请假申请 ID，必填
        approved (bool): 是否批准，可选，默认 True
        comment (str): 审批意见，可选
        
    返回数据:
        success (bool): 操作是否成功
        message (str): 提示信息
        workflow_completed (bool): 工作流是否完全结束
        status (str): 更新后的申请状态
        
    HTTP 状态码:
        200: 审批成功
        400: 请求参数错误
        404: 请假申请不存在
        500: 服务器内部错误
        
    示例:
        POST /api/leave/approve/
        {
            "task_guid": "xxx-xxx-xxx",
            "process_instance_id": "yyy-yyy-yyy",
            "leave_request_id": 1,
            "approved": true,
            "comment": "同意请假"
        }
    """
    try:
        # ========== 获取请求参数 ==========
        task_guid = request.data['task_guid']  # 任务唯一标识
        process_instance_id = request.data['process_instance_id']  # 工作流实例 ID
        leave_request_id = request.data['leave_request_id']  # 请假申请 ID
        approved = request.data.get('approved', True)  # 是否批准，默认 True
        comment = request.data.get('comment', '')  # 审批意见
        
        # ========== 步骤 1: 获取请假申请记录 ==========
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        
        # ========== 步骤 2: 完成工作流任务 ==========
        # 调用 SpiffWorkflow 客户端完成任务
        # 传递审批结果和意见作为任务数据
        result = spiff_client.complete_task(
            process_instance_id,
            task_guid,
            {
                'approved': approved,  # 审批结果，可在 BPMN 的条件表达式中使用
                'comment': comment      # 审批意见
            }
        )
        
        # 检查任务是否完成成功
        if not result:
            return Response({
                'success': False,
                'error': '完成任务失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # ========== 步骤 3: 更新业务状态 ==========
        # 重要：无论工作流是否完全结束，都立即更新业务状态
        # 原因：当前 BPMN 流程缺少结束事件，工作流不会完全结束
        # 但业务上需要立即反映审批结果
        leave_request.status = 'approved' if approved else 'rejected'
        leave_request.approval_comment = comment
        leave_request.approved_at = timezone.now()  # 记录审批时间
        leave_request.save()
        
        logger.info(f"请假申请 {leave_request_id} 审批完成: {leave_request.status}")
        
        # 返回成功响应
        return Response({
            'success': True,
            'message': '审批提交成功',
            'workflow_completed': result.get('completed', False),  # 工作流是否完全结束
            'status': leave_request.status  # 更新后的状态
        })
    
    except KeyError as e:
        # 捕获缺少必填字段的错误
        return Response({
            'success': False,
            'error': f'缺少必填字段: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except LeaveRequest.DoesNotExist:
        # 捕获请假申请不存在的错误
        return Response({
            'success': False,
            'error': '请假申请不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # 捕获其他异常
        logger.error(f"审批请假申请失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
