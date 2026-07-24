from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Sesion(models.Model):
    """
    Una sesión de entrenamiento real (el 'lo que pasó de verdad' de un día).
    Puede estar ligada a una rutina planificada o ser libre.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sesiones",
    )
    rutina = models.ForeignKey(
        "rutinas.Rutina",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sesiones",
        help_text="Rutina de referencia, si esta sesión sigue un plan",
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    lugar = models.CharField(
        max_length=100, blank=True,
        help_text="Ej: gimnasio, casa, aire libre",
    )
    notas = models.TextField(blank=True)
    completada = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sesión"
        verbose_name_plural = "Sesiones"
        ordering = ["-fecha", "-hora_inicio"]

    def __str__(self):
        return f"Sesión {self.fecha} - {self.usuario.username}"


class SesionEjercicio(models.Model):
    """
    Un ejercicio concreto realizado dentro de una sesión.
    Agrupa las series realizadas de ese ejercicio en esa sesión.
    """

    sesion = models.ForeignKey(
        Sesion, on_delete=models.CASCADE, related_name="ejercicios_sesion"
    )
    ejercicio = models.ForeignKey(
        "ejercicios.Ejercicio", on_delete=models.PROTECT, related_name="usado_en_sesiones"
    )
    rutina_ejercicio = models.ForeignKey(
        "rutinas.RutinaEjercicio",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="ejecuciones",
        help_text="Referencia al objetivo planificado, si existe",
    )
    orden = models.PositiveSmallIntegerField(default=0)
    notas = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Ejercicio de sesión"
        verbose_name_plural = "Ejercicios de sesión"
        ordering = ["orden"]

    def __str__(self):
        return f"{self.ejercicio.nombre} en {self.sesion}"


class SerieRealizada(models.Model):
    """Una serie individual ejecutada dentro de un ejercicio de una sesión."""

    sesion_ejercicio = models.ForeignKey(
        SesionEjercicio, on_delete=models.CASCADE, related_name="series"
    )
    numero_serie = models.PositiveSmallIntegerField()
    repeticiones_realizadas = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)]
    )
    peso_kg = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Dejar en blanco si es peso corporal o sin peso",
    )
    rpe = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Esfuerzo percibido (Rate of Perceived Exertion), escala 1-10",
    )
    al_fallo = models.BooleanField(
        default=False, help_text="Si la serie se hizo hasta el fallo muscular"
    )
    notas = models.CharField(max_length=255, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Serie realizada"
        verbose_name_plural = "Series realizadas"
        ordering = ["numero_serie"]
        constraints = [
            models.UniqueConstraint(
                fields=["sesion_ejercicio", "numero_serie"],
                name="unico_numero_serie_por_ejercicio_sesion",
            )
        ]

    def __str__(self):
        return f"Serie {self.numero_serie} - {self.sesion_ejercicio}"