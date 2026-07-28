# users/urls.py
from django.urls import path
from . import views

app_name = 'ejercicios'

urlpatterns = [
    path('ejercicios/', views.lista_ejercicios, name='ejercicios'),
    path('ejercicios/', views.lista_ejercicios, name='lista'),
]