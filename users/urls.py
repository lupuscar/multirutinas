from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('registro/', views.registro_view, name='registro'),
    path('registro/pendiente/', views.registro_pendiente_view, name='registro_pendiente'),
    path('activar/<uidb64>/<token>/', views.activar_cuenta_view, name='activar_cuenta'),
    path('reenviar-activacion/', views.reenviar_activacion_view, name='reenviar_activacion'),
    path('perfil/', views.perfil_view, name='perfil'),
]