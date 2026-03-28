from django.urls import path

from . import views

app_name = 'permissions'

urlpatterns = [
    path('', views.permission_center, name='center'),
    path('no-access/', views.no_access, name='no_access'),
]
