"""
URL 路由配置模块

定义请假审批系统的 API 路由
所有路由都以 /api/ 为前缀（在主 urls.py 中配置）

路由说明：
- /api/leave/create/ - 创建请假申请并启动工作流
- /api/leave/my-requests/ - 查询我的请假申请列表
- /api/leave/pending-approvals/ - 查询待审批任务列表
- /api/leave/approve/ - 提交审批决定
"""

from django.urls import path
from . import views

urlpatterns = [
    # ========== 请假申请相关接口 ==========
    
    # 创建请假申请
    # POST /api/leave/create/
    # 功能：创建请假申请记录并启动 SpiffWorkflow 工作流
    path('leave/create/', views.create_leave_request, name='create_leave_request'),
    
    # 查询我的请假申请
    # GET /api/leave/my-requests/?user_email=xxx
    # 功能：根据用户邮箱查询该用户的所有请假申请
    path('leave/my-requests/', views.get_my_leave_requests, name='get_my_leave_requests'),
    
    # 查询待审批任务
    # GET /api/leave/pending-approvals/?user_id=admin
    # 功能：查询所有待审批的任务（从工作流引擎获取并关联业务数据）
    path('leave/pending-approvals/', views.get_pending_approvals, name='get_pending_approvals'),
    
    # 提交审批决定
    # POST /api/leave/approve/
    # 功能：完成工作流任务并更新业务状态
    path('leave/approve/', views.approve_leave_request, name='approve_leave_request'),
]
