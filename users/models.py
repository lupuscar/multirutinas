from django.db import models
from django.conf import settings

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Campo nuevo para la foto de perfil
    foto_perfil = models.ImageField(
        upload_to='perfiles/', 
        null=True, 
        blank=True,
        help_text="Foto de perfil del usuario"
    )
    
    # Datos físicos
    peso = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Peso en kg",
        null=True, 
        blank=True
    )
    altura = models.PositiveIntegerField(
        help_text="Altura en cm",
        null=True, 
        blank=True
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    
    # Datos deportivos opcionales
    NIVEL_EXPERIENCIA = [
        ('PR', 'Principiante'),
        ('IN', 'Intermedio'),
        ('AV', 'Avanzado'),
    ]
    nivel = models.CharField(
        max_length=2, 
        choices=NIVEL_EXPERIENCIA, 
        default='PR'
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"

    @property
    def imc(self):
        if self.peso and self.altura:
            altura_m = self.altura / 100
            return round(float(self.peso) / (altura_m ** 2), 2)
        return None