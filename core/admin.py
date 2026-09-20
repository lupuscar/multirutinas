from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from .models import ConfiguracionSitio


@admin.register(ConfiguracionSitio)
class ConfiguracionSitioAdmin(admin.ModelAdmin):
    fieldsets = (
        ("🛑 Estado del Sitio y Modo Mantenimiento", {
            "description": "Controla el acceso global a la web. Si activas el mantenimiento, solo staff y administradores podrán navegar.",
            "fields": ("modo_mantenimiento", "mensaje_mantenimiento", "tiempo_estimado_reapertura"),
        }),
        ("👥 Registro de Usuarios y Acceso", {
            "description": "Controla si nuevos usuarios pueden darse de alta de forma pública.",
            "fields": ("registro_abierto", "mensaje_registro_cerrado"),
        }),
        ("📢 Avisos Globales (Broadcast Banner)", {
            "description": "Muestra una barra de notificación superior a todos los usuarios logueados.",
            "fields": ("banner_activo", "banner_texto", "banner_tipo"),
        }),
        ("🏋️ Catálogo y Parámetros Deportivos", {
            "description": "Reglas sobre la creación de ejercicios y entrenamientos.",
            "fields": ("usuarios_pueden_crear_ejercicios",),
        }),
        ("🏷️ Identidad y Contacto", {
            "fields": ("nombre_sitio", "email_soporte", "actualizado_en"),
        }),
    )

    readonly_fields = ("actualizado_en",)

    def has_add_permission(self, request):
        # Solo se permite un registro en la base de datos
        return not ConfiguracionSitio.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # La configuración global nunca debe ser eliminada
        return False

    def changelist_view(self, request, extra_context=None):
        # Redirigir directamente al formulario de edición de la configuración única
        config = ConfiguracionSitio.get_config()
        return redirect(reverse("admin:core_configuracionsitio_change", args=[config.id]))
