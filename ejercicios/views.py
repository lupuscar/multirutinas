from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import models
from django.db.models import Max

from .models import Ejercicio, RegistroEjercicio, Serie
from .forms import EjercicioForm


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
    Permite al usuario crear un nuevo ejercicio desde la interfaz web o móvil.
    """
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

        # Récord personal: mayor peso levantado o mayor tiempo registrado
        series_usuario = Serie.objects.filter(registro__usuario=request.user, registro__ejercicio=ejercicio)
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