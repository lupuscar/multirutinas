from django.urls import path
from django.views.generic.base import RedirectView
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', RedirectView.as_view(pattern_name='dashboard:dashboard', permanent=False)),
]