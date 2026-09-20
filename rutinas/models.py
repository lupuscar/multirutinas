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
    
    # DÍAS ASIGNADOS DE LA SEMANA: ej. "1,4" (1=Martes, 4=Viernes)
    # 0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo (coincide con datetime.weekday())
    dias_semana = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name="Días asignados",
        help_text="Códigos numéricos de los días de la semana separados por comas (0=Lun, ..., 6=Dom)"
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    DIAS_SEMANA_NOMBRES = {
        0: ('Lun', 'Lunes'),
        1: ('Mar', 'Martes'),
        2: ('Mié', 'Miércoles'),
        3: ('Jue', 'Jueves'),
        4: ('Vie', 'Viernes'),
        5: ('Sáb', 'Sábado'),
        6: ('Dom', 'Domingo'),
    }

    class Meta:
        verbose_name = "Rutina"
        verbose_name_plural = "Rutinas"
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.nombre} - {self.usuario.username}"

    @property
    def lista_dias_numeros(self):
        """Devuelve una lista ordenada de enteros con los días asignados [0, 1, ..., 6]"""
        if not self.dias_semana:
            return []
        try:
            return sorted([int(d.strip()) for d in str(self.dias_semana).split(',') if d.strip().isdigit()])
        except Exception:
            return []

    @property
    def badges_dias(self):
        """Devuelve una lista estructurada con información para renderizar los badges de días"""
        nums = sorted(self.lista_dias_numeros)
        return [
            {
                'num': n,
                'corto': self.DIAS_SEMANA_NOMBRES[n][0],
                'completo': self.DIAS_SEMANA_NOMBRES[n][1]
            }
            for n in nums if n in self.DIAS_SEMANA_NOMBRES
        ]

    @property
    def toca_hoy(self):
        """Indica si esta rutina está programada para entrenar hoy"""
        from django.utils import timezone
        return timezone.now().date().weekday() in self.lista_dias_numeros


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
    peso_objetivo = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Peso objetivo (kg)", 
        help_text="Carga en kg planificada para este ejercicio (dejar en blanco para peso corporal o libre)"
    )
    tiempo_objetivo_segundos = models.PositiveIntegerField(blank=True, null=True, help_text="Tiempo objetivo en segundos (ej. 45 para plancha)")


    class Meta:
        # Evita que el mismo ejercicio se agregue dos veces a la misma rutina por accidente
        unique_together = ('rutina', 'ejercicio') 
        ordering = ['orden']

    def __str__(self):
        return f"{self.orden}. {self.ejercicio.nombre} ({self.rutina.nombre})"