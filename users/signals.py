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
def guardar_perfil_usuario(sender, instance, **kwargs):
    """
    Guarda el perfil asociado al usuario cuando se actualiza el usuario.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()