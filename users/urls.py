# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('perfil/', views.perfil_view, name='perfil'),
]