import json
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.contrib import messages
from django.utils import timezone

from .models import Rutina, RutinaEjercicio
from .recomendador import generar_plan_recomendado
from ejercicios.models import Ejercicio, RegistroEjercicio, Serie
from users.models import Profile
from core.models import ConfiguracionSitio


# =====================================================================
# LISTADO DE RUTINAS
# =====================================================================
@login_required
def lista_rutinas_view(request):
    """
    Muestra todas las rutinas creadas por el usuario actual con métricas de ejercicios.
    """
    mis_rutinas = Rutina.objects.filter(usuario=request.user).prefetch_related('ejercicios', 'rutinaejercicio_set')
    
    context = {
        'rutinas': mis_rutinas
    }
    return render(request, 'rutinas/lista_rutinas.html', context)


# =====================================================================
# CREADOR Y EDITOR DE RUTINAS
# =====================================================================
@login_required
def crear_rutina_view(request):
    """
    Permite al usuario crear una rutina interactiva desde el móvil o PC,
    seleccionando o creando ejercicios y definiendo series, reps o tiempo.
    """
    if request.method == 'POST':
        try:
            # Puede recibir tanto JSON como formulario estándar
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = {
                    'nombre': request.POST.get('nombre'),
                    'descripcion': request.POST.get('descripcion', ''),
                    'ejercicios': json.loads(request.POST.get('ejercicios_json', '[]'))
                }

            nombre = data.get('nombre', '').strip()
            if not nombre:
                return JsonResponse({'status': 'error', 'message': 'El nombre de la rutina es obligatorio.'}, status=400)

            dias_semana_raw = data.get('dias_semana', [])
            if isinstance(dias_semana_raw, list):
                dias_semana_str = ",".join(str(d) for d in sorted(dias_semana_raw) if str(d).isdigit())
            else:
                dias_semana_str = str(dias_semana_raw or '').strip()

            with transaction.atomic():
                rutina = Rutina.objects.create(
                    usuario=request.user,
                    nombre=nombre,
                    descripcion=data.get('descripcion', '').strip(),
                    dias_semana=dias_semana_str
                )

                ejercicios_data = data.get('ejercicios', [])
                for index, item in enumerate(ejercicios_data, start=1):
                    ejercicio_id = item.get('ejercicio_id')
                    series = int(item.get('series_objetivo') or 3)
                    reps = int(item.get('repeticiones_objetivo') or 10) if item.get('repeticiones_objetivo') else None
                    tiempo = int(item.get('tiempo_objetivo_segundos') or 0) if item.get('tiempo_objetivo_segundos') else None

                    peso_raw = item.get('peso_objetivo')
                    peso = float(peso_raw) if peso_raw not in (None, '', 'null') else None

                    RutinaEjercicio.objects.create(
                        rutina=rutina,
                        ejercicio_id=ejercicio_id,
                        orden=index,
                        series_objetivo=series,
                        repeticiones_objetivo=reps,
                        peso_objetivo=peso,
                        tiempo_objetivo_segundos=tiempo
                    )

            messages.success(request, f"¡Rutina '{rutina.nombre}' creada con éxito!")
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'success', 'redirect_url': '/rutinas/'})
            return redirect('rutinas:lista_rutinas')

        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            messages.error(request, f"Error al crear la rutina: {e}")

    # Catálogo de ejercicios disponibles: globales o creados por este usuario
    ejercicios = Ejercicio.objects.filter(
        models.Q(creado_por=None) | models.Q(creado_por=request.user)
    ).order_by('nombre')

    ejercicios_json = [
        {
            'id': ej.id,
            'nombre': ej.nombre,
            'modalidad': ej.modalidad,
            'grupo_muscular': ej.get_grupo_muscular_display(),
            'tipo': ej.get_tipo_display()
        }
        for ej in ejercicios
    ]

    dias_semana_opciones = [
        (0, 'Lun', 'Lunes'),
        (1, 'Mar', 'Martes'),
        (2, 'Mié', 'Miércoles'),
        (3, 'Jue', 'Jueves'),
        (4, 'Vie', 'Viernes'),
        (5, 'Sáb', 'Sábado'),
        (6, 'Dom', 'Domingo'),
    ]

    context = {
        'ejercicios': ejercicios,
        'ejercicios_json': json.dumps(ejercicios_json),
        'dias_semana_json': json.dumps([]),
        'dias_semana_opciones': dias_semana_opciones,
        'grupos_musculares': Ejercicio.GRUPO_MUSCULAR_CHOICES,
        'tipos_ejercicio': Ejercicio.TIPO_CHOICES,
        'modalidades': Ejercicio.MODALIDAD_CHOICES,
        'es_edicion': False,
    }
    return render(request, 'rutinas/form_rutina.html', context)


