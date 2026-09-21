"""
Motor de Recomendación Inteligente de Rutinas Deportivas para OPTIFIT (FitApp).
Genera planes de entrenamiento científicamente estructurados a partir del perfil del deportista:
- Edad (considerando impacto articular y capacidad de recuperación)
- Género / Sexo (proporción tren inferior / glúteos / tren superior)
- Nivel de experiencia (Principiante, Intermedio, Avanzado)
- Objetivo deportivo (Hipertrofia, Pérdida de Grasa, Fuerza, Salud general, Resistencia)
- Meta por semana (2, 3, 4, 5, 6 días asignados)
- Preferencias de equipamiento y tiempo disponible
"""

from typing import Dict, Any, List, Optional
from datetime import date
from django.utils import timezone
from django.contrib.auth.models import User

from ejercicios.models import Ejercicio


# =============================================================================
# MAPEOS DE CONFIGURACIÓN CIENTÍFICA SEGÚN OBJETIVO Y NIVEL
# =============================================================================

CONFIG_OBJETIVOS = {
    'HIP': {
        'nombre': 'Hipertrofia y Desarrollo Muscular',
        'reps_compuesto': 8,
        'reps_aislamiento': 10,
        'reps_general': 10,
        'series_base': 4,
        'descanso_seg': 75,
        'rpe': '8 - 9',
        'tempo': '2-0-2 (Control en fase excéntrica)',
        'justificacion': 'Rango de 8 a 12 repeticiones optimizado para maximizar el estrés metabólico y la tensión mecánica, estimulando la hipertrofia miofibrilar y sarcoplasmática.'
    },
    'DEF': {
        'nombre': 'Definición y Pérdida de Grasa',
        'reps_compuesto': 12,
        'reps_aislamiento': 15,
        'reps_general': 12,
        'series_base': 3,
        'descanso_seg': 50,
        'rpe': '8',
        'tempo': '2-0-1 (Cadencia dinámica)',
        'justificacion': 'Mayor densidad de entrenamiento con descansos reducidos (45-60s) para elevar la tasa metabólica y el gasto calórico preservando la masa muscular magra.'
    },
    'FUE': {
        'nombre': 'Fuerza Máxima y Rendimiento',
        'reps_compuesto': 5,
        'reps_aislamiento': 8,
        'reps_general': 6,
        'series_base': 4,
        'descanso_seg': 150,
        'rpe': '8.5 - 9.5',
        'tempo': 'Explosivo concéntrico, controlado excéntrico',
        'justificacion': 'Cargas elevadas con bajas repeticiones (4-6 reps) y descansos prolongados (2-3 min) para maximizar el reclutamiento de unidades motoras y adaptaciones neurales.'
    },
    'SAL': {
        'nombre': 'Salud, Movilidad y Condición Física',
        'reps_compuesto': 10,
        'reps_aislamiento': 12,
        'reps_general': 10,
        'series_base': 3,
        'descanso_seg': 75,
        'rpe': '7',
        'tempo': 'Controlado y fluido',
        'justificacion': 'Trabajo biomecánicamente seguro con ejercicios multiarticulares y accesorios de movilidad para reforzar la postura, estabilidad del core y longevidad articular.'
    },
    'RES': {
        'nombre': 'Resistencia Muscular y Cardiovascular',
        'reps_compuesto': 15,
        'reps_aislamiento': 20,
        'reps_general': 15,
        'series_base': 3,
        'descanso_seg': 45,
        'rpe': '7 - 8',
        'tempo': 'Ritmo continuo',
        'justificacion': 'Series prolongadas de 15 a 20 repeticiones combinadas con trabajo cardiovascular para elevar la capacidad oxidativa y la tolerancia al lactato.'
    },
}

