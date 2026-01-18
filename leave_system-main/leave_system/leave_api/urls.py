"""
URL 路由配置模块

定义请假审批系统的 API 路由
所有路由都以 /api/ 为前缀（在主 urls.py 中配置）

路由说明：
- /api/leave/create/ - 创建请假申请并启动工作流
- /api/leave/my-requests/ - 查询我的请假申请列表
- /api/leave/pending-approvals/ - 查询待审批任务列表
- /api/leave/approve/ - 批准请假申请
- /api/leave/reject/ - 拒绝请假申请
- /api/leave/return/ - 退回请假申请
- /api/leave/requests/<id>/history/ - 查询审批历史
- /api/approval-tasks/my-tasks/ - 查询我的待办任务（新）
- /api/approval-tasks/<task_id>/approve/ - 批准任务（新）
- /api/approval-tasks/<task_id>/reject/ - 拒绝任务（新）
- /api/approval-tasks/<task_id>/return/ - 退回任务（新）
- /api/approval-tasks/<task_id>/add-sign/ - 加签任务（新）
- /api/approval-tasks/<task_id>/transfer/ - 转签任务（新）
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views_v2 as views
from . import views_approval_tasks as approval_views
from . import views_proxy as proxy_views
from . import views_rule as rule_views
from . import views_bpmn as bpmn_views

# 创建路由器
router = DefaultRouter()
router.register(r'approval-rules', rule_views.ApprovalRuleViewSet, basename='approval-rule')

urlpatterns = [
    # ========== 审批规则相关接口（自定义路由，必须在 router 之前）==========
    
    # 模拟规则匹配
    # POST /api/approval-rules/simulate/
    # 功能：模拟规则匹配，测试规则配置
    path('approval-rules/simulate/', rule_views.simulate_rule, name='simulate_rule'),
    
    # ========== 路由器注册的接口 ==========
    path('', include(router.urls)),
    
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
    # GET /api/leave/pending-approvals/?user_email=xxx
    # 功能：查询所有待审批的任务（从工作流引擎获取并关联业务数据）
    path('leave/pending-approvals/', views.get_pending_approvals, name='get_pending_approvals'),
    
    # 批准请假申请
    # POST /api/leave/approve/
    # 功能：完成工作流任务并更新业务状态为批准
    path('leave/approve/', views.approve_leave_request, name='approve_leave_request'),
    
    # 拒绝请假申请
    # POST /api/leave/reject/
    # 功能：完成工作流任务并更新业务状态为拒绝
    path('leave/reject/', views.reject_leave_request, name='reject_leave_request'),
    
    # 退回请假申请
    # POST /api/leave/return/
    # 功能：退回请假申请到申请人或上一级审批人
    path('leave/return/', views.return_leave_request, name='return_leave_request'),
    
    # 查询审批历史
    # GET /api/leave/requests/<id>/history/
    # 功能：查询指定请假申请的审批历史记录
    path('leave/requests/<int:leave_request_id>/history/', views.get_approval_history, name='get_approval_history'),
    
    # 获取审批轨迹可视化数据
    # GET /api/leave/requests/<id>/timeline/
    # 功能：获取适合前端时间轴展示的审批历史数据
    path('leave/requests/<int:leave_request_id>/timeline/', views.get_approval_timeline, name='get_approval_timeline'),
    
    # ========== 抄送相关接口 ==========
    
    # 添加抄送人
    # POST /api/leave/requests/<id>/cc/
    # 功能：为指定请假申请添加抄送人
    path('leave/requests/<int:leave_request_id>/cc/', views.add_cc_record, name='add_cc_record'),
    
    # 查询抄送记录
    # GET /api/leave/requests/<id>/cc/
    # 功能：查询指定请假申请的所有抄送记录
    path('leave/requests/<int:leave_request_id>/cc/', views.get_cc_records, name='get_cc_records'),
    
    # 查询我的抄送列表
    # GET /api/leave/my-cc-requests/?user_email=xxx
    # 功能：查询抄送给我的所有请假申请
    path('leave/my-cc-requests/', views.get_my_cc_requests, name='get_my_cc_requests'),
    
    # 标记抄送已读
    # POST /api/leave/cc-records/<id>/mark-read/
    # 功能：标记抄送记录为已读
    path('leave/cc-records/<int:cc_record_id>/mark-read/', views.mark_cc_read, name='mark_cc_read'),
    
    # ========== 超时处理相关接口 ==========
    
    # 催办审批任务
    # POST /api/leave/requests/<id>/urge/
    # 功能：发送催办通知给当前审批人
    path('leave/requests/<int:leave_request_id>/urge/', views.urge_approval_task, name='urge_approval_task'),
    
    # ========== 审批任务相关接口（新）==========
    
    # 查询我的待办任务
    # GET /api/approval-tasks/my-tasks/?user_email=xxx
    # 功能：查询指定用户的所有待办审批任务
    path('approval-tasks/my-tasks/', approval_views.get_my_approval_tasks, name='get_my_approval_tasks'),
    
    # 批准任务
    # POST /api/approval-tasks/<task_id>/approve/
    # 功能：批准指定的审批任务
    path('approval-tasks/<str:task_id>/approve/', approval_views.approve_task, name='approve_task'),
    
    # 拒绝任务
    # POST /api/approval-tasks/<task_id>/reject/
    # 功能：拒绝指定的审批任务
    path('approval-tasks/<str:task_id>/reject/', approval_views.reject_task, name='reject_task'),
    
    # 退回任务
    # POST /api/approval-tasks/<task_id>/return/
    # 功能：退回指定的审批任务
    path('approval-tasks/<str:task_id>/return/', approval_views.return_task, name='return_task'),
    
    # 加签任务
    # POST /api/approval-tasks/<task_id>/add-sign/
    # 功能：为指定任务添加额外审批人
    path('approval-tasks/<str:task_id>/add-sign/', approval_views.add_sign_task, name='add_sign_task'),
    
    # 转签任务
    # POST /api/approval-tasks/<task_id>/transfer/
    # 功能：将指定任务转给其他审批人
    path('approval-tasks/<str:task_id>/transfer/', approval_views.transfer_task, name='transfer_task'),
    
    # ========== 代理设置相关接口 ==========
    
    # 创建代理设置
    # POST /api/proxy-settings/
    # 功能：创建新的代理设置
    path('proxy-settings/', proxy_views.create_proxy_setting, name='create_proxy_setting'),
    
    # 查询我的代理设置
    # GET /api/proxy-settings/my-settings/?user_email=xxx
    # 功能：查询指定用户的代理设置
    path('proxy-settings/my-settings/', proxy_views.get_my_proxy_settings, name='get_my_proxy_settings'),
    
    # 更新代理设置
    # PUT /api/proxy-settings/<id>/
    # 功能：更新指定的代理设置
    path('proxy-settings/<int:proxy_id>/', proxy_views.update_proxy_setting, name='update_proxy_setting'),
    
    # 取消代理设置
    # DELETE /api/proxy-settings/<id>/
    # 功能：取消指定的代理设置
    path('proxy-settings/<int:proxy_id>/delete/', proxy_views.delete_proxy_setting, name='delete_proxy_setting'),
    
    # 查询有效审批人
    # GET /api/employees/<email>/effective-approver/
    # 功能：查询指定员工的有效审批人（考虑代理）
    path('employees/<str:employee_email>/effective-approver/', proxy_views.get_effective_approver, name='get_effective_approver'),
    
    # ========== BPMN 流程管理相关接口 ==========
    
    # 流程列表和创建
    # GET /api/bpmn/processes/ - 获取所有流程列表
    # POST /api/bpmn/processes/ - 创建新流程
    path('bpmn/processes/', bpmn_views.processes_list_create, name='bpmn_processes'),
    
    # 流程详情、更新和删除
    # GET /api/bpmn/processes/<process_id>/ - 获取流程详情
    # PUT /api/bpmn/processes/<process_id>/ - 更新流程
    # DELETE /api/bpmn/processes/<process_id>/ - 删除流程
    path('bpmn/processes/<path:process_id>/', bpmn_views.process_detail, name='bpmn_process_detail'),
    
    # 部署流程
    # POST /api/bpmn/processes/<process_id>/deploy/
    path('bpmn/processes/<path:process_id>/deploy/', bpmn_views.deploy_process, name='deploy_bpmn_process'),
    
    # 验证流程
    # GET /api/bpmn/processes/<process_id>/validate/
    path('bpmn/processes/<path:process_id>/validate/', bpmn_views.validate_process, name='validate_bpmn_process'),

    # 保存 LogicFlow 流程图
    # POST /api/bpmn/save/
    path('bpmn/save/', bpmn_views.save_logicflow_diagram, name='save_logicflow_diagram'),
]
