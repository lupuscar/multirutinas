import json
import datetime
from datetime import timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Max, F, ExpressionWrapper, DecimalField
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

    # =====================================================================
    # 3. SALÓN DE RÉCORDS PERSONALES (PRS) Y ESTIMACIÓN DE 1RM
    # =====================================================================
    series_usuario = Serie.objects.filter(
        registro__usuario=usuario,
        peso_kg__gt=0,
        repeticiones__gt=0
    ).select_related('registro__ejercicio')

    ejercicios_records = {}
    for s in series_usuario:
        ej_id = s.registro.ejercicio_id
        peso = float(s.peso_kg)
        reps = s.repeticiones
        # Fórmula de Epley: 1RM = Peso * (1 + reps / 30)
        un_rm = round(peso * (1.0 + (reps / 30.0)), 1)
        fecha_serie = s.registro.fecha

        if ej_id not in ejercicios_records:
            ejercicios_records[ej_id] = {
                'ejercicio': s.registro.ejercicio,
                'max_peso': peso,
                'max_peso_reps': reps,
                'max_peso_fecha': fecha_serie,
                'max_1rm': un_rm,
                'max_1rm_peso': peso,
                'max_1rm_reps': reps,
                'max_1rm_fecha': fecha_serie,
            }
        else:
            rec = ejercicios_records[ej_id]
            if peso > rec['max_peso']:
                rec['max_peso'] = peso
                rec['max_peso_reps'] = reps
                rec['max_peso_fecha'] = fecha_serie
            if un_rm > rec['max_1rm']:
                rec['max_1rm'] = un_rm
                rec['max_1rm_peso'] = peso
                rec['max_1rm_reps'] = reps
                rec['max_1rm_fecha'] = fecha_serie

    # Ordenamos por mayor 1RM y limitamos a los 6 más destacados
    records_personales = sorted(
        ejercicios_records.values(),
        key=lambda x: x['max_1rm'],
        reverse=True
    )[:6]

    # =====================================================================
    # 4. SIGUIENTE ENTRENAMIENTO RECOMENDADO
    # =====================================================================
    rutinas_usuario = Rutina.objects.filter(usuario=usuario).prefetch_related('ejercicios')
    rutina_sugerida = None

    if rutinas_usuario.exists():
        rutinas_con_fecha = []
        for rut in rutinas_usuario:
            ej_ids = rut.ejercicios.values_list('id', flat=True)
            ultimo_reg = RegistroEjercicio.objects.filter(
                usuario=usuario,
                ejercicio_id__in=ej_ids
            ).order_by('-fecha').first()

            ultima_fecha = ultimo_reg.fecha if ultimo_reg else None
            rutinas_con_fecha.append({
                'rutina': rut,
                'ultima_fecha': ultima_fecha,
                'ejercicios_count': len(ej_ids),
            })

        # Se sugiere la que hace más tiempo que no se entrena (o nunca entrenada)
        rutinas_con_fecha.sort(
            key=lambda x: (x['ultima_fecha'] is not None, x['ultima_fecha'] or datetime.date.min)
        )
        rutina_sugerida = rutinas_con_fecha[0]

    # =====================================================================
    # 5. HISTORIAL DE SESIONES RECIENTES
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

        sesiones_recientes.append({
            'fecha': fecha,
            'total_ejercicios': len(registros_dia),
            'total_series': total_series_dia,
            'ejercicios_resumen': ", ".join(nombres_ejercicios[:3]) + ("..." if len(nombres_ejercicios) > 3 else ""),
        })

    # =====================================================================
    # 6. CURVA DE PROGRESIÓN DE CARGAS POR EJERCICIO (CHART.JS)
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
        pesos_maximos = []
        volumen_lista = []

        for reg in registros:
            max_peso = reg.series_detalle.aggregate(Max('peso_kg'))['peso_kg__max']
            vol_dia = reg.series_detalle.filter(
                repeticiones__isnull=False,
                peso_kg__isnull=False
            ).aggregate(v=Sum(volumen_expr))['v'] or 0

            if max_peso is not None:
                fechas_lista.append(reg.fecha.strftime('%d/%m/%Y'))
                pesos_maximos.append(float(max_peso))
                volumen_lista.append(float(vol_dia))

        if fechas_lista:
            datos_progresion[str(ej.id)] = {
                'nombre': ej.nombre,
                'modalidad': ej.modalidad,
                'fechas': fechas_lista,
                'pesos_max': pesos_maximos,
                'volumen': volumen_lista,
            }

    # =====================================================================
    # 7. DISTRIBUCIÓN POR GRUPO MUSCULAR
    # =====================================================================
    distribucion_raw = RegistroEjercicio.objects.filter(
        usuario=usuario
    ).values('ejercicio__grupo_muscular').annotate(total=Count('id')).order_by('-total')

    nombres_grupos = dict(Ejercicio.GRUPO_MUSCULAR_CHOICES)
    distribucion_json = [
        {
            'grupo': nombres_grupos.get(item['ejercicio__grupo_muscular'], item['ejercicio__grupo_muscular']),
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

        # KPIs y Tendencias
        'dias_entrenados_mes': dias_entrenados_mes,
        'volumen_total': round(volumen_total, 1),
        'vol_sem_actual': round(vol_sem_actual, 1),
        'vol_cambio_pct': vol_cambio_pct,
        'total_series': total_series,
        'series_sem_actual': series_sem_actual,
        'series_cambio_pct': series_cambio_pct,
        'total_rutinas': total_rutinas,

        # Récords y Rendimiento
        'records_personales': records_personales,

        # Historial y Gráficos
        'sesiones_recientes': sesiones_recientes,
        'ejercicios_con_datos': ejercicios_con_datos,
        'datos_progresion_json': json.dumps(datos_progresion),
        'distribucion_json': json.dumps(distribucion_json),
    }
    return render(request, 'dashboard/dashboard.html', context)