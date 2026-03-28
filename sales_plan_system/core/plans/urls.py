from django.urls import path

from . import views

app_name = 'plans'

urlpatterns = [
    path('', views.plan_list, name='plan_list'),
    path('my/', views.my_plans, name='my_plans'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('tasks/my/', views.my_tasks, name='my_tasks'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/add-items/', views.add_task_items, name='add_task_items'),
    path('tasks/<int:pk>/save-matrix/', views.save_task_matrix, name='save_task_matrix'),
    path('tasks/<int:pk>/update-cell/', views.update_task_cell, name='update_task_cell'),
    path('tasks/<int:pk>/submit/', views.submit_task, name='submit_task'),
    path('tasks/<int:pk>/withdraw/', views.withdraw_task, name='withdraw_task'),
    path('tasks/<int:pk>/bulk-delete/', views.bulk_delete_task_items, name='bulk_delete_task_items'),
    path('tasks/<int:pk>/template/', views.task_import_template, name='task_import_template'),
    path('tasks/<int:pk>/import-preview/', views.task_import_preview, name='task_import_preview'),
    path('tasks/<int:pk>/import-confirm/', views.task_import_confirm, name='task_import_confirm'),
    path('tasks/<int:pk>/export/', views.export_task, name='export_task'),
    path('reports/', views.plan_report, name='plan_report'),
    path('reports/export/', views.export_report, name='export_report'),
    path('api/summary/', views.plan_summary_api, name='plan_summary_api'),
]
