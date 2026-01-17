"""
组织架构序列化器
定义 REST API 的数据序列化和反序列化
"""

from rest_framework import serializers
from .models import Department, Employee, Role
from django.contrib.auth.models import User


class DepartmentSerializer(serializers.ModelSerializer):
    """部门序列化器"""
    manager_name = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = ['id', 'name', 'parent', 'parent_name', 'manager', 'manager_name', 
                  'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_manager_name(self, obj):
        return obj.manager.get_full_name() if obj.manager else None
    
    def get_parent_name(self, obj):
        return obj.parent.name if obj.parent else None


class EmployeeSerializer(serializers.ModelSerializer):
    """员工序列化器"""
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    manager_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = ['id', 'user', 'username', 'full_name', 'employee_id', 'department', 
                  'department_name', 'position', 'level', 'direct_manager', 'manager_name',
                  'email', 'phone', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_manager_name(self, obj):
        return obj.direct_manager.get_full_name() if obj.direct_manager else None


class RoleSerializer(serializers.ModelSerializer):
    """角色序列化器"""
    employee_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'employees', 'employee_count', 'created_at']
        read_only_fields = ['created_at']
    
    def get_employee_count(self, obj):
        return obj.employees.count()
