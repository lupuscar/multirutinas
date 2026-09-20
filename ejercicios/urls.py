from django.urls import path
from . import views

app_name = 'ejercicios'

urlpatterns = [
    path('', views.lista_ejercicios, name='ejercicios'),
    path('crear/', views.crear_ejercicio, name='crear_ejercicio'),
    path('editar/<int:ejercicio_id>/', views.editar_ejercicio, name='editar_ejercicio'),
    path('eliminar/<int:ejercicio_id>/', views.eliminar_ejercicio, name='eliminar_ejercicio'),
    path('detalle/<int:ejercicio_id>/', views.detalle_ejercicio, name='detalle_ejercicio'),
    path('registrar-sesion/', views.registrar_sesion_libre, name='registrar_sesion_libre'),
    path('registrar-sesion/<int:ejercicio_id>/', views.registrar_sesion_libre, name='registrar_sesion_libre_ejercicio'),
]