@login_required
def editar_rutina_view(request, rutina_id):
    """
    Edita una rutina existente del usuario y sus ejercicios asignados.
    """
    rutina = get_object_or_404(Rutina, id=rutina_id, usuario=request.user)

    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = {
                    'nombre': request.POST.get('nombre'),
                    'descripcion': request.POST.get('descripcion', ''),
                    'dias_semana': json.loads(request.POST.get('dias_semana_json', '[]')),
                    'ejercicios': json.loads(request.POST.get('ejercicios_json', '[]'))
                }

            nombre = data.get('nombre', '').strip()
            if not nombre:
                return JsonResponse({'status': 'error', 'message': 'El nombre es obligatorio.'}, status=400)

            dias_semana_raw = data.get('dias_semana', [])
            if isinstance(dias_semana_raw, list):
                dias_semana_str = ",".join(str(d) for d in sorted(dias_semana_raw) if str(d).isdigit())
            else:
                dias_semana_str = str(dias_semana_raw or '').strip()

            with transaction.atomic():
                rutina.nombre = nombre
                rutina.descripcion = data.get('descripcion', '').strip()
                rutina.dias_semana = dias_semana_str
                rutina.save()

                # Reemplazamos los ejercicios con la nueva configuración
                rutina.rutinaejercicio_set.all().delete()
                for index, item in enumerate(data.get('ejercicios', []), start=1):
                    peso_raw = item.get('peso_objetivo')
                    peso = float(peso_raw) if peso_raw not in (None, '', 'null') else None

                    RutinaEjercicio.objects.create(
                        rutina=rutina,
                        ejercicio_id=item.get('ejercicio_id'),
                        orden=index,
                        series_objetivo=int(item.get('series_objetivo') or 3),
                        repeticiones_objetivo=int(item.get('repeticiones_objetivo') or 10) if item.get('repeticiones_objetivo') else None,
                        peso_objetivo=peso,
                        tiempo_objetivo_segundos=int(item.get('tiempo_objetivo_segundos') or 0) if item.get('tiempo_objetivo_segundos') else None
                    )

            messages.success(request, "¡Rutina actualizada correctamente!")
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'success', 'redirect_url': '/rutinas/'})
            return redirect('rutinas:lista_rutinas')

        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            messages.error(request, f"Error al actualizar la rutina: {e}")

    # Catálogo de ejercicios
    ejercicios = Ejercicio.objects.filter(
        models.Q(creado_por=None) | models.Q(creado_por=request.user)
    ).order_by('nombre')

    ejercicios_json = [
        {
            'id': ej.id,
            'nombre': ej.nombre,
            'modalidad': ej.modalidad,
            'grupo_muscular': ej.get_grupo_muscular_display(),
            'tipo': ej.get_tipo_display()
        }
        for ej in ejercicios
    ]

    # Ejercicios precargados en la rutina actual
    rutina_ejercicios_actuales = [
        {
            'ejercicio_id': re.ejercicio.id,
            'nombre': re.ejercicio.nombre,
            'modalidad': re.ejercicio.modalidad,
            'grupo_muscular': re.ejercicio.get_grupo_muscular_display(),
            'series_objetivo': re.series_objetivo or 3,
            'repeticiones_objetivo': re.repeticiones_objetivo or 10,
            'peso_objetivo': str(re.peso_objetivo) if re.peso_objetivo is not None else '',
            'tiempo_objetivo_segundos': re.tiempo_objetivo_segundos or 45,
        }
        for re in rutina.rutinaejercicio_set.select_related('ejercicio').order_by('orden')
    ]

    dias_semana_opciones = [
        (0, 'Lun', 'Lunes'),
        (1, 'Mar', 'Martes'),
        (2, 'Mié', 'Miércoles'),
        (3, 'Jue', 'Jueves'),
        (4, 'Vie', 'Viernes'),
        (5, 'Sáb', 'Sábado'),
        (6, 'Dom', 'Domingo'),
    ]

    context = {
        'rutina': rutina,
        'ejercicios': ejercicios,
        'ejercicios_json': json.dumps(ejercicios_json),
        'rutina_ejercicios_json': json.dumps(rutina_ejercicios_actuales),
        'dias_semana_json': json.dumps(rutina.lista_dias_numeros),
        'dias_semana_opciones': dias_semana_opciones,
        'grupos_musculares': Ejercicio.GRUPO_MUSCULAR_CHOICES,
        'tipos_ejercicio': Ejercicio.TIPO_CHOICES,
        'modalidades': Ejercicio.MODALIDAD_CHOICES,
        'es_edicion': True,
    }
    return render(request, 'rutinas/form_rutina.html', context)


