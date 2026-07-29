from django.db import models
from django.contrib.auth.models import User

# (Tu modelo Ejercicio se mantiene igual)
class Ejercicio(models.Model):
    TIPO_CHOICES = [
        ('MAQ', 'Máquina'),
        ('LIB', 'Peso Libre'),
        ('CAL', 'Calistenia'),
        ('CAR', 'Cardio'),
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
    ]

    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Ejercicio")
    definicion = models.TextField(verbose_name="Definición y técnica correcta")
    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES, default='LIB', verbose_name="Tipo de Ejercicio")
    foto = models.ImageField(upload_to='ejercicios/fotos/', null=True, blank=True, verbose_name="Foto demostrativa")
    video = models.URLField(max_length=200, null=True, blank=True, verbose_name="Enlace al Vídeo")
    dificultad = models.CharField(max_length=3, choices=DIFICULTAD_CHOICES, default='PRI', verbose_name="Dificultad")
    grupo_muscular = models.CharField(max_length=3, choices=GRUPO_MUSCULAR_CHOICES, verbose_name="Grupo Muscular Principal")
    equipo_necesario = models.CharField(max_length=100, blank=True, null=True, help_text="Ej: Mancuernas, Polea...")

    class Meta:
        verbose_name = "Ejercicio"
        verbose_name_plural = "Ejercicios"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_grupo_muscular_display()})"


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
    # Dejamos editable=False o blank=True para permitir que se calcule automáticamente
    numero_serie = models.PositiveIntegerField(verbose_name="Nº de Serie", blank=True, null=True)
    repeticiones = models.PositiveIntegerField(default=10, verbose_name="Repeticiones")
    peso_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, 
                                  verbose_name="Peso (kg)", help_text="Dejar en blanco si es Calistenia.")
    

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

    def __str__(self):
        peso_str = f"{self.peso_kg} kg" if self.peso_kg else "Peso corporal"
        return f"Serie {self.numero_serie}: {self.repeticiones} reps x {peso_str}"