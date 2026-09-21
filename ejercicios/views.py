import json
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone

from .models import Ejercicio, RegistroEjercicio, Serie
from .forms import EjercicioForm
from core.models import ConfiguracionSitio


def lista_ejercicios(request):
    """
    Muestra el catálogo de ejercicios (oficiales + personalizados del usuario),
    con filtros por búsqueda, grupo muscular, modalidad y origen (todos/míos/oficiales).
    """
    user = request.user
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    grupo = request.GET.get('grupo', '').strip()
    modalidad = request.GET.get('modalidad', '').strip()
    origen = request.GET.get('origen', 'todos').strip()

    if user.is_authenticated:
        qs = Ejercicio.objects.filter(
            models.Q(creado_por=None) | models.Q(creado_por=user)
        )
    else:
        qs = Ejercicio.objects.filter(creado_por=None)

    # Filtrar por origen
    if origen == 'mis_ejercicios' and user.is_authenticated:
        qs = qs.filter(creado_por=user)
    elif origen == 'oficiales':
        qs = qs.filter(creado_por=None)

    # Filtrar por tipo de actividad (Máquina, Peso libre, Deporte, Danza, Aire Libre...)
    if tipo:
        qs = qs.filter(tipo=tipo)

    # Filtrar por grupo muscular
    if grupo:
        qs = qs.filter(grupo_muscular=grupo)

    # Filtrar por modalidad (Reps/Peso vs Tiempo)
    if modalidad:
        qs = qs.filter(modalidad=modalidad)

    # Filtrar por búsqueda textual
    if q:
        qs = qs.filter(nombre__icontains=q)

    # Contadores para pestañas
    total_todos = Ejercicio.objects.filter(models.Q(creado_por=None) | models.Q(creado_por=user)).count() if user.is_authenticated else Ejercicio.objects.filter(creado_por=None).count()
    total_mios = Ejercicio.objects.filter(creado_por=user).count() if user.is_authenticated else 0
    total_oficiales = Ejercicio.objects.filter(creado_por=None).count()

    context = {
        'ejercicios': qs.order_by('nombre'),
        'tipos_ejercicio': Ejercicio.TIPO_CHOICES,
        'grupos_musculares': Ejercicio.GRUPO_MUSCULAR_CHOICES,
        'modalidades': Ejercicio.MODALIDAD_CHOICES,
        'q': q,
        'tipo_actual': tipo,
        'grupo_actual': grupo,
        'modalidad_actual': modalidad,
        'origen_actual': origen,
        'total_todos': total_todos,
        'total_mios': total_mios,
        'total_oficiales': total_oficiales,
    }
    return render(request, 'ejercicios/ejercicio_list.html', context)


@login_required
def crear_ejercicio(request):
    """
    Permite al usuario crear un nuevo ejercicio desde la interfaz web o móvil
    siempre que esté permitido en la configuración global o sea staff.
    """
    config = ConfiguracionSitio.get_config()
    if not config.usuarios_pueden_crear_ejercicios and not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "La creación de ejercicios personalizados está desactivada por el administrador.")
        return redirect('ejercicios:ejercicios')

    if request.method == 'POST':
        form = EjercicioForm(request.POST, request.FILES)
        if form.is_valid():
            ejercicio = form.save(commit=False)
            ejercicio.creado_por = request.user
            ejercicio.save()
            messages.success(request, f"¡Ejercicio '{ejercicio.nombre}' creado con éxito!")
            return redirect('ejercicios:ejercicios')
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = EjercicioForm()

    context = {
        'form': form,
        'es_edicion': False,
    }
    return render(request, 'ejercicios/form_ejercicio.html', context)


