import json
import datetime
from datetime import timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Max, F, ExpressionWrapper, DecimalField, Q
from django.utils import timezone

from ejercicios.models import RegistroEjercicio, Serie, Ejercicio
from rutinas.models import Rutina


@login_required
def dashboard(request):
    """
    Vista principal de analíticas y progreso del usuario:
    - Gamificación: Racha de semanas, tira de calendario semanal (L-D), meta semanal.
    - Siguiente rutina recomendada para hoy.
    - KPIs mensuales y comparativa de tendencia semanal (% vs semana anterior).
    - Salón de Récords Personales (PRs) con estimación de 1RM (Epley).
    - Curva interactiva de progresión de cargas (Chart.js).
    - Distribución por grupo muscular.
    """
    usuario = request.user
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)

    # =====================================================================
    # 1. CÁLCULO DE SEMANA, RACHAS Y HÁBITOS (GAMIFICACIÓN)
    # =====================================================================
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes de esta semana
    fin_semana = inicio_semana + timedelta(days=6)       # Domingo de esta semana

    inicio_semana_ant = inicio_semana - timedelta(days=7) # Lunes semana pasada
    fin_semana_ant = inicio_semana - timedelta(days=1)    # Domingo semana pasada

    # Días entrenados esta semana
    fechas_semana_actual = set(
        RegistroEjercicio.objects.filter(
            usuario=usuario,
            fecha__gte=inicio_semana,
            fecha__lte=fin_semana
        ).values_list('fecha', flat=True).distinct()
    )
    dias_entrenados_semana = len(fechas_semana_actual)

    # Meta semanal desde el perfil del usuario
    meta_semanal = getattr(usuario.profile, 'dias_objetivo_semana', 4) if hasattr(usuario, 'profile') else 4
    if not meta_semanal or meta_semanal < 1:
        meta_semanal = 4
    progreso_meta_pct = min(int((dias_entrenados_semana / meta_semanal) * 100), 100)

    # Tira visual de 7 días (L a D)
    nombres_dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    calendario_semanal = []
    for i in range(7):
        dia_fecha = inicio_semana + timedelta(days=i)
        calendario_semanal.append({
            'nombre': nombres_dias[i],
            'dia_mes': dia_fecha.day,
            'fecha': dia_fecha,
            'entrenado': dia_fecha in fechas_semana_actual,
            'es_hoy': dia_fecha == hoy,
            'es_futuro': dia_fecha > hoy,
        })

    # Racha de semanas consecutivas entrenando (retrocediendo)
    todas_fechas_entrenadas = set(
        RegistroEjercicio.objects.filter(usuario=usuario).values_list('fecha', flat=True).distinct()
    )
    racha_semanas = 0
    semana_a_evaluar = inicio_semana
    if dias_entrenados_semana == 0:
        semana_a_evaluar = inicio_semana_ant

    while True:
        dias_esta_sem = {semana_a_evaluar + timedelta(days=d) for d in range(7)}
        if any(d in todas_fechas_entrenadas for d in dias_esta_sem):
            racha_semanas += 1
            semana_a_evaluar -= timedelta(days=7)
        else:
            break

    # =====================================================================
    # 2. MÉTRICAS CLAVE (KPIS) Y TENDENCIA SEMANAL (+/- %)
    # =====================================================================
    dias_entrenados_mes = RegistroEjercicio.objects.filter(
        usuario=usuario,
        fecha__gte=inicio_mes
    ).values('fecha').distinct().count()

    total_series = Serie.objects.filter(registro__usuario=usuario).count()

    volumen_expr = ExpressionWrapper(F('repeticiones') * F('peso_kg'), output_field=DecimalField())
    volumen_total = Serie.objects.filter(
        registro__usuario=usuario,
        repeticiones__isnull=False,
        peso_kg__isnull=False
    ).aggregate(total=Sum(volumen_expr))['total'] or 0

    total_rutinas = Rutina.objects.filter(usuario=usuario).count()

    # Volumen semana actual vs semana anterior
    vol_sem_actual = Serie.objects.filter(
        registro__usuario=usuario,
        registro__fecha__gte=inicio_semana,
        registro__fecha__lte=fin_semana,
        repeticiones__isnull=False,
        peso_kg__isnull=False
    ).aggregate(v=Sum(volumen_expr))['v'] or 0

    vol_sem_ant = Serie.objects.filter(
        registro__usuario=usuario,
        registro__fecha__gte=inicio_semana_ant,
        registro__fecha__lte=fin_semana_ant,
        repeticiones__isnull=False,
        peso_kg__isnull=False
    ).aggregate(v=Sum(volumen_expr))['v'] or 0

    vol_cambio_pct = None
    if vol_sem_ant > 0:
        vol_cambio_pct = round(float((vol_sem_actual - vol_sem_ant) / vol_sem_ant) * 100, 1)

    # Series semana actual vs semana anterior
    series_sem_actual = Serie.objects.filter(
        registro__usuario=usuario,
        registro__fecha__gte=inicio_semana,
        registro__fecha__lte=fin_semana
    ).count()

    series_sem_ant = Serie.objects.filter(
        registro__usuario=usuario,
        registro__fecha__gte=inicio_semana_ant,
        registro__fecha__lte=fin_semana_ant
    ).count()

    series_cambio_pct = None
    if series_sem_ant > 0:
        series_cambio_pct = round(float((series_sem_actual - series_sem_ant) / series_sem_ant) * 100, 1)

    # Tiempo Activo de Entrenamiento (Total, Mes y Semana)
    tiempo_total_seg = Serie.objects.filter(
        registro__usuario=usuario,
        tiempo_segundos__isnull=False
    ).aggregate(t=Sum('tiempo_segundos'))['t'] or 0

    tiempo_mes_seg = Serie.objects.filter(
        registro__usuario=usuario,
        registro__fecha__gte=inicio_mes,
        tiempo_segundos__isnull=False
    ).aggregate(t=Sum('tiempo_segundos'))['t'] or 0

    tiempo_sem_seg = Serie.objects.filter(
        registro__usuario=usuario,
        registro__fecha__gte=inicio_semana,
        registro__fecha__lte=fin_semana,
        tiempo_segundos__isnull=False
    ).aggregate(t=Sum('tiempo_segundos'))['t'] or 0

    def formatear_segundos(segundos):
        if not segundos or segundos <= 0:
            return "0m"
        horas, rem = divmod(int(segundos), 3600)
        minutos = rem // 60
        if horas > 0:
            return f"{horas}h {minutos}m" if minutos > 0 else f"{horas}h"
        return f"{minutos}m"

    tiempo_total_str = formatear_segundos(tiempo_total_seg)
    tiempo_mes_str = formatear_segundos(tiempo_mes_seg)
    tiempo_sem_str = formatear_segundos(tiempo_sem_seg)

    # Distancia Acumulada de Cardio / Carrera (km)
    km_total = Serie.objects.filter(
        registro__usuario=usuario,
        distancia_km__isnull=False
    ).aggregate(k=Sum('distancia_km'))['k'] or 0

    km_mes = Serie.objects.filter(
        registro__usuario=usuario,
        registro__fecha__gte=inicio_mes,
        distancia_km__isnull=False
    ).aggregate(k=Sum('distancia_km'))['k'] or 0

    km_sem = Serie.objects.filter(
        registro__usuario=usuario,
        registro__fecha__gte=inicio_semana,
        registro__fecha__lte=fin_semana,
        distancia_km__isnull=False
    ).aggregate(k=Sum('distancia_km'))['k'] or 0

    # =====================================================================
    # 3. SALÓN DE RÉCORDS PERSONALES (PRS) ADAPTATIVO POR DISCIPLINA
    # =====================================================================
    todas_series_usuario = Serie.objects.filter(
        registro__usuario=usuario
    ).select_related('registro__ejercicio')

    records_fuerza = {}
    records_tiempo = {}
    records_calistenia = {}

    for s in todas_series_usuario:
        ej = s.registro.ejercicio
        ej_id = ej.id
        fecha_serie = s.registro.fecha

        # 1. Récord de FUERZA (Pesas / Máquinas con kg y reps)
        if s.peso_kg and s.peso_kg > 0 and s.repeticiones and s.repeticiones > 0:
            peso = float(s.peso_kg)
            reps = s.repeticiones
            un_rm = round(peso * (1.0 + (reps / 30.0)), 1)
            if ej_id not in records_fuerza:
                records_fuerza[ej_id] = {
                    'ejercicio': ej,
                    'categoria': 'fuerza',
                    'categoria_label': 'Fuerza',
                    'categoria_icono': 'fa-solid fa-dumbbell',
                    'max_peso': peso,
                    'max_peso_reps': reps,
                    'max_1rm': un_rm,
                    'valor_principal': f"{un_rm} kg",
                    'valor_sub': "1RM Estimado",
                    'detalle': f"{peso} kg × {reps} reps",
                    'fecha': fecha_serie,
                    'orden': un_rm,
                }
            else:
                rec = records_fuerza[ej_id]
                if un_rm > rec['max_1rm']:
                    rec['max_1rm'] = un_rm
                    rec['valor_principal'] = f"{un_rm} kg"
                    rec['max_peso'] = peso
                    rec['max_peso_reps'] = reps
                    rec['detalle'] = f"{peso} kg × {reps} reps"
                    rec['fecha'] = fecha_serie
                    rec['orden'] = un_rm

        # 2. Récord de DISTANCIA / TIEMPO / CARDIO / DEPORTES (Running, Pádel, Danza, Yoga...)
        if (s.distancia_km and s.distancia_km > 0) or (s.tiempo_segundos and s.tiempo_segundos > 0):
            seg = s.tiempo_segundos or 0
            dist = float(s.distancia_km) if s.distancia_km and s.distancia_km > 0 else 0.0

            if dist > 0:
                # Priorizar récord de distancia para corredores
                rec_actual = records_tiempo.get(ej_id)
                if not rec_actual or dist > rec_actual.get('max_distancia', 0):
                    ritmo_str = f" • {s.ritmo_min_km}" if s.ritmo_min_km else ""
                    duracion_txt = f"{round(seg / 60)} min" if seg else ""
                    records_tiempo[ej_id] = {
                        'ejercicio': ej,
                        'categoria': 'tiempo',
                        'categoria_label': 'Carrera & Cardio',
                        'categoria_icono': ej.icono,
                        'max_segundos': seg,
                        'max_distancia': dist,
                        'valor_principal': f"{dist:g} km",
                        'valor_sub': "Mayor Distancia",
                        'detalle': f"{duracion_txt}{ritmo_str}".strip(' • '),
                        'fecha': fecha_serie,
                        'orden': dist * 1000 + seg,
                    }
            elif ej_id not in records_tiempo or seg > records_tiempo[ej_id]['max_segundos']:
                records_tiempo[ej_id] = {
                    'ejercicio': ej,
                    'categoria': 'tiempo',
                    'categoria_label': 'Cardio & Deporte',
                    'categoria_icono': ej.icono,
                    'max_segundos': seg,
                    'max_distancia': 0.0,
                    'valor_principal': formatear_segundos(seg),
                    'valor_sub': "Mayor Duración",
                    'detalle': f"{round(seg / 60)} min continuos",
                    'fecha': fecha_serie,
                    'orden': seg,
                }

        # 3. Récord de CALISTENIA / PESO CORPORAL (Dominadas, Flexiones, Fondos...)
        if (s.peso_kg is None or s.peso_kg == 0) and s.repeticiones and s.repeticiones > 0:
            reps = s.repeticiones
            if ej_id not in records_fuerza and (ej.tipo == 'CAL' or ej.modalidad == 'REPS_PESO'):
                if ej_id not in records_calistenia or reps > records_calistenia[ej_id]['max_reps']:
                    records_calistenia[ej_id] = {
                        'ejercicio': ej,
                        'categoria': 'calistenia',
                        'categoria_label': 'Calistenia',
                        'categoria_icono': 'fa-solid fa-person-walking',
                        'max_reps': reps,
                        'valor_principal': f"{reps} reps",
                        'valor_sub': "Máx. Reps por Serie",
                        'detalle': "Peso corporal",
                        'fecha': fecha_serie,
                        'orden': reps,
                    }

    lista_fuerza = sorted(records_fuerza.values(), key=lambda x: x['orden'], reverse=True)
    lista_tiempo = sorted(records_tiempo.values(), key=lambda x: x['orden'], reverse=True)
    lista_calistenia = sorted(records_calistenia.values(), key=lambda x: x['orden'], reverse=True)

    # Combinamos para la vista general (priorizando los más destacados de cada ámbito)
    records_personales = []
    max_cada = 4
    records_personales.extend(lista_fuerza[:max_cada])
    records_personales.extend(lista_tiempo[:max_cada])
    records_personales.extend(lista_calistenia[:max_cada])

    # =====================================================================
    # 4. SIGUIENTE ENTRENAMIENTO RECOMENDADO (PRIORIDAD POR DÍA ASIGNADO)
    # =====================================================================
    rutinas_usuario = Rutina.objects.filter(usuario=usuario).prefetch_related('ejercicios')
    rutina_sugerida = None

    nombres_dias_completos = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dia_hoy_nombre = nombres_dias_completos[hoy.weekday()]

    if rutinas_usuario.exists():
        rutinas_con_fecha = []
        for rut in rutinas_usuario:
            ej_ids = rut.ejercicios.values_list('id', flat=True)
            ultimo_reg = RegistroEjercicio.objects.filter(
                usuario=usuario,
                ejercicio_id__in=ej_ids
            ).order_by('-fecha').first()

            ultima_fecha = ultimo_reg.fecha if ultimo_reg else None
            es_programada_hoy = rut.toca_hoy
            ya_entrenada_hoy = (ultima_fecha == hoy)

            rutinas_con_fecha.append({
                'rutina': rut,
                'ultima_fecha': ultima_fecha,
                'ejercicios_count': len(ej_ids),
                'es_programada_hoy': es_programada_hoy,
                'ya_entrenada_hoy': ya_entrenada_hoy,
            })

        rutinas_hoy_pendientes = [r for r in rutinas_con_fecha if r['es_programada_hoy'] and not r['ya_entrenada_hoy']]
        if rutinas_hoy_pendientes:
            rutina_sugerida = rutinas_hoy_pendientes[0]
        else:
            rutinas_con_fecha.sort(
                key=lambda x: (x['ultima_fecha'] is not None, x['ultima_fecha'] or datetime.date.min)
            )
            rutina_sugerida = rutinas_con_fecha[0]

    # =====================================================================
    # 5. HISTORIAL DE SESIONES RECIENTES CON ICONOS Y FORMATO HÍBRIDO
    # =====================================================================
    sesiones_recientes = []
    fechas_recientes = RegistroEjercicio.objects.filter(
        usuario=usuario
    ).values_list('fecha', flat=True).distinct().order_by('-fecha')[:5]

    for fecha in fechas_recientes:
        registros_dia = RegistroEjercicio.objects.filter(
            usuario=usuario,
            fecha=fecha
        ).select_related('ejercicio').prefetch_related('series_detalle')

        total_series_dia = sum(r.series_detalle.count() for r in registros_dia)
        nombres_ejercicios = [r.ejercicio.nombre for r in registros_dia]

        # Resumen de actividad principal
        primer_ej = registros_dia[0].ejercicio if registros_dia else None
        icono_dia = primer_ej.icono if primer_ej else 'fa-solid fa-dumbbell'

        sesiones_recientes.append({
            'fecha': fecha,
            'total_ejercicios': len(registros_dia),
            'total_series': total_series_dia,
            'icono': icono_dia,
            'ejercicios_resumen': ", ".join(nombres_ejercicios[:3]) + ("..." if len(nombres_ejercicios) > 3 else ""),
        })

    # =====================================================================
    # 6. CURVA DE PROGRESIÓN UNIVERSAL (FUERZA, TIEMPO Y CALISTENIA)
    # =====================================================================
    ejercicios_con_datos = Ejercicio.objects.filter(
        historial__usuario=usuario
    ).distinct().order_by('nombre')

    datos_progresion = {}
    for ej in ejercicios_con_datos:
        registros = RegistroEjercicio.objects.filter(
            usuario=usuario,
            ejercicio=ej
        ).order_by('fecha', 'id')

        fechas_lista = []
        valores_principales = []
        valores_secundarios = []

        # Caso 1: Ejercicio por Tiempo (Running, Ciclismo, Danza, Yoga, Deportes...)
        if ej.modalidad == 'TIEMPO':
            for reg in registros:
                seg = reg.series_detalle.aggregate(Max('tiempo_segundos'))['tiempo_segundos__max']
                if seg is not None and seg > 0:
                    fechas_lista.append(reg.fecha.strftime('%d/%m/%Y'))
                    valores_principales.append(round(seg / 60.0, 1))

            if fechas_lista:
                datos_progresion[str(ej.id)] = {
                    'nombre': ej.nombre,
                    'tipo_progresion': 'tiempo',
                    'unidad': 'min',
                    'fechas': fechas_lista,
                    'valores': valores_principales,
                    'label_metrica': 'Duración (minutos)',
                    'tiene_secundaria': False,
                }

        # Caso 2 & 3: Calistenia o Fuerza
        else:
            tiene_series_con_peso = Serie.objects.filter(registro__usuario=usuario, registro__ejercicio=ej, peso_kg__gt=0).exists()
            if ej.tipo == 'CAL' or not tiene_series_con_peso:
                for reg in registros:
                    max_reps = reg.series_detalle.aggregate(Max('repeticiones'))['repeticiones__max']
                    tot_reps = reg.series_detalle.aggregate(Sum('repeticiones'))['repeticiones__sum']
                    if max_reps is not None and max_reps > 0:
                        fechas_lista.append(reg.fecha.strftime('%d/%m/%Y'))
                        valores_principales.append(int(max_reps))
                        valores_secundarios.append(int(tot_reps or max_reps))

                if fechas_lista:
                    datos_progresion[str(ej.id)] = {
                        'nombre': ej.nombre,
                        'tipo_progresion': 'calistenia',
                        'unidad': 'reps',
                        'fechas': fechas_lista,
                        'valores': valores_principales,
                        'valores_sec': valores_secundarios,
                        'label_metrica': 'Máx. Reps por Serie',
                        'label_secundaria': 'Reps Totales',
                        'tiene_secundaria': True,
                    }
            else:
                for reg in registros:
                    max_peso = reg.series_detalle.aggregate(Max('peso_kg'))['peso_kg__max']
                    vol_dia = reg.series_detalle.filter(
                        repeticiones__isnull=False,
                        peso_kg__isnull=False
                    ).aggregate(v=Sum(volumen_expr))['v'] or 0

                    if max_peso is not None:
                        fechas_lista.append(reg.fecha.strftime('%d/%m/%Y'))
                        valores_principales.append(float(max_peso))
                        valores_secundarios.append(float(vol_dia))

                if fechas_lista:
                    datos_progresion[str(ej.id)] = {
                        'nombre': ej.nombre,
                        'tipo_progresion': 'fuerza',
                        'unidad': 'kg',
                        'fechas': fechas_lista,
                        'valores': valores_principales,
                        'valores_sec': valores_secundarios,
                        'label_metrica': 'Peso Máximo (kg)',
                        'label_secundaria': 'Volumen Total (kg)',
                        'tiene_secundaria': True,
                    }

    # =====================================================================
    # 7. DISTRIBUCIÓN POR DISCIPLINA Y POR GRUPO MUSCULAR
    # =====================================================================
    # Desglose por Tipo de Actividad / Disciplina
    disciplinas_map = {
        'MAQ': ('Fuerza (Máquinas)', '#4f46e5'),
        'LIB': ('Fuerza (Peso Libre)', '#6366f1'),
        'CAL': ('Calistenia', '#06b6d4'),
        'CAR': ('Cardio', '#10b981'),
        'DEP': ('Deportes (Pádel, etc.)', '#f59e0b'),
        'DAN': ('Danza / Baile', '#ec4899'),
        'OUT': ('Outdoor / Aire Libre', '#14b8a6'),
        'FLL': ('Yoga / Movilidad', '#8b5cf6'),
    }

    distribucion_tipos_raw = RegistroEjercicio.objects.filter(
        usuario=usuario
    ).values('ejercicio__tipo').annotate(total=Count('id')).order_by('-total')

    distribucion_disciplinas_json = []
    for item in distribucion_tipos_raw:
        codigo_tipo = item['ejercicio__tipo']
        nombre_disc, color_disc = disciplinas_map.get(codigo_tipo, ('Otro', '#64748b'))
        distribucion_disciplinas_json.append({
            'nombre': nombre_disc,
            'total': item['total'],
            'color': color_disc,
        })

    # Desglose Anatómico por Grupo Muscular
    distribucion_raw = RegistroEjercicio.objects.filter(
        usuario=usuario
    ).values('ejercicio__grupo_muscular').annotate(total=Count('id')).order_by('-total')

    nombres_grupos = dict(Ejercicio.GRUPO_MUSCULAR_CHOICES)
    distribucion_muscular_json = [
        {
            'nombre': nombres_grupos.get(item['ejercicio__grupo_muscular'], item['ejercicio__grupo_muscular']),
            'total': item['total']
        }
        for item in distribucion_raw
    ]

    context = {
        # Gamificación y Hábitos
        'racha_semanas': racha_semanas,
        'calendario_semanal': calendario_semanal,
        'dias_entrenados_semana': dias_entrenados_semana,
        'meta_semanal': meta_semanal,
        'progreso_meta_pct': progreso_meta_pct,
        'rutina_sugerida': rutina_sugerida,
        'dia_hoy_nombre': dia_hoy_nombre,

        # KPIs Híbridos y Tendencias
        'dias_entrenados_mes': dias_entrenados_mes,
        'tiempo_total_str': tiempo_total_str,
        'tiempo_mes_str': tiempo_mes_str,
        'tiempo_sem_str': tiempo_sem_str,
        'volumen_total': round(volumen_total, 1),
        'vol_sem_actual': round(vol_sem_actual, 1),
        'vol_cambio_pct': vol_cambio_pct,
        'total_series': total_series,
        'series_sem_actual': series_sem_actual,
        'series_cambio_pct': series_cambio_pct,
        'total_rutinas': total_rutinas,
        'km_total': round(float(km_total), 1),
        'km_mes': round(float(km_mes), 1),
        'km_sem': round(float(km_sem), 1),

        # Récords Adaptativos
        'records_personales': records_personales,
        'total_prs_fuerza': len(lista_fuerza),
        'total_prs_tiempo': len(lista_tiempo),
        'total_prs_calistenia': len(lista_calistenia),

        # Historial y Gráficos
        'sesiones_recientes': sesiones_recientes,
        'ejercicios_con_datos': ejercicios_con_datos,
        'datos_progresion_json': json.dumps(datos_progresion),
        'distribucion_disciplinas_json': json.dumps(distribucion_disciplinas_json),
        'distribucion_muscular_json': json.dumps(distribucion_muscular_json),
        'distribucion_json': json.dumps(distribucion_disciplinas_json or distribucion_muscular_json),
        'ejercicios_catalogo_json': json.dumps([
            {
                'id': ej.id,
                'nombre': ej.nombre,
                'modalidad': ej.modalidad,
                'tipo': ej.get_tipo_display(),
                'grupo_muscular': ej.get_grupo_muscular_display(),
                'es_distancia': ej.es_distancia,
            }
            for ej in Ejercicio.objects.filter(Q(creado_por=None) | Q(creado_por=usuario)).order_by('nombre')
        ]),
    }
    return render(request, 'dashboard/dashboard.html', context)