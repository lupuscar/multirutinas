from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Profile, LogActividad


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tipo_suscripcion', 'peso', 'altura', 'nivel', 'objetivo')
    list_filter = ('tipo_suscripcion', 'nivel', 'objetivo')
    search_fields = ('user__username', 'user__email', 'biografia')


@admin.register(LogActividad)
class LogActividadAdmin(admin.ModelAdmin):
    list_display = (
        'creado_en_str',
        'nivel_badge',
        'tipo_badge',
        'usuario_link',
        'metodo_badge',
        'ruta',
        'ip',
        'mensaje_resumen',
    )
    list_filter = ('nivel', 'tipo', 'metodo', 'creado_en')
    search_fields = ('usuario__username', 'usuario__email', 'ip', 'ruta', 'mensaje', 'traceback')
    date_hierarchy = 'creado_en'
    ordering = ('-creado_en',)

    # Los registros de auditoría son de solo lectura para garantizar integridad
    readonly_fields = [
        'usuario',
        'nivel',
        'tipo',
        'ruta',
        'metodo',
        'ip',
        'user_agent',
        'mensaje',
        'traceback_formateado',
        'creado_en',
    ]

    fieldsets = (
        ('Información General del Evento', {
            'fields': ('creado_en', 'nivel', 'tipo', 'usuario', 'mensaje')
        }),
        ('Contexto de Red y Petición HTTP', {
            'fields': ('metodo', 'ruta', 'ip', 'user_agent')
        }),
        ('Diagnóstico Técnico (Excepciones y Fallos)', {
            'fields': ('traceback_formateado',),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        """Los logs solo pueden generarse por el sistema, no manualmente"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Solo los superusuarios pueden depurar o eliminar logs si es necesario"""
        return request.user.is_superuser

    @admin.display(description="Fecha y Hora", ordering='creado_en')
    def creado_en_str(self, obj):
        return obj.creado_en.strftime("%d/%m/%Y %H:%M:%S")

    @admin.display(description="Severidad", ordering='nivel')
    def nivel_badge(self, obj):
        colores = {
            'INFO': ('#10b981', '#ecfdf5', 'Información'),
            'WARNING': ('#f59e0b', '#fffbeb', 'Advertencia'),
            'ERROR': ('#ef4444', '#fef2f2', 'Error 500'),
            'CRITICAL': ('#7c3aed', '#f5f3ff', 'Crítico'),
        }
        color_texto, color_bg, texto = colores.get(obj.nivel, ('#6b7280', '#f3f4f6', obj.nivel))
        return format_html(
            '<span style="display:inline-block; padding:3px 8px; font-weight:700; font-size:11px; border-radius:8px; color:{}; background-color:{}; border:1px solid {};">{}</span>',
            color_texto, color_bg, color_texto, texto
        )

    @admin.display(description="Evento", ordering='tipo')
    def tipo_badge(self, obj):
        return format_html(
            '<span style="font-weight:600; font-size:11px; color:#4f46e5;">{}</span>',
            obj.get_tipo_display()
        )

    @admin.display(description="Usuario", ordering='usuario')
    def usuario_link(self, obj):
        if obj.usuario:
            url = reverse('admin:auth_user_change', args=[obj.usuario.id])
            return format_html('<a href="{}" style="font-weight:600; color:#4f46e5;">{}</a>', url, obj.usuario.username)
        return format_html('<span style="color:#9ca3af; font-style:italic;">Anónimo</span>')

    @admin.display(description="Método", ordering='metodo')
    def metodo_badge(self, obj):
        if not obj.metodo:
            return "-"
        bg = '#e0e7ff' if obj.metodo == 'GET' else ('#fef3c7' if obj.metodo == 'POST' else '#f3f4f6')
        color = '#3730a3' if obj.metodo == 'GET' else ('#92400e' if obj.metodo == 'POST' else '#374151')
        return format_html(
            '<span style="padding:2px 6px; font-size:10px; font-weight:700; border-radius:6px; background-color:{}; color:{};">{}</span>',
            bg, color, obj.metodo
        )

    @admin.display(description="Mensaje")
    def mensaje_resumen(self, obj):
        msg = obj.mensaje or ""
        return msg[:80] + ("..." if len(msg) > 80 else "")

    @admin.display(description="Pila de Error / Traceback")
    def traceback_formateado(self, obj):
        if obj.traceback:
            return format_html(
                '<pre style="background:#111827; color:#f87171; padding:15px; border-radius:10px; font-size:11px; overflow-x:auto; font-family:monospace; line-height:1.4;">{}</pre>',
                obj.traceback
            )
        return format_html('<span style="color:#9ca3af;">Sin excepciones registradas.</span>')