CONFIG_NIVELES = {
    'PR': {
        'nombre': 'Principiante',
        'delta_series': -1,  # Reducir volumen
        'max_ejercicios': 5,
        'preferir_maquinas': True,
        'rpe_max': '7 - 8',
        'consejo': 'Prioriza la técnica y la ejecución limpia antes de añadir carga. Las máquinas guiadas ofrecen una base segura y estable.'
    },
    'IN': {
        'nombre': 'Intermedio',
        'delta_series': 0,
        'max_ejercicios': 6,
        'preferir_maquinas': False,
        'rpe_max': '8 - 9',
        'consejo': 'Aplica sobrecarga progresiva sistemática en los ejercicios básicos (anotando repeticiones y peso en cada sesión).'
    },
    'AV': {
        'nombre': 'Avanzado',
        'delta_series': 1,  # Aumentar volumen
        'max_ejercicios': 7,
        'preferir_maquinas': False,
        'rpe_max': '8.5 - 9.5',
        'consejo': 'Mayor intensidad y volumen de trabajo. Presta especial atención a la recuperación entre sesiones y a la periodización.'
    },
}


# =============================================================================
# ESTRUCTURAS SEMANALES DE RUTINAS (SPLITS) SEGÚN DÍAS
# =============================================================================

def _obtener_esquema_dias(dias_semana: int) -> List[Dict[str, Any]]:
    """
    Determina la distribución de rutinas y los días de la semana recomendados.
    0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo.
    """
    if dias_semana <= 2:
        return [
            {
                'nombre': 'Full Body A — Empuje & Cuádriceps',
                'enfoque': 'Cuerpo completo con énfasis en empuje horizontal/vertical y cadena anterior',
                'dias_numeros': [0], # Lunes
                'dias_str': '0',
                'roles': ['PIE_QUAD', 'PEC_BASE', 'ESP_JALON', 'HOM_PRESS', 'COR_PLANK']
            },
            {
                'nombre': 'Full Body B — Tracción & Cadena Posterior',
                'enfoque': 'Cuerpo completo con énfasis en tracción dorsal, isquiotibiales y glúteos',
                'dias_numeros': [3], # Jueves
                'dias_str': '3',
                'roles': ['PIE_POST', 'ESP_REMO', 'PEC_ACC', 'BRA_BICEPS', 'BRA_TRICEPS', 'COR_CRUNCH']
            },
        ]
    elif dias_semana == 3:
        return [
            {
                'nombre': 'Empuje (Push) — Pectoral, Hombro & Tríceps',
                'enfoque': 'Músculos extensores y de empuje del tren superior',
                'dias_numeros': [0], # Lunes
                'dias_str': '0',
                'roles': ['PEC_BASE', 'PEC_INC', 'HOM_PRESS', 'HOM_LAT', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Tirón (Pull) — Espalda, Bíceps & Core',
                'enfoque': 'Músculos flexores y de tracción dorsal y braquial',
                'dias_numeros': [2], # Miércoles
                'dias_str': '2',
                'roles': ['ESP_JALON', 'ESP_REMO', 'ESP_ACC', 'BRA_BICEPS', 'COR_PLANK']
            },
            {
                'nombre': 'Piernas & Glúteos (Legs) — Tren Inferior',
                'enfoque': 'Desarrollo integral de cuádriceps, glúteos, isquiotibiales y pantorrillas',
                'dias_numeros': [4], # Viernes
                'dias_str': '4',
                'roles': ['PIE_QUAD_BASE', 'PIE_POST', 'PIE_ISO', 'GLU_BASE', 'PIE_CALF']
            },
        ]
    elif dias_semana == 4:
        return [
            {
                'nombre': 'Torso A — Fuerza Pecho & Espalda',
                'enfoque': 'Tren superior con énfasis en compuestos horizontales de empuje y tracción',
                'dias_numeros': [0], # Lunes
                'dias_str': '0',
                'roles': ['PEC_BASE', 'ESP_REMO', 'PEC_INC', 'ESP_JALON', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Pierna A — Cuádriceps & Gemelos',
                'enfoque': 'Tren inferior con énfasis en rodilla-dominante y cuádriceps',
                'dias_numeros': [1], # Martes
                'dias_str': '1',
                'roles': ['PIE_QUAD_BASE', 'PIE_EXT', 'PIE_POST', 'PIE_CALF', 'COR_PLANK']
            },
            {
                'nombre': 'Torso B — Hombros, Espalda & Brazos',
                'enfoque': 'Tren superior con énfasis en empuje vertical, deltoides y brazos',
                'dias_numeros': [3], # Jueves
                'dias_str': '3',
                'roles': ['HOM_PRESS', 'ESP_JALON', 'HOM_LAT', 'BRA_BICEPS', 'BRA_TRICEPS', 'PEC_ACC']
            },
            {
                'nombre': 'Pierna B — Isquiotibiales, Glúteos & Core',
                'enfoque': 'Tren inferior con énfasis en cadera-dominante y estabilidad',
                'dias_numeros': [4], # Viernes
                'dias_str': '4',
                'roles': ['PIE_POST', 'GLU_BASE', 'PIE_QUAD_ACC', 'GLU_ABD', 'COR_CRUNCH']
            },
        ]
    elif dias_semana == 5:
        return [
            {
                'nombre': 'Push — Pectoral & Tríceps',
                'enfoque': 'Empuje horizontal e inclinado enfocado en pecho y tríceps',
                'dias_numeros': [0], # Lunes
                'dias_str': '0',
                'roles': ['PEC_BASE', 'PEC_INC', 'PEC_ACC', 'BRA_TRICEPS', 'BRA_TRICEPS_ACC']
            },
            {
                'nombre': 'Pull — Espalda & Bíceps',
                'enfoque': 'Tracción vertical y horizontal con desarrollo de espalda alta y brazos',
                'dias_numeros': [1], # Martes
                'dias_str': '1',
                'roles': ['ESP_JALON', 'ESP_REMO', 'ESP_ACC', 'BRA_BICEPS', 'BRA_BICEPS_ACC']
            },
            {
                'nombre': 'Legs — Cuádriceps & Gemelos',
                'enfoque': 'Tren inferior completo con énfasis en cuádriceps',
                'dias_numeros': [2], # Miércoles
                'dias_str': '2',
                'roles': ['PIE_QUAD_BASE', 'PIE_EXT', 'PIE_POST', 'PIE_CALF', 'COR_PLANK']
            },
            {
                'nombre': 'Hombros & Core — Deltoides 3D',
                'enfoque': 'Desarrollo de las 3 cabezas del hombro y zona media',
                'dias_numeros': [3], # Jueves
                'dias_str': '3',
                'roles': ['HOM_PRESS', 'HOM_LAT', 'HOM_ACC', 'COR_CRUNCH', 'COR_PLANK']
            },
            {
                'nombre': 'Glúteos & Isquios / Acondicionamiento',
                'enfoque': 'Cadena posterior y equilibrio muscular',
                'dias_numeros': [4], # Viernes
                'dias_str': '4',
                'roles': ['GLU_BASE', 'PIE_POST', 'GLU_ABD', 'PIE_LUNGE', 'CAR_CARDIO']
            },
        ]
    else: # 6 días (Push Pull Legs x2)
        return [
            {
                'nombre': 'Push 1 — Pecho & Hombros (Pesado)',
                'enfoque': 'Empuje con intensidades más altas en básicos',
                'dias_numeros': [0], # Lunes
                'dias_str': '0',
                'roles': ['PEC_BASE', 'HOM_PRESS', 'PEC_INC', 'HOM_LAT', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Pull 1 — Espalda & Bíceps (Pesado)',
                'enfoque': 'Tracción con foco en amplitud y densidad dorsal',
                'dias_numeros': [1], # Martes
                'dias_str': '1',
                'roles': ['ESP_JALON', 'ESP_REMO', 'ESP_ACC', 'BRA_BICEPS', 'COR_PLANK']
            },
            {
                'nombre': 'Legs 1 — Enfoque Cuádriceps',
                'enfoque': 'Tren inferior con énfasis en rodilla dominante',
                'dias_numeros': [2], # Miércoles
                'dias_str': '2',
                'roles': ['PIE_QUAD_BASE', 'PIE_EXT', 'PIE_POST', 'GLU_BASE', 'PIE_CALF']
            },
            {
                'nombre': 'Push 2 — Hipertrofia & Bombeo',
                'enfoque': 'Empuje con mayor volumen y aislamiento muscular',
                'dias_numeros': [3], # Jueves
                'dias_str': '3',
                'roles': ['PEC_INC', 'PEC_ACC', 'HOM_LAT', 'BRA_TRICEPS', 'BRA_TRICEPS_ACC']
            },
            {
                'nombre': 'Pull 2 — Hipertrofia & Detalles',
                'enfoque': 'Tracción con poleas y mancuernas para aislamiento dorsal',
                'dias_numeros': [4], # Viernes
                'dias_str': '4',
                'roles': ['ESP_REMO', 'ESP_JALON', 'BRA_BICEPS', 'COR_CRUNCH', 'COR_PLANK']
            },
            {
                'nombre': 'Legs 2 — Isquios & Glúteos',
                'enfoque': 'Cadena posterior, cadera dominante y glúteos',
                'dias_numeros': [5], # Sábado
                'dias_str': '5',
                'roles': ['PIE_POST', 'GLU_BASE', 'PIE_LUNGE', 'GLU_ABD', 'PIE_CALF']
            },
        ]


# =============================================================================
# MAPEO INTELIGENTE DE ROLES A CONSULTAS EN EL CATÁLOGO OFICIAL
# =============================================================================

ROLE_QUERIES = {
    'PEC_BASE': [
        {'nombre__icontains': 'Press de Pecho en Máquina', 'tipo': 'MAQ'},
        {'nombre__icontains': 'Press de Banca Plano', 'tipo': 'LIB'},
        {'grupo_muscular': 'PEC', 'tipo': 'MAQ'},
        {'grupo_muscular': 'PEC'},
    ],
    'PEC_INC': [
        {'nombre__icontains': 'Press Inclinado con Mancuernas'},
        {'nombre__icontains': 'Contractora de Pecho'},
        {'grupo_muscular': 'PEC'},
    ],
    'PEC_ACC': [
        {'nombre__icontains': 'Cruces de Poleas'},
        {'nombre__icontains': 'Contractora de Pecho'},
        {'nombre__icontains': 'Flexiones de Pecho'},
        {'grupo_muscular': 'PEC'},
    ],
    'ESP_JALON': [
        {'nombre__icontains': 'Jalón al Pecho en Polea'},
        {'nombre__icontains': 'Dominadas'},
        {'grupo_muscular': 'ESP'},
    ],
    'ESP_REMO': [
        {'nombre__icontains': 'Remo en Polea Baja'},
        {'nombre__icontains': 'Remo con Mancuerna'},
        {'grupo_muscular': 'ESP'},
    ],
    'ESP_ACC': [
        {'nombre__icontains': 'Remo con Mancuerna'},
        {'nombre__icontains': 'Peso Muerto Convencional'},
        {'nombre__icontains': 'Remo en Polea'},
        {'grupo_muscular': 'ESP'},
    ],
    'PIE_QUAD': [
        {'nombre__icontains': 'Prensa de Piernas'},
        {'nombre__icontains': 'Sentadilla Trasera'},
        {'grupo_muscular': 'PIE'},
    ],
    'PIE_QUAD_BASE': [
        {'nombre__icontains': 'Prensa de Piernas'},
        {'nombre__icontains': 'Sentadilla Trasera'},
        {'nombre__icontains': 'Sentadillas Aéreas'},
        {'grupo_muscular': 'PIE'},
    ],
    'PIE_QUAD_ACC': [
        {'nombre__icontains': 'Extensión de Cuádriceps'},
        {'nombre__icontains': 'Zancadas con Mancuernas'},
        {'grupo_muscular': 'PIE'},
    ],
    'PIE_POST': [
        {'nombre__icontains': 'Curl Femoral'},
        {'nombre__icontains': 'Peso Muerto Rumano'},
        {'grupo_muscular': 'PIE'},
    ],
    'PIE_EXT': [
        {'nombre__icontains': 'Extensión de Cuádriceps'},
        {'nombre__icontains': 'Prensa de Piernas'},
        {'grupo_muscular': 'PIE'},
    ],
    'PIE_ISO': [
        {'nombre__icontains': 'Curl Femoral'},
        {'nombre__icontains': 'Extensión de Cuádriceps'},
        {'grupo_muscular': 'PIE'},
    ],
    'PIE_LUNGE': [
        {'nombre__icontains': 'Zancadas con Mancuernas'},
        {'nombre__icontains': 'Máquina de Aductores'},
        {'grupo_muscular': 'PIE'},
    ],
    'PIE_CALF': [
        {'nombre__icontains': 'Elevación de Gemelos'},
        {'grupo_muscular': 'PIE'},
    ],
    'HOM_PRESS': [
        {'nombre__icontains': 'Press de Hombros en Máquina'},
        {'nombre__icontains': 'Press Militar'},
        {'grupo_muscular': 'HOM'},
    ],
    'HOM_LAT': [
        {'nombre__icontains': 'Elevaciones Laterales en Máquina'},
        {'nombre__icontains': 'Elevaciones Laterales con Mancuernas'},
        {'grupo_muscular': 'HOM'},
    ],
    'HOM_ACC': [
        {'nombre__icontains': 'Elevaciones Laterales'},
        {'nombre__icontains': 'Press Militar'},
        {'grupo_muscular': 'HOM'},
    ],
    'BRA_TRICEPS': [
        {'nombre__icontains': 'Extensión de Tríceps en Polea'},
        {'nombre__icontains': 'Fondos de Tríceps'},
        {'nombre__icontains': 'Press Francés'},
        {'grupo_muscular': 'BRA'},
    ],
    'BRA_TRICEPS_ACC': [
        {'nombre__icontains': 'Press Francés'},
        {'nombre__icontains': 'Fondos de Tríceps'},
        {'grupo_muscular': 'BRA'},
    ],
    'BRA_BICEPS': [
        {'nombre__icontains': 'Curl de Bíceps en Polea'},
        {'nombre__icontains': 'Curl de Bíceps con Mancuernas'},
        {'grupo_muscular': 'BRA'},
    ],
    'BRA_BICEPS_ACC': [
        {'nombre__icontains': 'Curl de Bíceps con Mancuernas'},
        {'nombre__icontains': 'Curl de Bíceps en Polea'},
        {'grupo_muscular': 'BRA'},
    ],
    'GLU_BASE': [
        {'nombre__icontains': 'Hip Thrust'},
        {'nombre__icontains': 'Máquina de Abductores'},
        {'nombre__icontains': 'Zancadas con Mancuernas'},
        {'grupo_muscular': 'GLU'},
    ],
    'GLU_ABD': [
        {'nombre__icontains': 'Máquina de Abductores'},
        {'nombre__icontains': 'Hip Thrust'},
        {'grupo_muscular': 'GLU'},
    ],
    'COR_PLANK': [
        {'nombre__icontains': 'Plancha Abdominal Isométrica'},
        {'nombre__icontains': 'Plancha Lateral'},
        {'grupo_muscular': 'COR'},
    ],
    'COR_CRUNCH': [
        {'nombre__icontains': 'Abdominales Crunch'},
        {'nombre__icontains': 'Elevaciones de Piernas Colgado'},
        {'grupo_muscular': 'COR'},
    ],
    'CAR_CARDIO': [
        {'nombre__icontains': 'Remo Ergómetro'},
        {'nombre__icontains': 'Bicicleta Estática'},
        {'nombre__icontains': 'Elíptica'},
        {'grupo_muscular': 'CAR'},
    ],
}


def _buscar_ejercicio_por_rol(rol: str, ya_usados_ids: set, preferir_maquinas: bool = False) -> Optional[Ejercicio]:
    """
    Localiza en el catálogo de Ejercicio el ejercicio más idóneo para un rol dado,
    evitando duplicarlo en la misma sesión y respetando preferencias de seguridad articular.
    """
    consultas = ROLE_QUERIES.get(rol, [{'nombre__icontains': rol}])
    
    # 1. Si se prefieren máquinas (principiante o edad avanzada), intentar primero filtros con tipo MAQ
    if preferir_maquinas:
        for q in consultas:
            q_maq = {**q, 'tipo': 'MAQ'}
            ej = Ejercicio.objects.filter(**q_maq).exclude(id__in=ya_usados_ids).first()
            if ej:
                return ej

    # 2. Búsqueda normal según la lista de prioridades de cada rol
    for q in consultas:
        ej = Ejercicio.objects.filter(**q).exclude(id__in=ya_usados_ids).first()
        if ej:
            return ej

    # 3. Fallback: cualquier ejercicio del grupo muscular principal del rol que no esté ya usado
    grupo_prefijo = rol.split('_')[0]
    if grupo_prefijo in ['PEC', 'ESP', 'PIE', 'HOM', 'BRA', 'GLU', 'COR', 'CAR']:
        ej = Ejercicio.objects.filter(grupo_muscular=grupo_prefijo).exclude(id__in=ya_usados_ids).first()
        if ej:
            return ej

    # 4. Fallback final
    return Ejercicio.objects.exclude(id__in=ya_usados_ids).first()


# =============================================================================
# FUNCIÓN PRINCIPAL DEL MOTOR DE RECOMENDACIÓN
# =============================================================================

def generar_plan_recomendado(usuario: User, preferencias: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Genera un plan estructurado de rutinas recomendadas adaptado al perfil y preferencias.
    Devuelve un diccionario con metadatos del plan, justificación y listado de rutinas
    con sus ejercicios preparados para previsualizar o guardar.
    """
    preferencias = preferencias or {}
    perfil = getattr(usuario, 'profile', None)

    # 1. Extracción de Parámetros del Usuario
    genero = preferencias.get('genero') or (getattr(perfil, 'genero', 'H') or 'H')
    
    edad = None
    if preferencias.get('edad'):
        try:
            edad = int(preferencias.get('edad'))
        except (ValueError, TypeError):
            pass
    if edad is None and perfil and perfil.edad:
        edad = perfil.edad
    if edad is None:
        edad = 28  # Fallback estándar

    nivel = preferencias.get('nivel') or (getattr(perfil, 'nivel', 'PR') or 'PR')
    if nivel not in CONFIG_NIVELES:
        nivel = 'PR'

    objetivo = preferencias.get('objetivo') or (getattr(perfil, 'objetivo', 'HIP') or 'HIP')
    if objetivo not in CONFIG_OBJETIVOS:
        objetivo = 'HIP'

    dias_semana_raw = preferencias.get('dias_semana') or getattr(perfil, 'dias_objetivo_semana', 4)
    try:
        dias_semana = int(dias_semana_raw)
    except (ValueError, TypeError):
        dias_semana = 4
    dias_semana = max(2, min(dias_semana, 6))

    equipamiento = preferencias.get('equipamiento', 'TODO')
    duracion = preferencias.get('duracion', 'ESTANDAR')

    # 2. Configuraciones Base
    cfg_obj = CONFIG_OBJETIVOS[objetivo]
    cfg_niv = CONFIG_NIVELES[nivel]

    # Ajuste por edad: Si edad >= 50, favorecer máquinas/poleas con apoyo lumbar y más descanso
    edad_avanzada = edad >= 50
    preferir_maquinas = cfg_niv['preferir_maquinas'] or edad_avanzada
    
    descanso_final = cfg_obj['descanso_seg']
    if edad_avanzada:
        descanso_final += 15

    # 3. Justificación y Notas Científicas Personalizadas
    notas_adaptacion = []
    
    # Nota de edad
    if edad < 25:
        notas_adaptacion.append("🚀 Tu juventud te confiere alta capacidad de síntesis proteica y recuperación rápida.")
    elif edad >= 50:
        notas_adaptacion.append("🛡️ Priorizamos estabilidad articular, descansos ampliados (+15s) y soporte lumbar para máxima longevidad.")
    else:
        notas_adaptacion.append("⚖️ Periodización equilibrada para consolidar fuerza, tono muscular y prevención de sobrecargas.")

    # Nota de género
    if genero == 'M':
        notas_adaptacion.append("✨ Enfoque armónico con volumen estratégico en tren inferior, glúteos y cadena posterior.")
    else:
        notas_adaptacion.append("💪 Proporción atlética simétrica en torso, deltoides y piernas.")

    # Nota de objetivo y nivel
    notas_adaptacion.append(f"🎯 {cfg_obj['justificacion']}")
    notas_adaptacion.append(f"📈 Nivel {cfg_niv['nombre']}: {cfg_niv['consejo']}")

    # 4. Obtención del Esquema de División (Split)
    esquema = _obtener_esquema_dias(dias_semana)
    rutinas_generadas = []

    # Mapa de nombres de días de la semana para badges
    dias_nombres_map = {
        0: ('Lun', 'Lunes'),
        1: ('Mar', 'Martes'),
        2: ('Mié', 'Miércoles'),
        3: ('Jue', 'Jueves'),
        4: ('Vie', 'Viernes'),
        5: ('Sáb', 'Sábado'),
        6: ('Dom', 'Domingo'),
    }

    # 5. Generación de cada Rutina con sus Ejercicios
    for rut_data in esquema:
        roles = rut_data['roles']
        
        # Ajuste de cantidad de ejercicios según nivel y duración
        max_ej = cfg_niv['max_ejercicios']
        if duracion == 'RAPIDO':
            max_ej = min(max_ej, 4)
        elif duracion == 'COMPLETO':
            max_ej = min(max_ej + 1, 7)
        roles = roles[:max_ej]

        # Ajuste de roles si el usuario es mujer (mayor presencia de glúteos/isquios si es día de pierna)
        if genero == 'M' and any('PIE' in r for r in roles):
            if 'GLU_BASE' not in roles and len(roles) >= 3:
                roles[-1] = 'GLU_BASE'

        ejercicios_rutina = []
        ya_usados = set()

        for orden, rol in enumerate(roles, start=1):
            ej = _buscar_ejercicio_por_rol(rol, ya_usados, preferir_maquinas=preferir_maquinas)
            if not ej:
                continue
            
            ya_usados.add(ej.id)

            # Cálculo de series y reps
            series = max(2, cfg_obj['series_base'] + cfg_niv['delta_series'])
            
            # Modalidad por tiempo vs reps
            if ej.modalidad == 'TIEMPO':
                reps = None
                tiempo_seg = 45 if nivel == 'PR' else (60 if nivel == 'IN' else 75)
            else:
                tiempo_seg = None
                # Ejercicios compuestos pesados vs aislamiento
                es_compuesto = (orden == 1) or any(k in ej.nombre.lower() for k in ['sentadilla', 'prensa', 'press', 'jalón', 'peso muerto', 'remo'])
                reps = cfg_obj['reps_compuesto'] if es_compuesto else cfg_obj['reps_aislamiento']

            ejercicios_rutina.append({
                'orden': orden,
                'ejercicio_id': ej.id,
                'nombre': ej.nombre,
                'grupo_muscular': ej.grupo_muscular,
                'grupo_muscular_display': ej.get_grupo_muscular_display(),
                'tipo': ej.tipo,
                'tipo_display': ej.get_tipo_display(),
                'modalidad': ej.modalidad,
                'icono': ej.icono,
                'series_objetivo': series,
                'repeticiones_objetivo': reps,
                'tiempo_objetivo_segundos': tiempo_seg,
                'peso_objetivo': None,
                'descanso_segundos': descanso_final,
                'rpe_sugerido': cfg_obj['rpe'],
            })

        # Badges estructurados para los días
        badges_dias = []
        for d in rut_data['dias_numeros']:
            if d in dias_nombres_map:
                badges_dias.append({
                    'num': d,
                    'corto': dias_nombres_map[d][0],
                    'completo': dias_nombres_map[d][1]
                })

        rutinas_generadas.append({
            'nombre': rut_data['nombre'],
            'descripcion': f"{rut_data['enfoque']}. Diseñada para {cfg_obj['nombre']} ({cfg_niv['nombre']}).",
            'dias_semana': rut_data['dias_str'],
            'dias_numeros': rut_data['dias_numeros'],
            'badges_dias': badges_dias,
            'enfoque': rut_data['enfoque'],
            'ejercicios': ejercicios_rutina,
            'total_ejercicios': len(ejercicios_rutina),
        })

    # 6. Empaquetado del Plan
    plan = {
        'titulo': f"Plan de Entrenamiento {cfg_obj['nombre']} ({dias_semana} días)",
        'objetivo_codigo': objetivo,
        'objetivo_nombre': cfg_obj['nombre'],
        'nivel_codigo': nivel,
        'nivel_nombre': cfg_niv['nombre'],
        'genero': genero,
        'edad': edad,
        'dias_semana': dias_semana,
        'equipamiento': equipamiento,
        'duracion': duracion,
        'descanso_promedio_seg': descanso_final,
        'rpe_promedio': cfg_obj['rpe'],
        'tempo_recomendado': cfg_obj['tempo'],
        'notas_adaptacion': notas_adaptacion,
        'rutinas': rutinas_generadas,
        'total_rutinas': len(rutinas_generadas),
    }

    return plan
