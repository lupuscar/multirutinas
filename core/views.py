from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone

from .models import ConfiguracionSitio
from .forms import ConfiguracionSitioForm
from users.models import LogActividad
from users.utils import registrar_log
from ejercicios.models import Ejercicio
from rutinas.models import Rutina


def es_personal_administrativo(user):
    """Comprueba que el usuario sea staff o superusuario."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(es_personal_administrativo)
def configuracion_sistema_view(request):
    """
    Panel de control web para la gestión de parámetros globales del sistema:
    - Modo Mantenimiento
    - Control de Registro Libre
    - Banner Global de Anuncios
    - Catálogo y reglas deportivas
    - Métricas clave del sistema
    """
    config = ConfiguracionSitio.get_config()

    if request.method == 'POST':
        form = ConfiguracionSitioForm(request.POST, instance=config)
        if form.is_valid():
            instancia = form.save()

            # Registro en auditoría
            registrar_log(
                request=request,
                usuario=request.user,
                nivel='WARNING' if instancia.modo_mantenimiento else 'INFO',
                tipo='PERFIL_EDIT',
                mensaje=(
                    f"Ajustes del sistema actualizados por {request.user.username}. "
                    f"Mantenimiento: {'ON' if instancia.modo_mantenimiento else 'OFF'}, "
                    f"Registro: {'ABIERTO' if instancia.registro_abierto else 'CERRADO'}"
                )
            )

            messages.success(request, "¡Configuración del sistema actualizada correctamente!")
            return redirect('core:configuracion_sistema')
        else:
            messages.error(request, "Se encontraron errores en el formulario. Por favor revísalos.")
    else:
        form = ConfiguracionSitioForm(instance=config)

    # Métricas de resumen para la cabecera del panel
    total_usuarios = User.objects.count()
    total_usuarios_activos = User.objects.filter(is_active=True).count()
    total_ejercicios = Ejercicio.objects.count()
    total_rutinas = Rutina.objects.count()
    total_errores_recientes = LogActividad.objects.filter(
        nivel__in=['ERROR', 'CRITICAL'],
        creado_en__gte=timezone.now() - timedelta(days=7)
    ).count()

    context = {
        'form': form,
        'config': config,
        'stats': {
            'total_usuarios': total_usuarios,
            'total_activos': total_usuarios_activos,
            'total_ejercicios': total_ejercicios,
            'total_rutinas': total_rutinas,
            'total_errores_recientes': total_errores_recientes,
        }
    }
    return render(request, 'core/configuracion_sistema.html', context)


@login_required
@user_passes_test(es_personal_administrativo)
def accion_mantenimiento_view(request, accion):
    """
    Ejecuta acciones de mantenimiento y limpieza a un clic de distancia.
    """
    if request.method != 'POST':
        return redirect('core:configuracion_sistema')

    if accion == 'clearsessions':
        try:
            call_command('clearsessions')
            messages.success(request, "✅ Sesiones caducadas eliminadas correctamente del sistema.")
            registrar_log(
                request=request,
                usuario=request.user,
                nivel='INFO',
                tipo='OTRO',
                mensaje=f"Limpieza de sesiones ejecutada por {request.user.username}"
            )
        except Exception as e:
            messages.error(request, f"Error al limpiar sesiones: {str(e)}")

    elif accion == 'purgar_logs':
        try:
            fecha_limite = timezone.now() - timedelta(days=60)
            eliminados, _ = LogActividad.objects.filter(creado_en__lt=fecha_limite).delete()
            messages.success(request, f"✅ Se han purgado {eliminados} registros de auditoría anteriores a 60 días.")
            registrar_log(
                request=request,
                usuario=request.user,
                nivel='INFO',
                tipo='OTRO',
                mensaje=f"Purga de logs ejecutada por {request.user.username} ({eliminados} eliminados)"
            )
        except Exception as e:
            messages.error(request, f"Error al purgar registros de log: {str(e)}")

    return redirect('core:configuracion_sistema')
