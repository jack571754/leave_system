"""
组织架构视图
定义组织架构相关的 REST API 视图
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Department, Employee, Role
from .serializers import DepartmentSerializer, EmployeeSerializer, RoleSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    """部门管理 ViewSet"""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    
    @action(detail=True, methods=['get'])
    def manager(self, request, pk=None):
        """获取部门负责人"""
        department = self.get_object()
        if department.manager:
            serializer = EmployeeSerializer(department.manager)
            return Response(serializer.data)
        return Response({'detail': '该部门没有负责人'}, status=status.HTTP_404_NOT_FOUND)


class EmployeeViewSet(viewsets.ModelViewSet):
    """员工管理 ViewSet"""
    queryset = Employee.objects.select_related('user', 'department', 'direct_manager').all()
    serializer_class = EmployeeSerializer
    
    @action(detail=True, methods=['get'])
    def direct_manager(self, request, pk=None):
        """获取直属上级"""
        employee = self.get_object()
        if employee.direct_manager:
            serializer = EmployeeSerializer(employee.direct_manager)
            return Response(serializer.data)
        return Response({'detail': '该员工没有直属上级'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def subordinates(self, request, pk=None):
        """获取下属列表"""
        employee = self.get_object()
        subordinates = employee.subordinates.all()
        serializer = EmployeeSerializer(subordinates, many=True)
        return Response(serializer.data)


class RoleViewSet(viewsets.ModelViewSet):
    """角色管理 ViewSet"""
    queryset = Role.objects.prefetch_related('employees').all()
    serializer_class = RoleSerializer
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """获取角色成员列表"""
        role = self.get_object()
        members = role.employees.all()
        serializer = EmployeeSerializer(members, many=True)
        return Response(serializer.data)