@login_required
def editar_ejercicio(request, ejercicio_id):
    """
    Edita un ejercicio personalizado. Solo el creador o un superusuario pueden editarlo.
    """
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)

    # Validar permisos
    if ejercicio.creado_por != request.user and not request.user.is_superuser:
        messages.error(request, "No tienes permiso para modificar este ejercicio oficial.")
        return redirect('ejercicios:ejercicios')

    if request.method == 'POST':
        form = EjercicioForm(request.POST, request.FILES, instance=ejercicio)
        if form.is_valid():
            form.save()
            messages.success(request, f"¡Ejercicio '{ejercicio.nombre}' actualizado correctamente!")
            return redirect('ejercicios:ejercicios')
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = EjercicioForm(instance=ejercicio)

    context = {
        'form': form,
        'ejercicio': ejercicio,
        'es_edicion': True,
    }
    return render(request, 'ejercicios/form_ejercicio.html', context)


@login_required
@require_POST
def eliminar_ejercicio(request, ejercicio_id):
    """
    Elimina un ejercicio creado por el usuario.
    """
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)

    if ejercicio.creado_por != request.user and not request.user.is_superuser:
        messages.error(request, "No puedes eliminar ejercicios del catálogo oficial.")
        return redirect('ejercicios:ejercicios')

    nombre = ejercicio.nombre
    ejercicio.delete()
    messages.success(request, f"Ejercicio '{nombre}' eliminado correctamente.")
    return redirect('ejercicios:ejercicios')


def detalle_ejercicio(request, ejercicio_id):
    """
    Muestra la ficha técnica completa del ejercicio, su foto/vídeo,
    y el récord personal o historial reciente del usuario en este ejercicio.
    """
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)

    record_personal = None
    historial_reciente = []

    if request.user.is_authenticated:
        registros = RegistroEjercicio.objects.filter(
            usuario=request.user,
            ejercicio=ejercicio
        ).prefetch_related('series_detalle').order_by('-fecha')[:5]

        # Récord personal: mayor peso levantado, mayor tiempo registrado o mayor distancia en km
        series_usuario = Serie.objects.filter(registro__usuario=request.user, registro__ejercicio=ejercicio)
        if ejercicio.es_distancia or series_usuario.filter(distancia_km__gt=0).exists():
            max_dist = series_usuario.aggregate(Max('distancia_km'))['distancia_km__max']
            if max_dist:
                serie_max = series_usuario.filter(distancia_km=max_dist).order_by('-tiempo_segundos').first()
                ritmo_txt = f" ({serie_max.ritmo_min_km})" if serie_max and serie_max.ritmo_min_km else ""
                record_personal = f"{max_dist} km{ritmo_txt}"

        if not record_personal:
            if ejercicio.modalidad == 'TIEMPO':
                max_tiempo = series_usuario.aggregate(Max('tiempo_segundos'))['tiempo_segundos__max']
                if max_tiempo:
                    mins, secs = divmod(max_tiempo, 60)
                    if mins >= 60:
                        horas, mins = divmod(mins, 60)
                        record_personal = f"{horas}h {mins}m" if mins else f"{horas}h"
                    elif mins:
                        record_personal = f"{mins} min {secs}s" if secs else f"{mins} min"
                    else:
                        record_personal = f"{secs} segundos"
            else:
                max_peso = series_usuario.aggregate(Max('peso_kg'))['peso_kg__max']
                if max_peso:
                    record_personal = f"{max_peso} kg"

        historial_reciente = registros

    context = {
        'ejercicio': ejercicio,
        'record_personal': record_personal,
        'historial_reciente': historial_reciente,
    }
    return render(request, 'ejercicios/detalle_ejercicio.html', context)


