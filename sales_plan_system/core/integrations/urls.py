from django.urls import path

from . import views

app_name = 'integrations'

urlpatterns = [
    path('', views.integration_center, name='center'),
]
