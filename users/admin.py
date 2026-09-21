from django.contrib import admin
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import path, reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile, LogActividad
from .utils import registrar_log, enviar_correo_activacion, resetear_datos_usuario
from rutinas.models import Rutina
from ejercicios.models import RegistroEjercicio, Ejercicio

User = get_user_model()

# Desregistramos el User por defecto de Django para usar nuestra versión personalizada
admin.site.unregister(User)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Ficha de Atleta y Verificación'
    fk_name = 'user'
    fields = (
        ('tipo_suscripcion', 'email_verificado'),
        ('genero', 'peso', 'altura'),
        ('nivel', 'objetivo'),
        'biografia',
        'fecha_fin_suscripcion'
    )


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        'username',
        'email',
        'first_name',
        'estado_cuenta_badge',
        'is_staff',
        'date_joined',
    )
    list_filter = (
        'is_active',
        'profile__email_verificado',
        'profile__tipo_suscripcion',
        'is_staff',
        'is_superuser',
        'date_joined',
    )
    actions = ['bloquear_usuarios', 'desbloquear_usuarios', 'reenviar_activacion_accion', 'resetear_datos_usuario_accion']
    readonly_fields = ('resetear_datos_link',)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            tiene_mantenimiento = any(fs[0] == 'Zona de Peligro (Mantenimiento)' for fs in fieldsets)
            if not tiene_mantenimiento:
                fieldsets = fieldsets + (
                    ('Zona de Peligro (Mantenimiento)', {
                        'fields': ('resetear_datos_link',),
                        'description': 'Permite restablecer a cero todas las rutinas, registros y ejercicios de este usuario conservando intacto su perfil y credenciales.',
                    }),
                )
        return fieldsets

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<id>/resetear-datos/',
                self.admin_site.admin_view(self.admin_resetear_datos_usuario_view),
                name='auth_user_resetear_datos',
            ),
        ]
        return custom_urls + urls

    @admin.display(description="Restablecer Datos")
    def resetear_datos_link(self, obj):
        if not obj or not obj.pk:
            return "-"
        url = reverse('admin:auth_user_resetear_datos', args=[obj.pk])
        rutinas_count = Rutina.objects.filter(usuario=obj).count()
        registros_count = RegistroEjercicio.objects.filter(usuario=obj).count()
        ejercicios_count = Ejercicio.objects.filter(creado_por=obj).count()
        return format_html(
            '<div style="padding: 6px 0;">'
            '<p style="margin: 0 0 8px 0; color: #6b7280; font-size: 12px;">'
            'Datos actuales: <strong>{}</strong> rutinas, <strong>{}</strong> sesiones y <strong>{}</strong> ejercicios creados.'
            '</p>'
            '<a class="button" href="{}" style="background-color: #dc2626; color: #ffffff !important; font-weight: bold; padding: 6px 14px; border-radius: 6px; text-decoration: none; display: inline-block;">'
            '🗑️ Restablecer datos de este usuario a 0'
            '</a>'
            '</div>',
            rutinas_count, registros_count, ejercicios_count, url
        )

    def admin_resetear_datos_usuario_view(self, request, id):
        user = get_object_or_404(User, pk=id)
        if request.method == 'POST' and request.POST.get('apply') == '1':
            res = resetear_datos_usuario(user, ejecutado_por=request.user, request=request)
            self.message_user(
                request,
                f"✅ Se han restablecido los datos a 0 para {user.username}. "
                f"Eliminadas {res['rutinas']} rutinas, {res['registros']} sesiones ({res['series']} series) "
                f"y {res['ejercicios_personalizados']} ejercicios personalizados. Su perfil se mantiene intacto."
            )
            return redirect('admin:auth_user_change', id)

        users_data = [{
            'user': user,
            'rutinas': Rutina.objects.filter(usuario=user).count(),
            'registros': RegistroEjercicio.objects.filter(usuario=user).count(),
            'ejercicios': Ejercicio.objects.filter(creado_por=user).count(),
        }]

        context = {
            **self.admin_site.each_context(request),
            'title': f'Restablecer datos a 0: {user.username}',
            'users_to_reset': [user],
            'users_data': users_data,
            'cancel_url': reverse('admin:auth_user_change', args=[id]),
        }
        return render(request, 'admin/confirm_reset_users.html', context)

    @admin.action(description="🗑️ Restablecer datos a 0 (conservar solo perfil)")
    def resetear_datos_usuario_accion(self, request, queryset):
        if request.POST.get('apply') == '1':
            count_usuarios = 0
            total_rutinas = 0
            total_registros = 0
            total_series = 0
            total_ejercicios = 0
            for u in queryset:
                res = resetear_datos_usuario(u, ejecutado_por=request.user, request=request)
                count_usuarios += 1
                total_rutinas += res['rutinas']
                total_registros += res['registros']
                total_series += res['series']
                total_ejercicios += res['ejercicios_personalizados']

            self.message_user(
                request,
                f"✅ Se han restablecido los datos a 0 para {count_usuarios} usuario(s). "
                f"Eliminadas {total_rutinas} rutinas, {total_registros} sesiones ({total_series} series) "
                f"y {total_ejercicios} ejercicios personalizados. Sus perfiles se mantienen intactos."
            )
            return None

        # Pantalla intermedia de confirmación
        users_data = []
        for u in queryset:
            users_data.append({
                'user': u,
                'rutinas': Rutina.objects.filter(usuario=u).count(),
                'registros': RegistroEjercicio.objects.filter(usuario=u).count(),
                'ejercicios': Ejercicio.objects.filter(creado_por=u).count(),
            })

        context = {
            **self.admin_site.each_context(request),
            'title': '¿Confirmar restablecimiento de datos a cero?',
            'users_to_reset': queryset,
            'users_data': users_data,
            'action_name': 'resetear_datos_usuario_accion',
            'cancel_url': reverse('admin:auth_user_changelist'),
        }
        return render(request, 'admin/confirm_reset_users.html', context)

    @admin.display(description="Estado de Cuenta")
    def estado_cuenta_badge(self, obj):
        profile = getattr(obj, 'profile', None)
        email_verificado = profile.email_verificado if profile else False

        if obj.is_active and email_verificado:
            color, bg, border, texto = '#065f46', '#d1fae5', '#a7f3d0', '🟢 Activo (Verificado)'
        elif not obj.is_active and not email_verificado:
            color, bg, border, texto = '#92400e', '#fef3c7', '#fde68a', '🟡 Pendiente Verificación'
        elif not obj.is_active and email_verificado:
            color, bg, border, texto = '#991b1b', '#fee2e2', '#fecaca', '🔴 Bloqueado / Deshabilitado'
        else:
            color, bg, border, texto = '#1e40af', '#dbeafe', '#bfdbfe', '🔵 Activo (Sin validar)'

        return format_html(
            '<span style="display:inline-block; padding:3px 10px; font-weight:700; font-size:11px; border-radius:12px; color:{}; background-color:{}; border:1px solid {};">{}</span>',
            color, bg, border, texto
        )

    @admin.action(description="🚫 Bloquear / Deshabilitar usuarios seleccionados")
    def bloquear_usuarios(self, request, queryset):
        # Impedir que el superusuario que ejecuta la acción se bloquee a sí mismo
        queryset_filtrado = queryset.exclude(pk=request.user.pk)
        afectados = queryset_filtrado.update(is_active=False)

        for u in queryset_filtrado:
            registrar_log(
                request=request,
                usuario=u,
                nivel='WARNING',
                tipo='OTRO',
                mensaje=f"Usuario {u.username} ({u.email}) bloqueado/deshabilitado por el administrador {request.user.username}"
            )

        self.message_user(request, f"Se han bloqueado {afectados} usuario(s) correctamente.")

    @admin.action(description="✅ Activar / Desbloquear usuarios seleccionados")
    def desbloquear_usuarios(self, request, queryset):
        afectados = queryset.update(is_active=True)
        Profile.objects.filter(user__in=queryset).update(email_verificado=True)

        for u in queryset:
            registrar_log(
                request=request,
                usuario=u,
                nivel='INFO',
                tipo='OTRO',
                mensaje=f"Usuario {u.username} ({u.email}) activado/desbloqueado por el administrador {request.user.username}"
            )

        self.message_user(request, f"Se han activado y verificado {afectados} usuario(s) correctamente.")

    @admin.action(description="📧 Reenviar correo de activación a pendientes")
    def reenviar_activacion_accion(self, request, queryset):
        enviados = 0
        for u in queryset:
            profile = getattr(u, 'profile', None)
            if not u.is_active or (profile and not profile.email_verificado):
                if enviar_correo_activacion(u, request):
                    enviados += 1
        self.message_user(request, f"Se ha enviado el enlace de activación a {enviados} usuario(s).")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'genero', 'email_verificado', 'tipo_suscripcion', 'peso', 'altura', 'nivel', 'objetivo')
    list_filter = ('genero', 'email_verificado', 'tipo_suscripcion', 'nivel', 'objetivo')
    search_fields = ('user__username', 'user__email', 'biografia')
    actions = ['resetear_datos_profile_accion']

    @admin.action(description="🗑️ Restablecer datos a 0 para usuarios de los perfiles seleccionados")
    def resetear_datos_profile_accion(self, request, queryset):
        users = [p.user for p in queryset if p.user]
        if request.POST.get('apply') == '1':
            count_usuarios = 0
            total_rutinas = 0
            total_registros = 0
            total_series = 0
            total_ejercicios = 0
            for u in users:
                res = resetear_datos_usuario(u, ejecutado_por=request.user, request=request)
                count_usuarios += 1
                total_rutinas += res['rutinas']
                total_registros += res['registros']
                total_series += res['series']
                total_ejercicios += res['ejercicios_personalizados']

            self.message_user(
                request,
                f"✅ Se han restablecido los datos a 0 para {count_usuarios} usuario(s). "
                f"Eliminadas {total_rutinas} rutinas, {total_registros} sesiones ({total_series} series) "
                f"y {total_ejercicios} ejercicios personalizados. Sus perfiles se mantienen intactos."
            )
            return None

        users_data = []
        for u in users:
            users_data.append({
                'user': u,
                'rutinas': Rutina.objects.filter(usuario=u).count(),
                'registros': RegistroEjercicio.objects.filter(usuario=u).count(),
                'ejercicios': Ejercicio.objects.filter(creado_por=u).count(),
            })

        context = {
            **self.admin_site.each_context(request),
            'title': '¿Confirmar restablecimiento de datos a cero?',
            'users_to_reset': users,
            'users_data': users_data,
            'action_name': 'resetear_datos_profile_accion',
            'cancel_url': reverse('admin:users_profile_changelist'),
        }
        return render(request, 'admin/confirm_reset_users.html', context)



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
        return mark_safe('<span style="color:#9ca3af; font-style:italic;">Anónimo</span>')

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
        return mark_safe('<span style="color:#9ca3af;">Sin excepciones registradas.</span>')
