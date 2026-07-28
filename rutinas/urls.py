# users/urls.py
from django.urls import path
from . import views

app_name = 'rutinas'

urlpatterns = [
    path('rutinas/', views.lista_rutinas, name='rutinas'),

]