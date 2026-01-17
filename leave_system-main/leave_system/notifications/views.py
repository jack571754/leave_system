"""
通知 API 视图
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Notification
from .serializers import NotificationSerializer
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
def get_my_notifications(request):
    """
    查询我的通知列表
    
    请求参数:
        user_email (str): 用户邮箱，必填
        is_read (str): 是否已读，可选（'true'/'false'）
        notification_type (str): 通知类型，可选
        limit (int): 返回数量限制，可选，默认50
        
    返回数据:
        success (bool): 操作是否成功
        notifications (list): 通知列表
        count (int): 通知数量
        unread_count (int): 未读数量
        
    HTTP 状态码:
        200: 查询成功
        400: 缺少必填参数
        500: 服务器内部错误
    """
    user_email = request.query_params.get('user_email')
    is_read_param = request.query_params.get('is_read')
    notification_type = request.query_params.get('notification_type')
    limit = int(request.query_params.get('limit', 50))
    
    if not user_email:
        return Response({
            'success': False,
            'error': '缺少 user_email 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 查询通知
        notifications = Notification.objects.filter(recipient_email=user_email)
        
        # 过滤已读/未读
        if is_read_param:
            is_read = is_read_param.lower() == 'true'
            notifications = notifications.filter(is_read=is_read)
        
        # 过滤通知类型
        if notification_type:
            notifications = notifications.filter(notification_type=notification_type)
        
        # 限制数量
        notifications = notifications.order_by('-created_at')[:limit]
        
        # 统计未读数量
        unread_count = Notification.objects.filter(
            recipient_email=user_email,
            is_read=False
        ).count()
        
        # 序列化
        serializer = NotificationSerializer(notifications, many=True)
        
        return Response({
            'success': True,
            'notifications': serializer.data,
            'count': len(serializer.data),
            'unread_count': unread_count
        })
    
    except Exception as e:
        logger.error(f"查询通知列表失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def mark_notification_read(request, notification_id):
    """
    标记通知已读
    
    请求参数:
        notification_id (int): 通知 ID，通过 URL 传递
        
    返回数据:
        success (bool): 操作是否成功
        
    HTTP 状态码:
        200: 标记成功
        404: 通知不存在
        500: 服务器内部错误
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            
            logger.info(f"标记通知已读: {notification_id}")
        
        return Response({
            'success': True,
            'message': '已标记为已读'
        })
    
    except Notification.DoesNotExist:
        return Response({
            'success': False,
            'error': '通知不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"标记通知已读失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def mark_all_read(request):
    """
    标记所有通知已读
    
    请求参数:
        user_email (str): 用户邮箱，必填
        
    返回数据:
        success (bool): 操作是否成功
        count (int): 标记数量
        
    HTTP 状态码:
        200: 标记成功
        400: 缺少必填参数
        500: 服务器内部错误
    """
    user_email = request.data.get('user_email')
    
    if not user_email:
        return Response({
            'success': False,
            'error': '缺少 user_email 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 更新所有未读通知
        count = Notification.objects.filter(
            recipient_email=user_email,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        logger.info(f"标记所有通知已读: {user_email}, 数量: {count}")
        
        return Response({
            'success': True,
            'count': count,
            'message': f'已标记 {count} 条通知为已读'
        })
    
    except Exception as e:
        logger.error(f"标记所有通知已读失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