@login_required
@require_POST
def registrar_sesion_libre(request, ejercicio_id=None):
    """
    Permite registrar un entrenamiento o actividad suelta (ej. correr 45 minutos,
    un partido de pádel o una sesión de pesas fuera de una rutina programada).
    Crea el RegistroEjercicio y las Series correspondientes, impactando inmediatamente
    en las rachas, el calendario de 7 días y las analíticas del Dashboard.
    """
    try:
        if request.content_type == 'application/json':
            datos = json.loads(request.body)
        else:
            datos = request.POST

        ej_id = ejercicio_id or datos.get('ejercicio_id')
        if not ej_id:
            msg = "Debes indicar un ejercicio válido."
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('ejercicios:ejercicios')

        ejercicio = get_object_or_404(Ejercicio, id=ej_id)

        # Fecha (por defecto hoy, o parseada)
        fecha_str = datos.get('fecha')
        if fecha_str:
            try:
                fecha_sesion = datetime.date.fromisoformat(str(fecha_str).strip())
            except Exception:
                fecha_sesion = timezone.now().date()
        else:
            fecha_sesion = timezone.now().date()

        notas = datos.get('notas', '').strip()
        etiqueta = datos.get('etiqueta', '').strip() or 'Actividad Libre'

        with transaction.atomic():
            registro = RegistroEjercicio.objects.create(
                usuario=request.user,
                ejercicio=ejercicio,
                fecha=fecha_sesion,
                notas=notas,
                etiqueta=etiqueta
            )

            # Distancia en km opcional (ej. running, cinta, ciclismo, senderismo)
            distancia_raw = datos.get('distancia_km')
            distancia_km = None
            if distancia_raw not in (None, '', 'null'):
                try:
                    distancia_val = float(str(distancia_raw).replace(',', '.').strip())
                    if distancia_val > 0:
                        distancia_km = round(distancia_val, 2)
                except (ValueError, TypeError):
                    distancia_km = None

            # Si es por tiempo (running, senderismo, deportes, danza, etc.)
            if ejercicio.modalidad == 'TIEMPO':
                duracion_minutos = float(datos.get('duracion_minutos') or 0)
                segundos_directos = int(datos.get('tiempo_segundos') or 0)
                segundos_totales = int(duracion_minutos * 60) if duracion_minutos > 0 else segundos_directos
                if segundos_totales <= 0:
                    segundos_totales = 1800  # 30 min por defecto si vino vacío

                Serie.objects.create(
                    registro=registro,
                    numero_serie=1,
                    tiempo_segundos=segundos_totales,
                    repeticiones=None,
                    peso_kg=None,
                    distancia_km=distancia_km
                )
            else:
                # Modalidad Reps + Peso
                series_data = datos.get('series')
                if isinstance(series_data, list) and len(series_data) > 0:
                    for idx, s in enumerate(series_data, start=1):
                        reps = int(s.get('repeticiones') or 10)
                        peso = float(s.get('peso_kg')) if s.get('peso_kg') not in (None, '', 'null') else None
                        dist_s_raw = s.get('distancia_km')
                        dist_s = float(dist_s_raw) if dist_s_raw not in (None, '', 'null') else distancia_km
                        Serie.objects.create(
                            registro=registro,
                            numero_serie=idx,
                            repeticiones=reps,
                            peso_kg=peso,
                            distancia_km=dist_s
                        )
                else:
                    # Datos planos desde formulario simple
                    num_series = int(datos.get('series_totales') or 1)
                    reps_gral = int(datos.get('repeticiones') or 10)
                    peso_raw = datos.get('peso_kg')
                    peso_gral = float(peso_raw) if peso_raw not in (None, '', 'null') else None

                    for idx in range(1, num_series + 1):
                        Serie.objects.create(
                            registro=registro,
                            numero_serie=idx,
                            repeticiones=reps_gral,
                            peso_kg=peso_gral,
                            distancia_km=distancia_km
                        )

        messages.success(request, f"¡Sesión de '{ejercicio.nombre}' registrada correctamente!")
        if request.content_type == 'application/json':
            return JsonResponse({
                'status': 'success',
                'message': f"Sesión de '{ejercicio.nombre}' guardada con éxito.",
                'redirect_url': reverse('ejercicios:detalle_ejercicio', args=[ejercicio.id])
            })
        return redirect('ejercicios:detalle_ejercicio', ejercicio_id=ejercicio.id)

    except Exception as e:
        if request.content_type == 'application/json':
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        messages.error(request, f"Error al registrar la actividad: {e}")
        return redirect('ejercicios:ejercicios')