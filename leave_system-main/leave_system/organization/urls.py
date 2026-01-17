"""
组织架构 URL 配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepartmentViewSet, EmployeeViewSet, RoleViewSet
from . import views_api

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'roles', RoleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # 简化的 API 接口（用于 BPMN 设计器）
    path('api/employees/', views_api.list_employees, name='api_list_employees'),
    path('api/departments/', views_api.list_departments, name='api_list_departments'),
    path('api/roles/', views_api.list_roles, name='api_list_roles'),
    path('api/roles/<int:role_id>/members/', views_api.get_role_members, name='api_get_role_members'),
]
