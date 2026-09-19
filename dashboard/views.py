import json
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
    KPIs mensuales, volumen acumulado, progresión por ejercicio y sesiones recientes.
    """
    usuario = request.user
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)

    # 1. Métricas Clave (KPIs)
    dias_entrenados_mes = RegistroEjercicio.objects.filter(
        usuario=usuario,
        fecha__gte=inicio_mes
    ).values('fecha').distinct().count()

    total_series = Serie.objects.filter(registro__usuario=usuario).count()

    # Cálculo del volumen acumulado (reps * peso_kg)
    volumen_expr = ExpressionWrapper(F('repeticiones') * F('peso_kg'), output_field=DecimalField())
    volumen_total = Serie.objects.filter(
        registro__usuario=usuario,
        repeticiones__isnull=False,
        peso_kg__isnull=False
    ).aggregate(total=Sum(volumen_expr))['total'] or 0

    total_rutinas = Rutina.objects.filter(usuario=usuario).count()

    # 2. Historial de Sesiones Recientes
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

    # 3. Curva de Progresión de Cargas por Ejercicio (para Chart.js)
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

    # 4. Distribución por Grupo Muscular
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
        'dias_entrenados_mes': dias_entrenados_mes,
        'volumen_total': round(volumen_total, 1),
        'total_series': total_series,
        'total_rutinas': total_rutinas,
        'sesiones_recientes': sesiones_recientes,
        'ejercicios_con_datos': ejercicios_con_datos,
        'datos_progresion_json': json.dumps(datos_progresion),
        'distribucion_json': json.dumps(distribucion_json),
    }
    return render(request, 'dashboard/dashboard.html', context)