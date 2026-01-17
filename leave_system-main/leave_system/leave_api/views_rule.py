"""
审批规则管理视图
实现审批规则的 CRUD 和管理功能
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ApprovalRule
from .serializers import ApprovalRuleSerializer
from .services.rule_service import ApprovalRuleService


class ApprovalRuleViewSet(viewsets.ModelViewSet):
    """
    审批规则视图集
    提供审批规则的 CRUD 操作
    """
    queryset = ApprovalRule.objects.all()
    serializer_class = ApprovalRuleSerializer
    
    def get_queryset(self):
        """获取查询集，支持过滤"""
        queryset = ApprovalRule.objects.all()
        
        # 按激活状态过滤
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # 按请假类型过滤
        leave_type = self.request.query_params.get('leave_type')
        if leave_type:
            queryset = queryset.filter(leave_type=leave_type)
        
        return queryset.order_by('-priority', '-created_at')
    
    @action(detail=True, methods=['patch'])
    def priority(self, request, pk=None):
        """
        调整规则优先级
        PATCH /api/approval-rules/{id}/priority/
        Body: {"priority": 10}
        """
        rule = self.get_object()
        new_priority = request.data.get('priority')
        
        if new_priority is None:
            return Response(
                {'error': '缺少 priority 参数'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_priority = int(new_priority)
        except (ValueError, TypeError):
            return Response(
                {'error': 'priority 必须是整数'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rule.priority = new_priority
        rule.save()
        
        serializer = self.get_serializer(rule)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def toggle(self, request, pk=None):
        """
        启用/禁用规则
        PATCH /api/approval-rules/{id}/toggle/
        Body: {"is_active": true}
        """
        rule = self.get_object()
        is_active = request.data.get('is_active')
        
        if is_active is None:
            return Response(
                {'error': '缺少 is_active 参数'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rule.is_active = bool(is_active)
        rule.save()
        
        serializer = self.get_serializer(rule)
        return Response(serializer.data)


@api_view(['POST'])
def simulate_rule(request):
    """
    模拟规则匹配
    POST /api/approval-rules/simulate/
    Body: {
        "leave_type": "annual",
        "duration": 3.0,
        "department_name": "技术部"
    }
    """
    leave_type = request.data.get('leave_type')
    duration = request.data.get('duration')
    department_name = request.data.get('department_name')
    
    # 转换 duration 为 float
    if duration is not None:
        try:
            duration = float(duration)
        except (ValueError, TypeError):
            return Response(
                {'error': 'duration 必须是数字'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # 调用规则服务进行模拟
    rule_service = ApprovalRuleService()
    result = rule_service.simulate_rule_matching(
        leave_type=leave_type,
        duration=duration,
        department_name=department_name
    )
    
    return Response(result)
