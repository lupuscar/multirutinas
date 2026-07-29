from django.db import models
from django.conf import settings

# =====================================================================
# 1. MODELO DE RUTINA 
# =====================================================================
class Rutina(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='rutinas'
    )
    nombre = models.CharField(max_length=100, help_text="Ej: Día de Piernas, Rutina Torso")
    descripcion = models.TextField(blank=True, help_text="Detalles opcionales de la rutina")
    
    # RELACIÓN ENTRE APPS: Usamos 'ejercicios.Ejercicio' como cadena de texto
    ejercicios = models.ManyToManyField(
        'ejercicios.Ejercicio', 
        through='RutinaEjercicio', 
        related_name='rutinas'
    )
    
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rutina"
        verbose_name_plural = "Rutinas"
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.nombre} - {self.usuario.username}"


# =====================================================================
# 2. MODELO INTERMEDIO RUTINA-EJERCICIO
# =====================================================================
class RutinaEjercicio(models.Model):
    """
    Este modelo define qué ejercicios van en qué rutina, en qué orden, 
    y cuáles son las series/repeticiones objetivo.
    """
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE)
    
    # RELACIÓN ENTRE APPS: Usamos 'ejercicios.Ejercicio' como cadena de texto
    ejercicio = models.ForeignKey('ejercicios.Ejercicio', on_delete=models.CASCADE)
    
    orden = models.PositiveIntegerField(default=1, help_text="Orden en el que se realiza el ejercicio")
    series_objetivo = models.PositiveIntegerField(default=3, blank=True, null=True)
    repeticiones_objetivo = models.PositiveIntegerField(default=10, blank=True, null=True)

    class Meta:
        # Evita que el mismo ejercicio se agregue dos veces a la misma rutina por accidente
        unique_together = ('rutina', 'ejercicio') 
        ordering = ['orden']

    def __str__(self):
        return f"{self.orden}. {self.ejercicio.nombre} ({self.rutina.nombre})"