@login_required
@require_POST
def eliminar_rutina_view(request, rutina_id):
    """
    Elimina una rutina perteneciente al usuario autenticado.
    """
    rutina = get_object_or_404(Rutina, id=rutina_id, usuario=request.user)
    nombre = rutina.nombre
    rutina.delete()
    messages.success(request, f"Rutina '{nombre}' eliminada correctamente.")
    return redirect('rutinas:lista_rutinas')


# =====================================================================
# CREACIÓN RÁPIDA DE EJERCICIOS PERSONALIZADOS (AJAX)
# =====================================================================
@login_required
@require_POST
def crear_ejercicio_rapido_ajax(request):
    """
    Permite al usuario crear un ejercicio personalizado al vuelo desde el modal
    del móvil y agregarlo inmediatamente a su rutina.
    """
    try:
        config = ConfiguracionSitio.get_config()
        if not config.usuarios_pueden_crear_ejercicios and not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({'status': 'error', 'message': 'La creación de ejercicios personalizados está desactivada por el administrador.'}, status=403)

        data = json.loads(request.body)
        nombre = data.get('nombre', '').strip()
        modalidad = data.get('modalidad', 'REPS_PESO')
        grupo_muscular = data.get('grupo_muscular', 'PEC')
        tipo = data.get('tipo', 'LIB')

        if not nombre:
            return JsonResponse({'status': 'error', 'message': 'El nombre del ejercicio es obligatorio.'}, status=400)

        ejercicio = Ejercicio.objects.create(
            nombre=nombre,
            modalidad=modalidad,
            grupo_muscular=grupo_muscular,
            tipo=tipo,
            creado_por=request.user,
            definicion="Ejercicio personalizado por el usuario."
        )

        return JsonResponse({
            'status': 'success',
            'ejercicio': {
                'id': ejercicio.id,
                'nombre': ejercicio.nombre,
                'modalidad': ejercicio.modalidad,
                'grupo_muscular': ejercicio.get_grupo_muscular_display(),
                'tipo': ejercicio.get_tipo_display()
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# =====================================================================
# EJECUCIÓN ("MODO GYM") Y AUTOGUARDADO DE SERIES
# =====================================================================
def obtener_datos_ultimo_entrenamiento(usuario, ejercicio_id):
    """
    Busca el último entrenamiento del usuario para un ejercicio específico
    y devuelve las repeticiones, peso y tiempo de las series anteriores.
    """
    ultimo_registro = RegistroEjercicio.objects.filter(
        usuario=usuario,
        ejercicio_id=ejercicio_id
    ).order_by('-id').first()

    datos_iniciales = []
    if ultimo_registro:
        series_anteriores = Serie.objects.filter(registro=ultimo_registro).order_by('numero_serie')
        for serie in series_anteriores:
            peso_crudo = serie.peso_kg if serie.peso_kg is not None else 0.0
            datos_iniciales.append({
                'numero_serie': serie.numero_serie,
                'repeticiones': serie.repeticiones,
                'peso_kg': str(peso_crudo) if serie.peso_kg is not None else '',
                'tiempo_segundos': serie.tiempo_segundos or '',
            })
    return datos_iniciales


@login_required
def iniciar_rutina_view(request, rutina_id):
    """
    Prepara la sesión en 'Modo Gym' para móvil:
    Carga los ejercicios de la rutina y las sugerencias basadas en el historial
    o las metas objetivo de la rutina (reps, peso o tiempo).
    """
    rutina = get_object_or_404(Rutina, id=rutina_id, usuario=request.user)
    ejercicios_rutina = RutinaEjercicio.objects.filter(rutina=rutina).select_related('ejercicio').order_by('orden')

    rutina_preparada = []

    for item in ejercicios_rutina:
        historial = obtener_datos_ultimo_entrenamiento(request.user, item.ejercicio.id)
        num_series = item.series_objetivo or 3
        series_sugeridas = []

        for num_s in range(1, num_series + 1):
            serie_prev = next((s for s in historial if s.get('numero_serie') == num_s), None) if historial else None

            peso_objetivo_str = str(item.peso_objetivo) if item.peso_objetivo is not None else ''
            
            if serie_prev:
                reps = serie_prev.get('repeticiones') or item.repeticiones_objetivo or 10
                peso = serie_prev.get('peso_kg') or peso_objetivo_str
                tiempo = serie_prev.get('tiempo_segundos') or item.tiempo_objetivo_segundos or 45
            else:
                reps = item.repeticiones_objetivo or 10
                peso = peso_objetivo_str
                tiempo = item.tiempo_objetivo_segundos or 45

            series_sugeridas.append({
                'numero_serie': num_s,
                'repeticiones': reps,
                'peso_kg': peso,
                'peso_anterior': serie_prev.get('peso_kg') if serie_prev else '',
                'reps_anteriores': serie_prev.get('repeticiones') if serie_prev else None,
                'tiempo_segundos': tiempo,
                'completado': False
            })

        rutina_preparada.append({
            'ejercicio_id': item.ejercicio.id,
            'ejercicio_nombre': item.ejercicio.nombre,
            'modalidad': item.ejercicio.modalidad,
            'grupo_muscular': item.ejercicio.get_grupo_muscular_display(),
            'series_sugeridas': series_sugeridas
        })

    context = {
        'rutina': rutina,
        'rutina_preparada': rutina_preparada,
        'rutina_preparada_json': json.dumps(rutina_preparada),
    }
    return render(request, 'rutinas/ejecutar_rutina.html', context)


@login_required
@require_POST
def guardar_serie_ajax(request):
    """
    Guarda o actualiza una serie específica mediante AJAX de manera instantánea.
    Soporta repeticiones, peso y tiempo en segundos.
    """
    try:
        datos = json.loads(request.body)
        ejercicio_id = datos.get('ejercicio_id')
        serie_num = int(datos.get('numero_serie', 1))
        repeticiones = datos.get('repeticiones')
        peso = datos.get('peso')
        tiempo_segundos = datos.get('tiempo_segundos')
        rutina_nombre = datos.get('rutina_nombre', 'Entrenamiento')

        ejercicio_obj = get_object_or_404(Ejercicio, id=ejercicio_id)

        # Buscamos o creamos el registro general de la sesión de hoy
        hoy = timezone.now().date()
        registro, _ = RegistroEjercicio.objects.get_or_create(
            usuario=request.user,
            ejercicio=ejercicio_obj,
            fecha=hoy,
            defaults={'etiqueta': f"Sesión: {rutina_nombre}"}
        )

        # Valores limpios
        reps_val = int(repeticiones) if repeticiones is not None and str(repeticiones).strip() != '' else None
        peso_val = float(peso) if peso is not None and str(peso).strip() != '' else None
        tiempo_val = int(tiempo_segundos) if tiempo_segundos is not None and str(tiempo_segundos).strip() != '' else None

        # Guardamos o actualizamos la serie
        serie, creada = Serie.objects.get_or_create(
            registro=registro,
            numero_serie=serie_num,
            defaults={
                'repeticiones': reps_val,
                'peso_kg': peso_val,
                'tiempo_segundos': tiempo_val,
            }
        )

        if not creada:
            serie.repeticiones = reps_val
            serie.peso_kg = peso_val
            serie.tiempo_segundos = tiempo_val
            serie.save()

        return JsonResponse({
            'status': 'success',
            'message': f"Serie {serie_num} guardada correctamente",
            'serie_id': serie.id
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def finalizar_entrenamiento_ajax(request):
    """
    Finaliza la sesión de entrenamiento y redirige al dashboard.
    """
    messages.success(request, "¡Entrenamiento completado y registrado con éxito! Gran trabajo hoy 💪")
    return JsonResponse({'status': 'success', 'redirect_url': '/dashboard/'})


# =====================================================================
# RECOMENDADOR AUTOMÁTICO E INTELIGENTE DE RUTINAS
# =====================================================================
@login_required
def recomendador_rutinas_view(request):
    """
    Asistente interactivo de recomendación de rutinas personalizadas.
    Calcula y previsualiza un plan de entrenamiento adaptado al perfil (edad, género, nivel,
    objetivo principal y meta semanal), permitiendo ajustarlo en tiempo real.
    """
    perfil = getattr(request.user, 'profile', None)

    # Si es petición AJAX o POST para recalcular el plan al vuelo
    if request.method == 'POST' or request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        prefs = {}
        if request.body and request.content_type == 'application/json':
            try:
                prefs = json.loads(request.body)
            except Exception:
                prefs = {}
        else:
            for k in ['dias_semana', 'objetivo', 'nivel', 'edad', 'genero', 'equipamiento', 'duracion']:
                val = request.POST.get(k) or request.GET.get(k)
                if val is not None and val != '':
                    prefs[k] = val

        plan = generar_plan_recomendado(request.user, prefs)
        return JsonResponse({'status': 'success', 'plan': plan})

    # Carga inicial de la página con los valores del perfil del usuario
    plan_inicial = generar_plan_recomendado(request.user)

    context = {
        'plan_inicial': plan_inicial,
        'plan_json': json.dumps(plan_inicial),
        'perfil': perfil,
        'objetivos_choices': Profile.OBJETIVOS_FITNESS if perfil else [
            ('HIP', 'Hipertrofia / Ganar Músculo'),
            ('DEF', 'Definición / Perder Grasa'),
            ('FUE', 'Fuerza / Rendimiento'),
            ('SAL', 'Salud y Condición Física'),
            ('RES', 'Resistencia y Cardio'),
        ],
        'niveles_choices': Profile.NIVEL_EXPERIENCIA if perfil else [
            ('PR', 'Principiante'),
            ('IN', 'Intermedio'),
            ('AV', 'Avanzado'),
        ],
        'genero_choices': Profile.GENERO_CHOICES if perfil else [
            ('H', 'Hombre'),
            ('M', 'Mujer'),
            ('O', 'Otro / Prefiero no decir'),
        ],
    }
    return render(request, 'rutinas/recomendador.html', context)


@login_required
@require_POST
def guardar_plan_recomendado_ajax(request):
    """
    Guarda atómicamente el plan recomendado completo (o una rutina individual del plan)
    en las tablas Rutina y RutinaEjercicio del usuario.
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = json.loads(request.POST.get('data', '{}'))

        rutinas_data = data.get('rutinas', [])
        if not rutinas_data and 'rutina' in data:
            rutinas_data = [data['rutina']]

        if not rutinas_data:
            return JsonResponse({'status': 'error', 'message': 'No se enviaron rutinas para guardar.'}, status=400)

        rutinas_creadas = []
        with transaction.atomic():
            for r_item in rutinas_data:
                nombre = r_item.get('nombre', 'Rutina Recomendada').strip()
                descripcion = r_item.get('descripcion', '').strip()
                dias_semana = str(r_item.get('dias_semana', '')).strip()

                rutina = Rutina.objects.create(
                    usuario=request.user,
                    nombre=nombre,
                    descripcion=descripcion,
                    dias_semana=dias_semana
                )

                ejercicios = r_item.get('ejercicios', [])
                for index, ej_item in enumerate(ejercicios, start=1):
                    ej_id = ej_item.get('ejercicio_id')
                    series = int(ej_item.get('series_objetivo') or 3)
                    reps = int(ej_item.get('repeticiones_objetivo')) if ej_item.get('repeticiones_objetivo') else None
                    tiempo = int(ej_item.get('tiempo_objetivo_segundos')) if ej_item.get('tiempo_objetivo_segundos') else None
                    peso = float(ej_item['peso_objetivo']) if ej_item.get('peso_objetivo') else None

                    RutinaEjercicio.objects.create(
                        rutina=rutina,
                        ejercicio_id=ej_id,
                        orden=index,
                        series_objetivo=series,
                        repeticiones_objetivo=reps,
                        peso_objetivo=peso,
                        tiempo_objetivo_segundos=tiempo
                    )

                rutinas_creadas.append(rutina.nombre)

        plural = "s" if len(rutinas_creadas) > 1 else ""
        mensaje = f"¡Se han guardado {len(rutinas_creadas)} rutina{plural} en tus entrenamientos! Listas para usar en el gimnasio."
        messages.success(request, mensaje)

        return JsonResponse({
            'status': 'success',
            'message': mensaje,
            'rutinas_creadas': rutinas_creadas,
            'redirect_url': '/rutinas/'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)