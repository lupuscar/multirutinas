from django.db import models
from django.contrib.auth.models import User

# (Tu modelo Ejercicio se mantiene igual)
class Ejercicio(models.Model):
    TIPO_CHOICES = [
        ('MAQ', 'Máquina'),
        ('LIB', 'Peso Libre'),
        ('CAL', 'Calistenia'),
        ('CAR', 'Cardio'),
        ('DEP', 'Deporte (Pádel, Tenis, etc.)'),
        ('DAN', 'Danza / Baile'),
        ('OUT', 'Aire Libre / Outdoor'),
        ('FLL', 'Flexibilidad / Yoga / Movilidad'),
    ]
    
    DIFICULTAD_CHOICES = [
        ('PRI', 'Principiante'),
        ('INT', 'Intermedio'),
        ('AVA', 'Avanzado'),
    ]

    GRUPO_MUSCULAR_CHOICES = [
        ('PEC', 'Pectoral'),
        ('ESP', 'Espalda'),
        ('PIE', 'Piernas'),
        ('HOM', 'Hombros'),
        ('BRA', 'Brazos (Bíceps/Tríceps)'),
        ('COR', 'Core / Abdominales'),
        ('GLU', 'Glúteos'),
        ('FUL', 'Cuerpo Completo / Full Body'),
        ('CAR', 'Cardiovascular / Resistencia'),
        ('AGI', 'Agilidad y Coordinación'),
    ]

    MODALIDAD_CHOICES = [
        ('REPS_PESO', 'Repeticiones y Peso'),
        ('TIEMPO', 'Tiempo / Duración'),
    ]

    nombre = models.CharField(max_length=100, verbose_name="Nombre del Ejercicio")
    definicion = models.TextField(blank=True, default='', verbose_name="Definición y técnica correcta")
    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES, default='LIB', verbose_name="Tipo de Ejercicio")
    modalidad = models.CharField(max_length=10, choices=MODALIDAD_CHOICES, default='REPS_PESO', verbose_name="Modalidad de medición")
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='ejercicios_personalizados', verbose_name="Creado por")
    foto = models.ImageField(upload_to='ejercicios/fotos/', null=True, blank=True, verbose_name="Foto demostrativa")
    video = models.URLField(max_length=200, null=True, blank=True, verbose_name="Enlace al Vídeo")
    dificultad = models.CharField(max_length=3, choices=DIFICULTAD_CHOICES, default='PRI', verbose_name="Dificultad")
    grupo_muscular = models.CharField(max_length=3, choices=GRUPO_MUSCULAR_CHOICES, verbose_name="Grupo Muscular Principal")
    equipo_necesario = models.CharField(max_length=100, blank=True, null=True, help_text="Ej: Mancuernas, Polea, Zapatillas de running, Pala de pádel...")

    class Meta:
        verbose_name = "Ejercicio"
        verbose_name_plural = "Ejercicios"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_grupo_muscular_display()})"

    @property
    def icono(self):
        """Devuelve el icono FontAwesome más representativo para este tipo de ejercicio"""
        iconos = {
            'DEP': 'fa-solid fa-table-tennis-paddle-ball',
            'DAN': 'fa-solid fa-person-dancing',
            'OUT': 'fa-solid fa-person-running',
            'CAR': 'fa-solid fa-heart-pulse',
            'FLL': 'fa-solid fa-spa',
            'CAL': 'fa-solid fa-person-walking',
            'MAQ': 'fa-solid fa-dumbbell',
            'LIB': 'fa-solid fa-dumbbell',
        }
        return iconos.get(self.tipo, 'fa-solid fa-stopwatch' if self.modalidad == 'TIEMPO' else 'fa-solid fa-dumbbell')



# =====================================================================
# MODELO PADRE: REGISTRO GENERAL DE LA SESIÓN DE EJERCICIO
# =====================================================================

class RegistroEjercicio(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_ejercicios')
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE, related_name='historial')
    fecha = models.DateField(auto_now_add=True)
    notas = models.TextField(blank=True, null=True, help_text="Ej: Sentí buena conexión mente-músculo.")
    etiqueta = models.CharField(max_length=50, blank=True, help_text="Identificador opcional (ej. 'Mañana', 'Fuerza', 'Variante A')")
    creado_en = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "Registro de Ejercicio"
        verbose_name_plural = "Registros de Ejercicios"
        ordering = ['-fecha']
        
    #MÉTODOS DE REPRESENTACIÓN DENTRO DEL ADMIN Y EL SISTEMA:
    def __str__(self):
            # Si el usuario escribió una etiqueta, la mostramos; si no, mostramos fecha y máquina
            if self.etiqueta:
                return f"{self.ejercicio.nombre} - {self.etiqueta} ({self.fecha})"
            return f"{self.ejercicio.nombre} - {self.fecha} [{self.creado_en.strftime('%H:%M')}]"


# =====================================================================
# MODELO HIJO: DETALLE DE CADA SERIE INDIVIDUAL
# =====================================================================
   
class Serie(models.Model):
    registro = models.ForeignKey(RegistroEjercicio, on_delete=models.CASCADE, related_name='series_detalle')
    numero_serie = models.PositiveIntegerField(verbose_name="Nº de Serie", blank=True, null=True)
    repeticiones = models.PositiveIntegerField(default=10, blank=True, null=True, verbose_name="Repeticiones")
    peso_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, 
                                  verbose_name="Peso (kg)", help_text="Dejar en blanco si es Calistenia.")
    tiempo_segundos = models.PositiveIntegerField(verbose_name="Tiempo (segundos)", null=True, blank=True,
                                                  help_text="Duración en segundos para ejercicios por tiempo.")
    

    class Meta:
        verbose_name = "Serie"
        verbose_name_plural = "Series"
        ordering = ['numero_serie']

    def save(self, *args, **kwargs):
        # Si la serie es nueva y no tiene número asignado todavía
        if not self.numero_serie:
            # Buscamos la última serie de este registro
            ultimas_series = Serie.objects.filter(registro=self.registro).order_by('-numero_serie')
            if ultimas_series.exists():
                self.numero_serie = ultimas_series.first().numero_serie + 1
            else:
                self.numero_serie = 1
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        if self.tiempo_segundos:
            mins, secs = divmod(self.tiempo_segundos, 60)
            if mins >= 60:
                horas, mins = divmod(mins, 60)
                tiempo_str = f"{horas}h {mins}m" if mins else f"{horas}h"
            elif mins:
                tiempo_str = f"{mins}m {secs}s" if secs else f"{mins}m"
            else:
                tiempo_str = f"{secs}s"
            peso_str = f" x {self.peso_kg} kg" if self.peso_kg else ""
            return f"Serie {self.numero_serie}: {tiempo_str}{peso_str}"
        peso_str = f"{self.peso_kg} kg" if self.peso_kg else "Peso corporal"
        return f"Serie {self.numero_serie}: {self.repeticiones or 0} reps x {peso_str}"