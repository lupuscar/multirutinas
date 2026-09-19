from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('registro/', views.registro_view, name='registro'),
    path('perfil/', views.perfil_view, name='perfil'),
]