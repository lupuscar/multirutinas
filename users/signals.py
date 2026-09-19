from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """
    Crea automáticamente el perfil del usuario cada vez que se registra uno nuevo.
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, created=False, **kwargs):
    """
    Guarda el perfil asociado al usuario cuando se actualiza el usuario.
    Ignora actualizaciones parciales como last_login o is_active para evitar colisiones en caché.
    """
    if not created and hasattr(instance, 'profile'):
        update_fields = kwargs.get('update_fields')
        if update_fields and ('last_login' in update_fields or 'is_active' in update_fields):
            return
        instance.profile.save()


# =====================================================================
# SEÑALES DE AUDITORÍA Y SEGURIDAD (ACCESOS E INCIDENCIAS)
# =====================================================================
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from .utils import registrar_log


@receiver(user_logged_in)
def log_usuario_login(sender, request, user, **kwargs):
    """Registra en la auditoría cada inicio de sesión exitoso"""
    registrar_log(
        request=request,
        usuario=user,
        nivel='INFO',
        tipo='LOGIN',
        mensaje=f"Inicio de sesión exitoso para usuario: {user.username} ({user.email})"
    )


@receiver(user_logged_out)
def log_usuario_logout(sender, request, user, **kwargs):
    """Registra en la auditoría el cierre de sesión"""
    if user:
        registrar_log(
            request=request,
            usuario=user,
            nivel='INFO',
            tipo='LOGOUT',
            mensaje=f"Cierre de sesión de usuario: {user.username}"
        )


@receiver(user_login_failed)
def log_usuario_login_fallido(sender, credentials, request, **kwargs):
    """Registra intentos fallidos de autenticación (posible fuerza bruta o errores)"""
    username_intentado = credentials.get('username', 'desconocido') if credentials else 'desconocido'
    registrar_log(
        request=request,
        usuario=None,
        nivel='WARNING',
        tipo='LOGIN_FAIL',
        mensaje=f"Intento fallido de inicio de sesión con usuario: '{username_intentado}'"
    )