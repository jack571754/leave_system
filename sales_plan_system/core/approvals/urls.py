from django.urls import path

from . import views

app_name = 'approvals'

urlpatterns = [
    path('', views.approval_center, name='center'),
    path('pending/', views.pending_approvals, name='pending'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('history/', views.approval_history, name='history'),
    path('instances/<int:instance_id>/', views.approval_instance_detail, name='instance_detail'),
    path('<int:plan_id>/approve/', views.approve_plan, name='approve'),
    path('<int:plan_id>/reject/', views.reject_plan, name='reject'),
    path('tasks/<int:task_id>/approve/', views.approve_task, name='approve_task'),
    path('tasks/<int:task_id>/reject/', views.reject_task, name='reject_task'),
    path('batch-approve/', views.batch_approve, name='batch_approve'),
    path('batch-reject/', views.batch_reject, name='batch_reject'),
    path('api/pending-count/', views.pending_count_api, name='pending_count_api'),
]
