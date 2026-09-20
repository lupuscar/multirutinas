from django.db import models
from django.core.cache import cache


class ConfiguracionSitio(models.Model):
    """
    Modelo Singleton que almacena la configuración global de la plataforma Multirutinas (FitApp).
    Solo existe un único registro (ID=1) y se cachea para optimizar el rendimiento de cada request.
    """
    TIPO_BANNER_CHOICES = [
        ('INFO', 'Información (Azul)'),
        ('WARNING', 'Advertencia (Ámbar)'),
        ('SUCCESS', 'Éxito (Esmeralda)'),
        ('DANGER', 'Urgente (Rojo)'),
    ]

    CACHE_KEY = 'configuracion_sitio_global'

    # --- 1. MODO MANTENIMIENTO ---
    modo_mantenimiento = models.BooleanField(
        default=False,
        verbose_name="Modo Mantenimiento Activo",
        help_text="Si está activo, los visitantes y usuarios normales verán la pantalla de mantenimiento (503). Solo Staff y Administradores podrán acceder."
    )
    mensaje_mantenimiento = models.TextField(
        default="Estamos realizando labores de optimización y mantenimiento en FitApp. Estaremos de vuelta muy pronto.",
        verbose_name="Mensaje de Mantenimiento",
        help_text="Texto explicativo mostrado a los usuarios en la pantalla 503."
    )
    tiempo_estimado_reapertura = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Tiempo Estimado de Reapertura",
        help_text="Ejemplo: 'En 30 minutos', 'Hoy a las 18:00 h'"
    )

    # --- 2. CONTROL DE REGISTRO DE USUARIOS ---
    registro_abierto = models.BooleanField(
        default=True,
        verbose_name="Registro Público Abierto",
        help_text="Si se desactiva, nadie podrá crear nuevas cuentas por el formulario público."
    )
    mensaje_registro_cerrado = models.TextField(
        default="El registro de nuevos usuarios se encuentra temporalmente cerrado. Contacta con la administración para solicitar una cuenta.",
        verbose_name="Mensaje de Registro Cerrado",
        help_text="Mensaje informativo cuando un usuario intenta acceder al registro estando cerrado."
    )

    # --- 3. BANNER GLOBAL DE AVISOS (BROADCAST) ---
    banner_activo = models.BooleanField(
        default=False,
        verbose_name="Banner Global Activo",
        help_text="Muestra una barra de notificación superior fija para todos los usuarios autenticados."
    )
    banner_texto = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Texto del Banner",
        help_text="Aviso breve (ej. '¡Actualización importante: nuevo sistema de cálculo 1RM disponible!')."
    )
    banner_tipo = models.CharField(
        max_length=20,
        choices=TIPO_BANNER_CHOICES,
        default='INFO',
        verbose_name="Tipo de Banner"
    )

    # --- 4. PARÁMETROS DEPORTIVOS Y CATÁLOGO ---
    usuarios_pueden_crear_ejercicios = models.BooleanField(
        default=True,
        verbose_name="Permitir a Usuarios Crear Ejercicios",
        help_text="Si se desactiva, los usuarios normales solo podrán usar los ejercicios del catálogo oficial."
    )

    # --- 5. IDENTIDAD Y CONTACTO ---
    nombre_sitio = models.CharField(
        max_length=100,
        default="FitApp",
        verbose_name="Nombre de la Plataforma"
    )
    email_soporte = models.EmailField(
        max_length=100,
        blank=True,
        default="soporte@fitapp.com",
        verbose_name="Email de Soporte"
    )

    actualizado_en = models.DateTimeField(auto_now=True, verbose_name="Última modificación")

    class Meta:
        verbose_name = "Configuración del Sitio"
        verbose_name_plural = "Configuración del Sitio"

    def __str__(self):
        estado_maint = " [MANTENIMIENTO ACTIVO]" if self.modo_mantenimiento else ""
        estado_reg = " [REGISTRO CERRADO]" if not self.registro_abierto else ""
        return f"{self.nombre_sitio} - Configuración Global{estado_maint}{estado_reg}"

    def save(self, *args, **kwargs):
        # Aseguramos que siempre sea el registro único ID=1
        self.pk = 1
        self.id = 1
        super().save(*args, **kwargs)
        cache.set(self.CACHE_KEY, self, timeout=300)

    def delete(self, *args, **kwargs):
        # Prohibir borrar la configuración única
        pass

    @classmethod
    def get_config(cls):
        """
        Obtiene la configuración única desde caché o desde la base de datos (creándola si no existe).
        """
        config = cache.get(cls.CACHE_KEY)
        if config is None:
            config, _ = cls.objects.get_or_create(
                id=1,
                defaults={
                    'nombre_sitio': 'FitApp',
                    'modo_mantenimiento': False,
                    'registro_abierto': True,
                    'usuarios_pueden_crear_ejercicios': True,
                }
            )
            cache.set(cls.CACHE_KEY, config, timeout=300)
        return config
