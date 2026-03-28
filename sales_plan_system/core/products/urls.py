from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.sku_list, name='sku_list'),
    path('create/', views.sku_create, name='sku_create'),
    path('<int:pk>/', views.sku_detail, name='sku_detail'),
    path('<int:pk>/edit/', views.sku_edit, name='sku_edit'),
    path('<int:pk>/delete/', views.sku_delete, name='sku_delete'),
    path('import/', views.sku_import, name='sku_import'),
    path('export/', views.sku_export, name='sku_export'),
    # API endpoints for HTMX
    path('api/search/', views.sku_search_api, name='sku_search_api'),
]
