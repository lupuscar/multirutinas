from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('usuario/', include('users.urls')),
    path('ejercicios/', include('ejercicios.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('rutinas/', include('rutinas.urls')),
    path('configuracion/', include('core.urls')),
    # Configuración personalizada de restablecimiento para enviar correo HTML interpretado + texto plano
    path(
        'accounts/password_reset/',
        auth_views.PasswordResetView.as_view(
            html_email_template_name='registration/password_reset_email.html',
            email_template_name='registration/password_reset_email.txt',
            subject_template_name='registration/password_reset_subject.txt',
        ),
        name='password_reset'
    ),
    # Añadimos el resto de URLs de autenticación por defecto de Django
    path('accounts/', include('django.contrib.auth.urls')), 
    path('', lambda request: redirect('users:perfil', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)