"""
URL configuration for leave_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.shortcuts import render, redirect

def index_view(request):
    """根路径视图 - 重定向到管理面板"""
    return redirect('/dashboard/')

def api_info_view(request):
    """API 信息视图"""
    return JsonResponse({
        'message': '欢迎使用请假审批系统 API',
        'version': '2.0',
        'dashboard': '/dashboard/',
        'endpoints': {
            'create_leave': '/api/leave/create/',
            'my_requests': '/api/leave/my-requests/',
            'pending_approvals': '/api/leave/pending-approvals/',
            'approve': '/api/leave/approve/',
            'reject': '/api/leave/reject/',
            'history': '/api/leave/requests/{id}/history/',
        },
        'documentation': '请访问 /dashboard/ 使用管理界面'
    })

def dashboard_view(request):
    """管理面板视图"""
    return render(request, 'dashboard.html')

def bpmn_designer_view(request):
    """BPMN 设计器视图"""
    return render(request, 'bpmn_designer.html')

urlpatterns = [
    path('', index_view, name='index'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('bpmn-designer/', bpmn_designer_view, name='bpmn_designer'),
    path('api-info/', api_info_view, name='api_info'),
    path('admin/', admin.site.urls),
    path('api/', include('leave_api.urls')),
    path('api/organization/', include('organization.urls')),
    path('api/notifications/', include('notifications.urls')),
]
