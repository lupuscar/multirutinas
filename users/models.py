from django.db import models
from django.conf import settings


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # 1. PLANES DE MONETIZACIÓN / SAAS
    PLANES_SUSCRIPCION = [
        ('FREE', 'Plan Gratuito'),
        ('PRO', 'FitApp PRO ⭐'),
        ('COACH', 'Coach / Entrenador'),
    ]
    tipo_suscripcion = models.CharField(
        max_length=10,
        choices=PLANES_SUSCRIPCION,
        default='FREE',
        verbose_name="Plan de Suscripción"
    )
    fecha_fin_suscripcion = models.DateField(
        null=True,
        blank=True,
        verbose_name="Vencimiento de Suscripción"
    )

    # 2. FOTO Y BIOGRAFÍA
    foto_perfil = models.ImageField(
        upload_to='perfiles/',
        null=True,
        blank=True,
        help_text="Foto de perfil del usuario"
    )
    biografia = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text="Una breve frase motivadora o descripción personal"
    )

    # 3. DATOS FÍSICOS
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

    # 4. OBJETIVOS Y NIVEL DEPORTIVO
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

    OBJETIVOS_FITNESS = [
        ('HIP', 'Hipertrofia / Ganar Músculo'),
        ('DEF', 'Definición / Perder Grasa'),
        ('FUE', 'Fuerza / Rendimiento'),
        ('SAL', 'Salud y Condición Física'),
        ('RES', 'Resistencia y Cardio'),
    ]
    objetivo = models.CharField(
        max_length=3,
        choices=OBJETIVOS_FITNESS,
        default='HIP',
        verbose_name="Objetivo Principal"
    )
    dias_objetivo_semana = models.PositiveSmallIntegerField(
        default=4,
        verbose_name="Días objetivo por semana"
    )

    def __str__(self):
        return f"Perfil de {self.user.username} ({self.get_tipo_suscripcion_display()})"

    @property
    def es_pro(self):
        return self.tipo_suscripcion in ['PRO', 'COACH']

    @property
    def imc(self):
        if self.peso and self.altura:
            altura_m = self.altura / 100
            return round(float(self.peso) / (altura_m ** 2), 2)
        return None

    @property
    def categoria_imc(self):
        val = self.imc
        if not val:
            return None
        if val < 18.5:
            return {'nombre': 'Bajo peso', 'badge_class': 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'}
        elif val < 25.0:
            return {'nombre': 'Peso normal / Saludable', 'badge_class': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'}
        elif val < 30.0:
            return {'nombre': 'Sobrepeso', 'badge_class': 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'}
        else:
            return {'nombre': 'Obesidad', 'badge_class': 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300'}


# =====================================================================
# 5. AUDITORÍA, INCIDENCIAS Y REGISTRO DE EVENTOS (LOGS)
# =====================================================================
class LogActividad(models.Model):
    NIVELES = [
        ('INFO', 'Información'),
        ('WARNING', 'Advertencia'),
        ('ERROR', 'Error / Excepción'),
        ('CRITICAL', 'Crítico'),
    ]

    TIPOS = [
        ('LOGIN', 'Inicio de sesión'),
        ('LOGOUT', 'Cierre de sesión'),
        ('LOGIN_FAIL', 'Intento de login fallido'),
        ('REGISTRO', 'Registro de nuevo usuario'),
        ('PERFIL_EDIT', 'Edición de perfil'),
        ('PASSWORD_RESET', 'Solicitud reseteo de clave'),
        ('PASSWORD_CHANGE', 'Cambio de clave'),
        ('RUTINA_CREATE', 'Creación de rutina'),
        ('SERIE_LOG', 'Registro de serie en Modo Gym'),
        ('ERROR_500', 'Excepción 500 en servidor'),
        ('OTRO', 'Otro evento'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs_actividad',
        verbose_name="Usuario"
    )
    nivel = models.CharField(max_length=10, choices=NIVELES, default='INFO', verbose_name="Nivel")
    tipo = models.CharField(max_length=20, choices=TIPOS, default='INFO', verbose_name="Tipo de Evento")
    ruta = models.CharField(max_length=255, blank=True, default='', verbose_name="Ruta / URL")
    metodo = models.CharField(max_length=10, blank=True, default='GET', verbose_name="Método HTTP")
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")
    user_agent = models.CharField(max_length=255, blank=True, default='', verbose_name="Dispositivo / Navegador")
    mensaje = models.TextField(verbose_name="Mensaje o Descripción")
    traceback = models.TextField(null=True, blank=True, verbose_name="Traza de Error (Traceback)")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")

    class Meta:
        verbose_name = "Registro de Actividad"
        verbose_name_plural = "Auditoría de Actividad e Incidencias"
        ordering = ['-creado_en']

    def __str__(self):
        usr = self.usuario.username if self.usuario else "Anónimo"
        return f"[{self.nivel}] {self.get_tipo_display()} - {usr} ({self.creado_en.strftime('%d/%m/%Y %H:%M')})"