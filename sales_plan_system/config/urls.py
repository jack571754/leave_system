from django.contrib import admin
from django.urls import include, path

from config.health_views import health_check, readiness_check
from core.plans.views import dashboard

admin.site.site_header = '销售计划系统管理后台'
admin.site.site_title = '销售计划系统 Admin'
admin.site.index_title = '后台管理'

urlpatterns = [
    path('health', health_check, name='health'),
    path('ready', readiness_check, name='ready'),
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('', include('core.users.urls')),
    path('products/', include('core.products.urls')),
    path('plans/', include('core.plans.urls')),
    path('approvals/', include('core.approvals.urls')),
    path('permissions/', include('core.permissions.urls')),
    path('mechanisms/', include('core.mechanisms.urls')),
    path('analytics/', include('core.analytics.urls')),
    path('integrations/', include('core.integrations.urls')),
]
