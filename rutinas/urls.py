from django.urls import path
from . import views

app_name = 'rutinas'

urlpatterns = [
    path('', views.lista_rutinas_view, name='lista_rutinas'),
    path('crear/', views.crear_rutina_view, name='crear_rutina'),
    path('editar/<int:rutina_id>/', views.editar_rutina_view, name='editar_rutina'),
    path('eliminar/<int:rutina_id>/', views.eliminar_rutina_view, name='eliminar_rutina'),
    path('iniciar/<int:rutina_id>/', views.iniciar_rutina_view, name='iniciar_rutina'),
    
    # Asistente y Recomendador Automático de Rutinas
    path('recomendador/', views.recomendador_rutinas_view, name='recomendador_rutinas'),
    path('recomendador/guardar/', views.guardar_plan_recomendado_ajax, name='guardar_plan_recomendado_ajax'),
    
    # Endpoints AJAX para experiencia interactiva y en directo
    path('crear-ejercicio-ajax/', views.crear_ejercicio_rapido_ajax, name='crear_ejercicio_rapido_ajax'),
    path('guardar-serie-ajax/', views.guardar_serie_ajax, name='guardar_serie_ajax'),
    path('finalizar-entrenamiento-ajax/', views.finalizar_entrenamiento_ajax, name='finalizar_entrenamiento_ajax'),
]