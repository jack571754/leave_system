"""
代理设置 API 视图
处理代理设置相关的 REST API 请求
"""

import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import ApprovalProxy
from .serializers import ApprovalProxySerializer
from .services.proxy_service import ProxyService

logger = logging.getLogger(__name__)


@api_view(['POST'])
def create_proxy_setting(request):
    """
    创建代理设置
    
    POST /api/proxy-settings/
    
    请求体：
        {
            "principal_email": "user@test.com",
            "proxy_email": "proxy@test.com",
            "start_date": "2026-01-20T00:00:00Z",
            "end_date": "2026-01-25T23:59:59Z"
        }
    
    返回：
        {
            "success": true,
            "proxy_setting": {...}
        }
    
    HTTP 状态码:
        201: 创建成功
        400: 请求参数错误
        500: 服务器内部错误
    """
    try:
        serializer = ApprovalProxySerializer(data=request.data)
        
        if serializer.is_valid():
            proxy_setting = serializer.save()
            
            logger.info(f"创建代理设置: {proxy_setting.principal_email} -> {proxy_setting.proxy_email}")
            
            return Response({
                'success': True,
                'proxy_setting': ApprovalProxySerializer(proxy_setting).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"创建代理设置失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_my_proxy_settings(request):
    """
    查询我的代理设置
    
    GET /api/proxy-settings/my-settings/?user_email=xxx
    
    查询参数：
        user_email: 用户邮箱（必填）
        is_active: 是否只查询激活的代理（可选，true/false）
    
    返回：
        {
            "success": true,
            "proxy_settings": [...]
        }
    
    HTTP 状态码:
        200: 查询成功
        400: 请求参数错误
        500: 服务器内部错误
    """
    try:
        user_email = request.query_params.get('user_email')
        is_active_param = request.query_params.get('is_active')
        
        if not user_email:
            return Response({
                'success': False,
                'error': '缺少必填参数: user_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 查询代理设置
        proxy_settings = ApprovalProxy.objects.filter(principal_email=user_email)
        
        # 过滤激活状态
        if is_active_param:
            is_active = is_active_param.lower() == 'true'
            proxy_settings = proxy_settings.filter(is_active=is_active)
        
        proxy_settings = proxy_settings.order_by('-created_at')
        
        logger.info(f"查询代理设置: 用户 {user_email}, 数量 {proxy_settings.count()}")
        
        return Response({
            'success': True,
            'proxy_settings': ApprovalProxySerializer(proxy_settings, many=True).data
        })
    
    except Exception as e:
        logger.error(f"查询代理设置失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_proxy_setting(request, proxy_id):
    """
    取消代理设置
    
    DELETE /api/proxy-settings/{id}/
    
    HTTP 状态码:
        200: 取消成功
        404: 代理设置不存在
        500: 服务器内部错误
    """
    try:
        try:
            proxy_setting = ApprovalProxy.objects.get(id=proxy_id)
        except ApprovalProxy.DoesNotExist:
            return Response({
                'success': False,
                'error': '代理设置不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 标记为不激活而不是删除
        proxy_setting.is_active = False
        proxy_setting.save()
        
        logger.info(f"取消代理设置: ID {proxy_id}")
        
        return Response({
            'success': True,
            'message': '代理设置已取消'
        })
    
    except Exception as e:
        logger.error(f"取消代理设置失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_effective_approver(request, employee_email):
    """
    查询有效审批人
    
    GET /api/employees/{email}/effective-approver/
    
    查询参数：
        check_time: 检查时间（可选，ISO格式，默认为当前时间）
    
    返回：
        {
            "success": true,
            "original_approver": "user@test.com",
            "effective_approver": "proxy@test.com",
            "is_proxy": true,
            "proxy_info": {...}
        }
    
    HTTP 状态码:
        200: 查询成功
        500: 服务器内部错误
    """
    try:
        check_time_param = request.query_params.get('check_time')
        
        # 解析检查时间
        if check_time_param:
            from django.utils.dateparse import parse_datetime
            check_time = parse_datetime(check_time_param)
            if not check_time:
                return Response({
                    'success': False,
                    'error': '无效的时间格式'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            check_time = timezone.now()
        
        # 使用 ProxyService 查询有效审批人
        proxy_service = ProxyService()
        result = proxy_service.get_effective_approver(
            approver_email=employee_email
        )
        
        logger.info(f"查询有效审批人: {employee_email} -> {result['effective_approver']}")
        
        return Response({
            'success': True,
            'original_approver': employee_email,
            'effective_approver': result['effective_approver'],
            'is_proxy': result['is_proxy'],
            'proxy_info': result.get('proxy_info')
        })
    
    except Exception as e:
        logger.error(f"查询有效审批人失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
def update_proxy_setting(request, proxy_id):
    """
    更新代理设置
    
    PUT /api/proxy-settings/{id}/
    
    请求体：
        {
            "start_date": "2026-01-20T00:00:00Z",
            "end_date": "2026-01-25T23:59:59Z",
            "is_active": true
        }
    
    HTTP 状态码:
        200: 更新成功
        400: 请求参数错误
        404: 代理设置不存在
        500: 服务器内部错误
    """
    try:
        try:
            proxy_setting = ApprovalProxy.objects.get(id=proxy_id)
        except ApprovalProxy.DoesNotExist:
            return Response({
                'success': False,
                'error': '代理设置不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ApprovalProxySerializer(proxy_setting, data=request.data, partial=True)
        
        if serializer.is_valid():
            proxy_setting = serializer.save()
            
            logger.info(f"更新代理设置: ID {proxy_id}")
            
            return Response({
                'success': True,
                'proxy_setting': ApprovalProxySerializer(proxy_setting).data
            })
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"更新代理设置失败: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
