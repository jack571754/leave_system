from django.urls import path

from . import views

app_name = 'mechanisms'

urlpatterns = [
    path('', views.mechanism_center, name='center'),
]
