from django.db import models
from django.contrib.auth.models import User

class Ejercicio(models.Model):
    # Opciones predefinidas (Choices)
    TIPO_CHOICES = [
        ('MAQ', 'Máquina'),
        ('LIB', 'Peso Libre'),
        ('CAL', 'Calistenia'),
        ('CAR', 'Cardio'), # Extra útil
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

    # Campos principales
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Ejercicio")
    definicion = models.TextField(verbose_name="Definición y técnica correcta")
    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES, default='LIB', verbose_name="Tipo de Ejercicio")
    
    # Multimedia
    foto = models.ImageField(upload_to='ejercicios/fotos/', null=True, blank=True, verbose_name="Foto demostrativa")
    video = models.URLField(max_length=200, null=True, blank=True, verbose_name="Enlace al Vídeo (YouTube, Vimeo...)")
    
    # Extras interesantes añadidos
    dificultad = models.CharField(max_length=3, choices=DIFICULTAD_CHOICES, default='PRI', verbose_name="Dificultad")
    grupo_muscular = models.CharField(max_length=3, choices=GRUPO_MUSCULAR_CHOICES, verbose_name="Grupo Muscular Principal")
    equipo_necesario = models.CharField(max_length=100, blank=True, null=True, help_text="Ej: Mancuernas, Banco inclinado, Polea...")

    class Meta:
        verbose_name = "Ejercicio"
        verbose_name_plural = "Ejercicios"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_grupo_muscular_display()})"


# =====================================================================
# MODELO PARA REGISTRAR EL PESO (Donde validamos si usa Kg o no)
# =====================================================================

class RegistroEjercicio(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_ejercicios')
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE, related_name='historial')
    
    fecha = models.DateField(auto_now_add=True)
    series = models.PositiveIntegerField(default=3, verbose_name="Series")
    repeticiones = models.PositiveIntegerField(default=10, verbose_name="Repeticiones por serie")
    
    # Aquí es donde va el PESO. Puede quedar en nulo si es Calistenia.
    peso_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, 
                                  help_text="Dejar en blanco si es Calistenia (peso corporal).")
    
    notas = models.TextField(blank=True, null=True, help_text="Ej: Me dolió un poco el hombro, o 'Subir peso la próxima vez'")

    class Meta:
        verbose_name = "Registro de Ejercicio"
        verbose_name_plural = "Registros de Ejercicios"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.ejercicio.nombre} - {self.peso_kg}kg el {self.fecha}"