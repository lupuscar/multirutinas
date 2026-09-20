from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('sistema/', views.configuracion_sistema_view, name='configuracion_sistema'),
    path('sistema/accion/<str:accion>/', views.accion_mantenimiento_view, name='accion_mantenimiento'),
]
