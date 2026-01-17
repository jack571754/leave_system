"""
API 视图模块 V2 - 使用服务层
提供请假审批系统的 REST API 接口
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import render
from .models import LeaveRequest
from .services.approval_service import ApprovalService
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)

# 初始化审批服务
approval_service = ApprovalService()


def index(request):
    """
    API 根路径视图
    返回 API 信息
    
    Args:
        request: HTTP 请求对象
        
    Returns:
        JsonResponse: 返回 API 信息
    """
    from django.http import JsonResponse
    
    return JsonResponse({
        'message': '欢迎使用请假审批系统 API',
        'version': '2.0',
        'endpoints': {
            'create_leave': '/api/leave/create/',
            'my_requests': '/api/leave/my-requests/',
            'pending_approvals': '/api/leave/pending-approvals/',
            'approve': '/api/leave/approve/',
            'reject': '/api/leave/reject/',
        }
    })


@api_view(['POST'])
def create_leave_request(request):
    """
    创建请假申请并启动审批流程
    
    使用 ApprovalService 处理业务逻辑
    
    请求参数:
        user_email (str): 申请人邮箱，必填
        staff_full_name (str): 申请人姓名，可选
        staff_dept (str): 申请人部门，可选
        reason (str): 请假原因，必填
        leave_hours (int): 请假时长（小时），必填
        leave_type (str): 请假类型，可选，默认 'annual'
        start_date (str): 开始日期，可选，格式 YYYY-MM-DD
        end_date (str): 结束日期，可选，格式 YYYY-MM-DD
        duration (float): 请假天数，可选
        
    返回数据:
        success (bool): 操作是否成功
        leave_request_id (int): 请假申请 ID
        process_instance_id (str): 工作流实例 ID（UUID）
        status (str): 申请状态
        workflow_spec_name (str): 使用的工作流规范名称
        message (str): 提示信息
        
    HTTP 状态码:
        201: 创建成功
        400: 请求参数错误
        500: 服务器内部错误
        
    示例:
        POST /api/leave/create/
        {
            "user_email": "user@example.com",
            "staff_full_name": "张三",
            "staff_dept": "技术部",
            "reason": "生病请假",
            "leave_hours": 8,
            "leave_type": "sick",
            "start_date": "2026-02-01",
            "end_date": "2026-02-01",
            "duration": 1.0
        }
    """
    try:
        # 从请求中获取参数
        user_email = request.data['user_email']
        reason = request.data['reason']
        leave_hours = request.data['leave_hours']
        
        # 可选参数
        staff_full_name = request.data.get('staff_full_name', '')
        staff_dept = request.data.get('staff_dept', '')
        leave_type = request.data.get('leave_type', 'annual')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        duration = request.data.get('duration')
        
        # 创建请假申请记录（草稿状态）
        leave_request = LeaveRequest.objects.create(
            user_email=user_email,
            staff_full_name=staff_full_name,
            staff_dept=staff_dept,
            reason=reason,
            leave_hours=leave_hours,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            duration=duration,
            status='draft'
        )
        logger.info(f"创建请假申请: ID={leave_request.id}, 用户={user_email}")
        
        # 使用 ApprovalService 提交申请
        leave_request = approval_service.submit_leave_request(leave_request)
        
        logger.info(f"流程启动成功: process_instance_id={leave_request.process_instance_id}")
        
        # 返回成功响应
        return Response({
            'success': True,
            'leave_request_id': leave_request.id,
            'process_instance_id': leave_request.process_instance_id,
            'status': leave_request.status,
            'workflow_spec_name': leave_request.workflow_spec_name,
            'message': '请假申请已提交，流程已启动'
        }, status=status.HTTP_201_CREATED)
    
    except KeyError as e:
        return Response({
            'success': False,
            'error': f'缺少必填字段: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
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
        requests (list): 请假申请列表
            
    HTTP 状态码:
        200: 查询成功
        400: 缺少必填参数
        
    示例:
        GET /api/leave/my-requests/?user_email=user@example.com
    """
    user_email = request.query_params.get('user_email')
    
    if not user_email:
        return Response({
            'success': False,
            'error': '缺少 user_email 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    requests_list = LeaveRequest.objects.filter(user_email=user_email).order_by('-created_at')
    
    return Response({
        'success': True,
        'requests': [{
            'id': r.id,
            'user_email': r.user_email,
            'staff_full_name': r.staff_full_name,
            'staff_dept': r.staff_dept,
            'reason': r.reason,
            'leave_hours': r.leave_hours,
            'leave_type': r.leave_type,
            'duration': float(r.duration) if r.duration else None,
            'start_date': r.start_date.isoformat() if r.start_date else None,
            'end_date': r.end_date.isoformat() if r.end_date else None,
            'status': r.status,
            'status_display': r.get_status_display(),
            'process_instance_id': r.process_instance_id,
            'workflow_spec_name': r.workflow_spec_name,
            'created_at': r.created_at.isoformat(),
            'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None,
            'completed_at': r.completed_at.isoformat() if r.completed_at else None,
        } for r in requests_list]
    })


@api_view(['GET'])
def get_pending_approvals(request):
    """
    查询待审批任务列表
    
    使用 ApprovalService 获取用户的待办任务
    
    请求参数:
        user_email (str): 审批人邮箱，必填
        
    返回数据:
        success (bool): 操作是否成功
        count (int): 待审批任务数量
        tasks (list): 待审批任务列表
                
    HTTP 状态码:
        200: 查询成功
        400: 缺少必填参数
        500: 服务器内部错误
        
    示例:
        GET /api/leave/pending-approvals/?user_email=manager@example.com
    """
    user_email = request.query_params.get('user_email')
    
    if not user_email:
        return Response({
            'success': False,
            'error': '缺少 user_email 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 使用 ApprovalService 获取待办任务
        tasks = approval_service.get_user_tasks(user_email)
        
        return Response({
            'success': True,
            'count': len(tasks),
            'tasks': tasks
        })
    
    except Exception as e:
        logger.error(f"查询待审批任务失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def approve_leave_request(request):
    """
    批准请假申请
    
    使用 ApprovalService 处理审批逻辑
    
    请求参数:
        leave_request_id (int): 请假申请 ID，必填
        task_id (str): 任务 ID，必填
        approver_email (str): 审批人邮箱，必填
        approver_name (str): 审批人姓名，可选
        comment (str): 审批意见，可选
        
    返回数据:
        success (bool): 操作是否成功
        message (str): 提示信息
        status (str): 更新后的申请状态
        completed (bool): 流程是否完成
        
    HTTP 状态码:
        200: 审批成功
        400: 请求参数错误
        404: 请假申请不存在
        500: 服务器内部错误
        
    示例:
        POST /api/leave/approve/
        {
            "leave_request_id": 1,
            "task_id": "task-123",
            "approver_email": "manager@example.com",
            "approver_name": "张经理",
            "comment": "同意请假"
        }
    """
    try:
        leave_request_id = request.data['leave_request_id']
        task_id = request.data['task_id']
        approver_email = request.data['approver_email']
        approver_name = request.data.get('approver_name', '')
        comment = request.data.get('comment', '')
        
        # 获取请假申请
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        
        # 使用 ApprovalService 批准任务
        leave_request = approval_service.approve_task(
            leave_request,
            task_id,
            approver_email,
            approver_name,
            comment
        )
        
        logger.info(f"请假申请 {leave_request_id} 批准成功")
        
        return Response({
            'success': True,
            'message': '审批提交成功',
            'status': leave_request.status,
            'completed': leave_request.completed_at is not None
        })
    
    except KeyError as e:
        return Response({
            'success': False,
            'error': f'缺少必填字段: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except LeaveRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': '请假申请不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"批准请假申请失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def reject_leave_request(request):
    """
    拒绝请假申请
    
    使用 ApprovalService 处理拒绝逻辑
    
    请求参数:
        leave_request_id (int): 请假申请 ID，必填
        task_id (str): 任务 ID，必填
        approver_email (str): 审批人邮箱，必填
        approver_name (str): 审批人姓名，可选
        comment (str): 拒绝理由，必填
        
    返回数据:
        success (bool): 操作是否成功
        message (str): 提示信息
        status (str): 更新后的申请状态
        
    HTTP 状态码:
        200: 拒绝成功
        400: 请求参数错误
        404: 请假申请不存在
        500: 服务器内部错误
        
    示例:
        POST /api/leave/reject/
        {
            "leave_request_id": 1,
            "task_id": "task-123",
            "approver_email": "manager@example.com",
            "approver_name": "张经理",
            "comment": "理由不充分"
        }
    """
    try:
        leave_request_id = request.data['leave_request_id']
        task_id = request.data['task_id']
        approver_email = request.data['approver_email']
        approver_name = request.data.get('approver_name', '')
        comment = request.data.get('comment', '')
        
        if not comment:
            return Response({
                'success': False,
                'error': '拒绝理由不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取请假申请
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        
        # 使用 ApprovalService 拒绝任务
        leave_request = approval_service.reject_task(
            leave_request,
            task_id,
            approver_email,
            approver_name,
            comment
        )
        
        logger.info(f"请假申请 {leave_request_id} 已拒绝")
        
        return Response({
            'success': True,
            'message': '已拒绝申请',
            'status': leave_request.status
        })
    
    except KeyError as e:
        return Response({
            'success': False,
            'error': f'缺少必填字段: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except LeaveRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': '请假申请不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"拒绝请假申请失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def return_leave_request(request):
    """
    退回请假申请
    
    使用 ApprovalService 处理退回逻辑
    
    请求参数:
        leave_request_id (int): 请假申请 ID，必填
        task_id (str): 任务 ID，必填
        approver_email (str): 审批人邮箱，必填
        approver_name (str): 审批人姓名，可选
        return_to (str): 退回目标，可选，默认 'applicant'（'applicant' 或 'previous'）
        comment (str): 退回理由，必填
        
    返回数据:
        success (bool): 操作是否成功
        message (str): 提示信息
        status (str): 更新后的申请状态
        
    HTTP 状态码:
        200: 退回成功
        400: 请求参数错误
        404: 请假申请不存在
        500: 服务器内部错误
        
    示例:
        POST /api/leave/return/
        {
            "leave_request_id": 1,
            "task_id": "task-123",
            "approver_email": "manager@example.com",
            "approver_name": "张经理",
            "return_to": "applicant",
            "comment": "请补充详细理由"
        }
    """
    try:
        leave_request_id = request.data['leave_request_id']
        task_id = request.data['task_id']
        approver_email = request.data['approver_email']
        approver_name = request.data.get('approver_name', '')
        return_to = request.data.get('return_to', 'applicant')
        comment = request.data.get('comment', '')
        
        if not comment:
            return Response({
                'success': False,
                'error': '退回理由不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取请假申请
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        
        # 使用 ApprovalService 退回任务
        leave_request = approval_service.return_task(
            leave_request,
            task_id,
            approver_email,
            approver_name,
            return_to,
            comment
        )
        
        logger.info(f"请假申请 {leave_request_id} 已退回")
        
        return Response({
            'success': True,
            'message': '已退回申请',
            'status': leave_request.status
        })
    
    except KeyError as e:
        return Response({
            'success': False,
            'error': f'缺少必填字段: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except LeaveRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': '请假申请不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"退回请假申请失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_approval_history(request, leave_request_id):
    """
    查询审批历史
    
    请求参数:
        leave_request_id (int): 请假申请 ID，通过 URL 传递
        
    返回数据:
        success (bool): 操作是否成功
        leave_request (dict): 请假申请基本信息
        history (list): 审批历史列表
        count (int): 历史记录数量
        
    HTTP 状态码:
        200: 查询成功
        404: 请假申请不存在
        500: 服务器内部错误
        
    示例:
        GET /api/leave/requests/1/history/
    """
    try:
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        history = leave_request.history.all().order_by('created_at')
        
        return Response({
            'success': True,
            'leave_request': {
                'id': leave_request.id,
                'user_email': leave_request.user_email,
                'staff_full_name': leave_request.staff_full_name,
                'staff_dept': leave_request.staff_dept,
                'reason': leave_request.reason,
                'leave_hours': leave_request.leave_hours,
                'leave_type': leave_request.leave_type,
                'status': leave_request.status,
                'status_display': leave_request.get_status_display(),
                'created_at': leave_request.created_at.isoformat(),
                'submitted_at': leave_request.submitted_at.isoformat() if leave_request.submitted_at else None,
                'completed_at': leave_request.completed_at.isoformat() if leave_request.completed_at else None,
            },
            'history': [{
                'id': h.id,
                'action': h.action,
                'action_display': h.get_action_display(),
                'operator_email': h.operator_email,
                'operator_name': h.operator_name,
                'operator_role': h.operator_role,
                'comment': h.comment,
                'is_proxy': h.is_proxy,
                'proxy_for_email': h.proxy_for_email,
                'task_id': h.task_id,
                'task_name': h.task_name,
                'created_at': h.created_at.isoformat()
            } for h in history],
            'count': history.count()
        })
    
    except LeaveRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': '请假申请不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"查询审批历史失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
def get_approval_timeline(request, leave_request_id):
    """
    获取审批轨迹可视化数据
    
    提供适合前端时间轴展示的审批历史数据，包含更丰富的展示信息
    
    请求参数:
        leave_request_id (int): 请假申请 ID，通过 URL 路径传递
        
    返回数据:
        success (bool): 操作是否成功
        timeline (list): 时间轴数据列表，每项包含：
            - timestamp: 时间戳（ISO 格式）
            - action: 操作类型
            - action_display: 操作类型中文显示
            - operator: 操作人信息
                - email: 邮箱
                - name: 姓名
                - role: 角色
            - comment: 操作意见
            - is_proxy: 是否代理操作
            - proxy_info: 代理信息（如果是代理操作）
            - task_name: 任务名称
            - icon: 图标类型（用于前端展示）
            - color: 颜色类型（用于前端展示）
        
    HTTP 状态码:
        200: 查询成功
        404: 请假申请不存在
        500: 服务器内部错误
        
    示例:
        GET /api/leave/requests/1/timeline/
    """
    try:
        # 查询请假申请
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        
        # 查询审批历史
        history = leave_request.history.all().order_by('created_at')
        
        # 构建时间轴数据
        timeline = []
        for record in history:
            # 根据操作类型确定图标和颜色
            icon_map = {
                'submit': 'file-text',
                'approve': 'check-circle',
                'reject': 'x-circle',
                'return': 'corner-up-left',
                'add_sign': 'user-plus',
                'transfer': 'arrow-right',
                'cancel': 'slash'
            }
            
            color_map = {
                'submit': 'blue',
                'approve': 'green',
                'reject': 'red',
                'return': 'orange',
                'add_sign': 'purple',
                'transfer': 'cyan',
                'cancel': 'gray'
            }
            
            item = {
                'timestamp': record.created_at.isoformat(),
                'action': record.action,
                'action_display': record.get_action_display(),
                'operator': {
                    'email': record.operator_email,
                    'name': record.operator_name,
                    'role': record.operator_role
                },
                'comment': record.comment,
                'is_proxy': record.is_proxy,
                'task_name': record.task_name,
                'icon': icon_map.get(record.action, 'circle'),
                'color': color_map.get(record.action, 'gray')
            }
            
            # 如果是代理操作，添加代理信息
            if record.is_proxy and record.proxy_for_email:
                item['proxy_info'] = {
                    'proxy_for_email': record.proxy_for_email,
                    'message': f'{record.operator_name} 代理 {record.proxy_for_email} 进行操作'
                }
            
            timeline.append(item)
        
        return Response({
            'success': True,
            'timeline': timeline
        })
        
    except LeaveRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': '请假申请不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"获取审批轨迹失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
def add_cc_record(request, leave_request_id):
    """
    添加抄送人
    
    请求参数:
        leave_request_id (int): 请假申请 ID，通过 URL 传递
        cc_to_email (str): 抄送人邮箱，必填
        cc_by_email (str): 抄送发起人邮箱，必填
        
    返回数据:
        success (bool): 操作是否成功
        cc_record (dict): 抄送记录信息
        
    HTTP 状态码:
        201: 创建成功
        400: 请求参数错误
        404: 请假申请不存在
        500: 服务器内部错误
    """
    from .models import CCRecord
    
    try:
        cc_to_email = request.data['cc_to_email']
        cc_by_email = request.data['cc_by_email']
        
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        
        # 检查是否已经抄送过
        existing = CCRecord.objects.filter(
            leave_request=leave_request,
            cc_to_email=cc_to_email
        ).first()
        
        if existing:
            return Response({
                'success': False,
                'error': '该用户已在抄送列表中'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建抄送记录
        cc_record = CCRecord.objects.create(
            leave_request=leave_request,
            cc_to_email=cc_to_email,
            cc_by_email=cc_by_email
        )
        
        logger.info(f"添加抄送: 申请 {leave_request_id}, 抄送给 {cc_to_email}")
        
        return Response({
            'success': True,
            'cc_record': {
                'id': cc_record.id,
                'cc_to_email': cc_record.cc_to_email,
                'cc_by_email': cc_record.cc_by_email,
                'is_read': cc_record.is_read,
                'created_at': cc_record.created_at.isoformat()
            }
        }, status=status.HTTP_201_CREATED)
    
    except KeyError as e:
        return Response({
            'success': False,
            'error': f'缺少必填字段: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except LeaveRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': '请假申请不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"添加抄送失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_cc_records(request, leave_request_id):
    """
    查询抄送记录
    
    请求参数:
        leave_request_id (int): 请假申请 ID，通过 URL 传递
        
    返回数据:
        success (bool): 操作是否成功
        cc_records (list): 抄送记录列表
        count (int): 抄送记录数量
        
    HTTP 状态码:
        200: 查询成功
        404: 请假申请不存在
        500: 服务器内部错误
    """
    from .models import CCRecord
    
    try:
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        cc_records = CCRecord.objects.filter(leave_request=leave_request).order_by('-created_at')
        
        return Response({
            'success': True,
            'cc_records': [{
                'id': cc.id,
                'cc_to_email': cc.cc_to_email,
                'cc_by_email': cc.cc_by_email,
                'is_read': cc.is_read,
                'created_at': cc.created_at.isoformat(),
                'read_at': cc.read_at.isoformat() if cc.read_at else None
            } for cc in cc_records],
            'count': cc_records.count()
        })
    
    except LeaveRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': '请假申请不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"查询抄送记录失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_my_cc_requests(request):
    """
    查询我的抄送列表
    
    请求参数:
        user_email (str): 用户邮箱，必填
        is_read (str): 是否已读，可选（'true'/'false'）
        
    返回数据:
        success (bool): 操作是否成功
        cc_requests (list): 抄送列表
        count (int): 抄送数量
        unread_count (int): 未读数量
        
    HTTP 状态码:
        200: 查询成功
        400: 缺少必填参数
        500: 服务器内部错误
    """
    from .models import CCRecord
    
    user_email = request.query_params.get('user_email')
    is_read_param = request.query_params.get('is_read')
    
    if not user_email:
        return Response({
            'success': False,
            'error': '缺少 user_email 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 查询抄送记录
        cc_records = CCRecord.objects.filter(cc_to_email=user_email)
        
        # 过滤已读/未读
        if is_read_param:
            is_read = is_read_param.lower() == 'true'
            cc_records = cc_records.filter(is_read=is_read)
        
        cc_records = cc_records.select_related('leave_request').order_by('-created_at')
        
        # 统计未读数量
        unread_count = CCRecord.objects.filter(
            cc_to_email=user_email,
            is_read=False
        ).count()
        
        return Response({
            'success': True,
            'cc_requests': [{
                'id': cc.id,
                'leave_request': {
                    'id': cc.leave_request.id,
                    'user_email': cc.leave_request.user_email,
                    'staff_full_name': cc.leave_request.staff_full_name,
                    'staff_dept': cc.leave_request.staff_dept,
                    'reason': cc.leave_request.reason,
                    'leave_hours': cc.leave_request.leave_hours,
                    'leave_type': cc.leave_request.leave_type,
                    'status': cc.leave_request.status,
                    'status_display': cc.leave_request.get_status_display(),
                    'created_at': cc.leave_request.created_at.isoformat()
                },
                'cc_by_email': cc.cc_by_email,
                'is_read': cc.is_read,
                'created_at': cc.created_at.isoformat(),
                'read_at': cc.read_at.isoformat() if cc.read_at else None
            } for cc in cc_records],
            'count': cc_records.count(),
            'unread_count': unread_count
        })
    
    except Exception as e:
        logger.error(f"查询抄送列表失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def mark_cc_read(request, cc_record_id):
    """
    标记抄送已读
    
    请求参数:
        cc_record_id (int): 抄送记录 ID，通过 URL 传递
        
    返回数据:
        success (bool): 操作是否成功
        
    HTTP 状态码:
        200: 标记成功
        404: 抄送记录不存在
        500: 服务器内部错误
    """
    from .models import CCRecord
    
    try:
        cc_record = CCRecord.objects.get(id=cc_record_id)
        
        if not cc_record.is_read:
            cc_record.is_read = True
            cc_record.read_at = timezone.now()
            cc_record.save()
            
            logger.info(f"标记抄送已读: {cc_record_id}")
        
        return Response({
            'success': True,
            'message': '已标记为已读'
        })
    
    except CCRecord.DoesNotExist:
        return Response({
            'success': False,
            'error': '抄送记录不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"标记抄送已读失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
def urge_approval_task(request, leave_request_id):
    """
    催办审批任务
    
    请求参数:
        leave_request_id (int): 请假申请 ID，通过 URL 传递
        urge_by_email (str): 催办人邮箱，必填
        urge_by_name (str): 催办人姓名，可选
        message (str): 催办消息，可选
        
    返回数据:
        success (bool): 操作是否成功
        message (str): 提示信息
        
    HTTP 状态码:
        200: 催办成功
        400: 请求参数错误
        404: 请假申请不存在
        500: 服务器内部错误
    """
    try:
        urge_by_email = request.data['urge_by_email']
        urge_by_name = request.data.get('urge_by_name', '')
        message = request.data.get('message', '')
        
        # 验证申请存在
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
        
        # 验证申请状态
        if leave_request.status != 'pending':
            return Response({
                'success': False,
                'error': '只能催办待审批的申请'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 异步发送催办通知
        from leave_api.tasks import send_urge_notification
        send_urge_notification.delay(
            leave_request_id=leave_request_id,
            urge_by_email=urge_by_email,
            urge_by_name=urge_by_name,
            message=message
        )
        
        logger.info(f"催办任务: 申请 {leave_request_id}, 催办人 {urge_by_email}")
        
        return Response({
            'success': True,
            'message': '催办通知已发送'
        })
    
    except KeyError as e:
        return Response({
            'success': False,
            'error': f'缺少必填字段: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except LeaveRequest.DoesNotExist:
        return Response({
            'success': False,
            'error': '请假申请不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"催办任务失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
