"""
审批 API 序列化器
定义审批相关的数据序列化和反序列化
"""

from rest_framework import serializers
from .models import ApprovalHistory, LeaveRequest, CCRecord, ApprovalProxy, ApprovalRule


class ApprovalHistorySerializer(serializers.ModelSerializer):
    """审批历史序列化器"""
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = ApprovalHistory
        fields = [
            'id',
            'action',
            'action_display',
            'operator_email',
            'operator_name',
            'operator_role',
            'comment',
            'is_proxy',
            'proxy_for_email',
            'task_id',
            'task_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'action_display']


class LeaveRequestSerializer(serializers.ModelSerializer):
    """请假申请序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id',
            'user_email',
            'staff_full_name',
            'staff_dept',
            'reason',
            'leave_hours',
            'leave_type',
            'leave_type_display',
            'start_date',
            'end_date',
            'duration',
            'status',
            'status_display',
            'process_instance_id',
            'workflow_spec_name',
            'created_at',
            'submitted_at',
            'completed_at'
        ]
        read_only_fields = [
            'id',
            'status',
            'status_display',
            'leave_type_display',
            'process_instance_id',
            'workflow_spec_name',
            'created_at',
            'submitted_at',
            'completed_at'
        ]


class CCRecordSerializer(serializers.ModelSerializer):
    """抄送记录序列化器"""
    leave_request_info = serializers.SerializerMethodField()
    
    class Meta:
        model = CCRecord
        fields = [
            'id',
            'leave_request',
            'leave_request_info',
            'cc_to_email',
            'cc_by_email',
            'is_read',
            'created_at',
            'read_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at', 'leave_request_info']
    
    def get_leave_request_info(self, obj):
        """获取请假申请基本信息"""
        return {
            'id': obj.leave_request.id,
            'user_email': obj.leave_request.user_email,
            'staff_full_name': obj.leave_request.staff_full_name,
            'staff_dept': obj.leave_request.staff_dept,
            'reason': obj.leave_request.reason,
            'status': obj.leave_request.status,
            'status_display': obj.leave_request.get_status_display()
        }


class ApprovalTaskSerializer(serializers.Serializer):
    """审批任务序列化器"""
    task_id = serializers.CharField(help_text='任务ID')
    task_name = serializers.CharField(help_text='任务名称')
    leave_request_id = serializers.IntegerField(help_text='请假申请ID')
    leave_request = LeaveRequestSerializer(read_only=True, help_text='请假申请详情')
    assignee_email = serializers.EmailField(help_text='审批人邮箱')
    created_at = serializers.DateTimeField(help_text='任务创建时间')
    
    class Meta:
        fields = [
            'task_id',
            'task_name',
            'leave_request_id',
            'leave_request',
            'assignee_email',
            'created_at'
        ]



class ApprovalProxySerializer(serializers.ModelSerializer):
    """代理设置序列化器"""
    from .models import ApprovalProxy
    
    class Meta:
        model = ApprovalProxy
        fields = [
            'id',
            'principal_email',
            'proxy_email',
            'start_date',
            'end_date',
            'is_active',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """验证代理设置"""
        # 获取实例（如果是更新操作）
        instance = getattr(self, 'instance', None)
        
        # 验证时间范围
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 如果是部分更新，从实例获取缺失的字段
        if instance:
            if start_date is None:
                start_date = instance.start_date
            if end_date is None:
                end_date = instance.end_date
        
        # 只有当两个日期都存在时才验证
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError('开始时间必须早于结束时间')
        
        # 验证不能自己代理自己
        principal_email = data.get('principal_email')
        proxy_email = data.get('proxy_email')
        
        # 如果是部分更新，从实例获取缺失的字段
        if instance:
            if principal_email is None:
                principal_email = instance.principal_email
            if proxy_email is None:
                proxy_email = instance.proxy_email
        
        if principal_email and proxy_email and principal_email == proxy_email:
            raise serializers.ValidationError('不能设置自己为代理人')
        
        return data



class ApprovalRuleSerializer(serializers.ModelSerializer):
    """审批规则序列化器"""
    
    class Meta:
        model = ApprovalRule
        fields = [
            'id',
            'name',
            'description',
            'priority',
            'is_active',
            'leave_type',
            'min_duration',
            'max_duration',
            'department_name',
            'min_level',
            'max_level',
            'workflow_spec_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """验证规则数据"""
        # 验证时长范围
        min_duration = data.get('min_duration')
        max_duration = data.get('max_duration')
        
        if min_duration is not None and max_duration is not None:
            if min_duration > max_duration:
                raise serializers.ValidationError('最小时长不能大于最大时长')
        
        # 验证职级范围
        min_level = data.get('min_level')
        max_level = data.get('max_level')
        
        if min_level is not None and max_level is not None:
            if min_level > max_level:
                raise serializers.ValidationError('最小职级不能大于最大职级')
        
        return data
