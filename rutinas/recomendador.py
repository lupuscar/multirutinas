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

from ejercicios.models import Ejercicio, Serie


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
        'justificacion': 'Mayor densidad de entrenamiento con descansos reducidos (45-50s) y remates cardiovasculares metabólicos para maximizar el gasto calórico preservando la masa muscular magra.'
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
        'justificacion': 'Cargas elevadas con bajas repeticiones (4-6 reps) en ejercicios multiarticulares primarios con peso libre y descansos prolongados (2-3 min) para maximizar adaptaciones neurales.'
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
        'justificacion': 'Trabajo biomecánicamente seguro con máquinas guiadas, ejercicios de movilidad/yoga, faja lumbo-abdominal y cardio suave para reforzar la postura y longevidad articular.'
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
        'justificacion': 'Entrenamiento combinado de capacidad cardiovascular de fondo e intervalos con calistenia y circuitos de alta repetición para elevar el umbral anaeróbico y la eficiencia oxidativa.'
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
# ESTRUCTURAS SEMANALES DE RUTINAS (SPLITS) SEGÚN OBJETIVO Y DÍAS
# =============================================================================

def _esquema_hipertrofia(dias_semana: int) -> List[Dict[str, Any]]:
    """Distribuciones optimizadas para volumen y crecimiento muscular (HIP)"""
    if dias_semana <= 2:
        return [
            {
                'nombre': 'Full Body A — Empuje & Cuádriceps',
                'enfoque': 'Cuerpo completo con énfasis en empuje horizontal/vertical y cadena anterior',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PIE_QUAD', 'PEC_BASE', 'ESP_JALON', 'HOM_PRESS', 'COR_PLANK']
            },
            {
                'nombre': 'Full Body B — Tracción & Cadena Posterior',
                'enfoque': 'Cuerpo completo con énfasis en tracción dorsal, isquiotibiales y glúteos',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['PIE_POST', 'ESP_REMO', 'PEC_INC', 'BRA_BICEPS', 'BRA_TRICEPS', 'COR_CRUNCH']
            },
        ]
    elif dias_semana == 3:
        return [
            {
                'nombre': 'Empuje (Push) — Pectoral, Hombro & Tríceps',
                'enfoque': 'Músculos extensores y de empuje del tren superior para hipertrofia',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BASE', 'PEC_INC', 'HOM_PRESS', 'HOM_LAT', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Tirón (Pull) — Espalda, Bíceps & Core',
                'enfoque': 'Músculos flexores y de tracción dorsal y braquial para amplitud y densidad',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['ESP_JALON', 'ESP_REMO', 'ESP_ACC', 'BRA_BICEPS', 'COR_PLANK']
            },
            {
                'nombre': 'Piernas & Glúteos (Legs) — Tren Inferior',
                'enfoque': 'Desarrollo integral de cuádriceps, glúteos, isquiotibiales y pantorrillas',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['PIE_QUAD_BASE', 'PIE_POST', 'PIE_ISO', 'GLU_BASE', 'PIE_CALF']
            },
        ]
    elif dias_semana == 4:
        return [
            {
                'nombre': 'Torso A — Hipertrofia Pecho & Espalda',
                'enfoque': 'Tren superior con énfasis en compuestos horizontales de empuje y tracción',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BASE', 'ESP_REMO', 'PEC_INC', 'ESP_JALON', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Pierna A — Cuádriceps & Gemelos',
                'enfoque': 'Tren inferior con énfasis en rodilla-dominante y cuádriceps',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['PIE_QUAD_BASE', 'PIE_EXT', 'PIE_POST', 'PIE_CALF', 'COR_PLANK']
            },
            {
                'nombre': 'Torso B — Hombros, Espalda & Brazos',
                'enfoque': 'Tren superior con énfasis en empuje vertical, deltoides y brazos',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['HOM_PRESS', 'ESP_JALON', 'HOM_LAT', 'BRA_BICEPS', 'BRA_TRICEPS', 'PEC_ACC']
            },
            {
                'nombre': 'Pierna B — Isquiotibiales, Glúteos & Core',
                'enfoque': 'Tren inferior con énfasis en cadera-dominante y estabilidad',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['PIE_POST', 'GLU_BASE', 'PIE_QUAD_ACC', 'GLU_ABD', 'COR_CRUNCH']
            },
        ]
    elif dias_semana == 5:
        return [
            {
                'nombre': 'Push — Pectoral & Tríceps',
                'enfoque': 'Empuje horizontal e inclinado enfocado en pecho y tríceps',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BASE', 'PEC_INC', 'PEC_ACC', 'BRA_TRICEPS', 'BRA_TRICEPS_ACC']
            },
            {
                'nombre': 'Pull — Espalda & Bíceps',
                'enfoque': 'Tracción vertical y horizontal con desarrollo de espalda alta y brazos',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['ESP_JALON', 'ESP_REMO', 'ESP_ACC', 'BRA_BICEPS', 'BRA_BICEPS_ACC']
            },
            {
                'nombre': 'Legs — Cuádriceps & Gemelos',
                'enfoque': 'Tren inferior completo con énfasis en cuádriceps',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['PIE_QUAD_BASE', 'PIE_EXT', 'PIE_POST', 'PIE_CALF', 'COR_PLANK']
            },
            {
                'nombre': 'Hombros & Brazos — Deltoides 3D',
                'enfoque': 'Desarrollo de las 3 cabezas del hombro y brazos completos',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['HOM_PRESS', 'HOM_LAT', 'HOM_ACC', 'BRA_BICEPS', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Glúteos & Isquios — Cadena Posterior',
                'enfoque': 'Cadena posterior y equilibrio muscular estético',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['GLU_BASE', 'PIE_POST', 'GLU_ABD', 'PIE_LUNGE', 'COR_CRUNCH']
            },
        ]
    else:  # 6 días
        return [
            {
                'nombre': 'Push 1 — Pecho & Hombros (Pesado)',
                'enfoque': 'Empuje con intensidades más altas en básicos',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BASE', 'HOM_PRESS', 'PEC_INC', 'HOM_LAT', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Pull 1 — Espalda & Bíceps (Pesado)',
                'enfoque': 'Tracción con foco en amplitud y densidad dorsal',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['ESP_JALON', 'ESP_REMO', 'ESP_ACC', 'BRA_BICEPS', 'COR_PLANK']
            },
            {
                'nombre': 'Legs 1 — Enfoque Cuádriceps',
                'enfoque': 'Tren inferior con énfasis en rodilla dominante',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['PIE_QUAD_BASE', 'PIE_EXT', 'PIE_POST', 'GLU_BASE', 'PIE_CALF']
            },
            {
                'nombre': 'Push 2 — Hipertrofia & Bombeo',
                'enfoque': 'Empuje con mayor volumen y aislamiento muscular',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['PEC_INC', 'PEC_ACC', 'HOM_LAT', 'BRA_TRICEPS', 'BRA_TRICEPS_ACC']
            },
            {
                'nombre': 'Pull 2 — Hipertrofia & Detalles',
                'enfoque': 'Tracción con poleas y mancuernas para aislamiento dorsal',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['ESP_REMO', 'ESP_JALON', 'BRA_BICEPS', 'COR_CRUNCH', 'COR_PLANK']
            },
            {
                'nombre': 'Legs 2 — Isquios & Glúteos',
                'enfoque': 'Cadena posterior, cadera dominante y glúteos',
                'dias_numeros': [5],
                'dias_str': '5',
                'roles': ['PIE_POST', 'GLU_BASE', 'PIE_LUNGE', 'GLU_ABD', 'PIE_CALF']
            },
        ]


def _esquema_fuerza(dias_semana: int) -> List[Dict[str, Any]]:
    """Distribuciones estructuradas en torno a los básicos pesados de fuerza (FUE)"""
    if dias_semana <= 2:
        return [
            {
                'nombre': 'Fuerza A — Sentadilla & Empuje Pesado',
                'enfoque': 'Patrones primarios de sentadilla con barra, press de banca plano y tracción pesada',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PIE_SQUAT_BAR', 'PEC_BENCH_BAR', 'ESP_ROW_HEAVY', 'COR_PLANK']
            },
            {
                'nombre': 'Fuerza B — Peso Muerto & Press Militar',
                'enfoque': 'Bisagra de cadera máxima con peso muerto convencional, press militar vertical y dominadas',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['ESP_DEADLIFT_BAR', 'HOM_PRESS_BAR', 'ESP_PULLUP', 'PIE_QUAD_BASE']
            },
        ]
    elif dias_semana == 3:
        return [
            {
                'nombre': 'Fuerza 1 — Sentadilla & Empuje',
                'enfoque': 'Sentadilla trasera con barra, press de banca plano y asistencia de empuje',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PIE_SQUAT_BAR', 'PEC_BENCH_BAR', 'PEC_INC', 'COR_PLANK']
            },
            {
                'nombre': 'Fuerza 2 — Peso Muerto & Tracción',
                'enfoque': 'Peso muerto convencional con barra, dominadas pronadas y remo pesado',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['ESP_DEADLIFT_BAR', 'ESP_PULLUP', 'ESP_REMO', 'COR_HANGING']
            },
            {
                'nombre': 'Fuerza 3 — Press Militar & Potencia Tren Inferior',
                'enfoque': 'Empuje vertical por encima de la cabeza, prensa pesada y peso muerto rumano',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['HOM_PRESS_BAR', 'PIE_QUAD_BASE', 'PIE_POST', 'ESP_REMO']
            },
        ]
    elif dias_semana == 4:
        return [
            {
                'nombre': 'Torso Fuerza A — Banca Pesada & Remo',
                'enfoque': 'Press de banca plano con barra como núcleo, combinado con remo unilateral pesado',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BENCH_BAR', 'ESP_REMO', 'HOM_PRESS_BAR', 'ESP_PULLUP']
            },
            {
                'nombre': 'Pierna Fuerza A — Sentadilla con Barra',
                'enfoque': 'Sentadilla trasera pesada, prensa complementaria y cadena posterior',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['PIE_SQUAT_BAR', 'PIE_QUAD_BASE', 'PIE_POST', 'PIE_CALF', 'COR_PLANK']
            },
            {
                'nombre': 'Torso Fuerza B — Press Militar & Dominadas',
                'enfoque': 'Press militar con barra y dominadas pronadas con sobrecarga',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['HOM_PRESS_BAR', 'ESP_PULLUP', 'PEC_INC', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Pierna Fuerza B — Peso Muerto Convencional',
                'enfoque': 'Peso muerto convencional con barra, prensa pesada e hip thrust de potencia',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['ESP_DEADLIFT_BAR', 'PIE_QUAD_BASE', 'GLU_BASE', 'COR_SIDE_PLANK']
            },
        ]
    elif dias_semana == 5:
        return [
            {
                'nombre': 'Fuerza Día 1 — Sentadilla & Cuádriceps',
                'enfoque': 'Sentadilla trasera con barra pesada y accesorios de extensión',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PIE_SQUAT_BAR', 'PIE_QUAD_BASE', 'PIE_LUNGE', 'PIE_CALF', 'COR_PLANK']
            },
            {
                'nombre': 'Fuerza Día 2 — Press de Banca & Pecho',
                'enfoque': 'Press de banca plano con barra pesada y accesorios de empuje',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['PEC_BENCH_BAR', 'PEC_INC', 'BRA_TRICEPS', 'COR_CRUNCH']
            },
            {
                'nombre': 'Fuerza Día 3 — Peso Muerto & Tracción',
                'enfoque': 'Peso muerto convencional con barra y dominadas estrictas',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['ESP_DEADLIFT_BAR', 'ESP_PULLUP', 'ESP_REMO', 'BRA_BICEPS']
            },
            {
                'nombre': 'Fuerza Día 4 — Press Militar & Deltoides',
                'enfoque': 'Press militar con barra vertical y densidad de espalda alta',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['HOM_PRESS_BAR', 'ESP_JALON', 'HOM_LAT', 'COR_HANGING']
            },
            {
                'nombre': 'Fuerza Día 5 — Cadena Posterior & Glúteos',
                'enfoque': 'Peso muerto rumano pesado, hip thrust con barra y prensa de apoyo',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['PIE_POST', 'GLU_BASE', 'PIE_QUAD_BASE', 'COR_PLANK']
            },
        ]
    else:  # 6 días
        return [
            {
                'nombre': 'Push Fuerza (Pesado)',
                'enfoque': 'Press de banca plano y press militar pesado a bajas repeticiones',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BENCH_BAR', 'HOM_PRESS_BAR', 'PEC_INC', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Pull Fuerza (Pesado)',
                'enfoque': 'Peso muerto convencional con barra y dominadas estrictas',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['ESP_DEADLIFT_BAR', 'ESP_PULLUP', 'ESP_REMO', 'COR_PLANK']
            },
            {
                'nombre': 'Legs Fuerza (Pesado)',
                'enfoque': 'Sentadilla trasera con barra pesada y prensa guiada',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['PIE_SQUAT_BAR', 'PIE_QUAD_BASE', 'PIE_POST', 'PIE_CALF']
            },
            {
                'nombre': 'Push Potencia / Volumen',
                'enfoque': 'Empuje con mancuernas y fondos con cadencia controlada',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['PEC_INC', 'HOM_PRESS', 'HOM_LAT', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Pull Potencia / Volumen',
                'enfoque': 'Remos con mancuerna, jalones y trabajo de bíceps pesado',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['ESP_REMO', 'ESP_JALON', 'BRA_BICEPS', 'COR_HANGING']
            },
            {
                'nombre': 'Legs Potencia / Cadena Posterior',
                'enfoque': 'Peso muerto rumano, hip thrust pesado y zancadas',
                'dias_numeros': [5],
                'dias_str': '5',
                'roles': ['PIE_POST', 'GLU_BASE', 'PIE_LUNGE', 'PIE_CALF']
            },
        ]


def _esquema_definicion(dias_semana: int) -> List[Dict[str, Any]]:
    """Distribuciones de alta densidad metabólica con finishers cardiovasculares (DEF)"""
    if dias_semana <= 2:
        return [
            {
                'nombre': 'Full Body Metabólico A + Finisher Cinta',
                'enfoque': 'Fuerza multiarticular de alta densidad con remate cardiovascular en cinta',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PIE_QUAD_BASE', 'PEC_BASE', 'ESP_REMO', 'CAL_PUSH', 'CAR_RUN']
            },
            {
                'nombre': 'Full Body Metabólico B + Finisher Remo',
                'enfoque': 'Cadena posterior y core dinámico con remate en remo ergómetro',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['PIE_POST', 'ESP_JALON', 'PIE_LUNGE', 'COR_PLANK', 'CAR_ROW']
            },
        ]
    elif dias_semana == 3:
        return [
            {
                'nombre': 'Empuje Metabólico & Finisher Cinta HIIT',
                'enfoque': 'Empuje de torso y piernas con remate cardiovascular en cinta rodante',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BASE', 'CAL_PUSH', 'HOM_PRESS', 'PIE_LUNGE', 'CAR_RUN']
            },
            {
                'nombre': 'Tracción Metabólica & Finisher Remo Ergómetro',
                'enfoque': 'Tracción dorsal y cadena posterior con remate de potencia respiratoria en remo',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['ESP_JALON', 'ESP_REMO', 'PIE_POST', 'COR_PLANK', 'CAR_ROW']
            },
            {
                'nombre': 'Piernas Alta Densidad & Bici Indoor Quema-Grasa',
                'enfoque': 'Circuito de tren inferior con remate continuo en bicicleta estática',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['PIE_QUAD_BASE', 'CAL_LEGS', 'GLU_BASE', 'PIE_CALF', 'CAR_BIKE']
            },
        ]
    elif dias_semana == 4:
        return [
            {
                'nombre': 'Torso Metabólico A + Finisher Comba',
                'enfoque': 'Empuje y tracción combinados en superserie con salto a la comba',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BASE', 'ESP_REMO', 'CAL_PUSH', 'COR_PLANK', 'CAR_COMBA']
            },
            {
                'nombre': 'Pierna & Core A + Finisher Cinta',
                'enfoque': 'Cuádriceps, zancadas y zona media con carrera continua en cinta',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['PIE_QUAD_BASE', 'PIE_LUNGE', 'PIE_EXT', 'COR_CRUNCH', 'CAR_RUN']
            },
            {
                'nombre': 'Torso Metabólico B + Finisher Remo',
                'enfoque': 'Hombros, deltoides y brazos dinámicos con remo ergómetro',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['HOM_PRESS', 'ESP_JALON', 'HOM_LAT', 'BRA_TRICEPS', 'CAR_ROW']
            },
            {
                'nombre': 'Pierna & Glúteos B + Finisher Bici',
                'enfoque': 'Cadena posterior y glúteos con pedaleo de quema calórica en bici estática',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['PIE_POST', 'GLU_BASE', 'CAL_LEGS', 'COR_PLANK', 'CAR_BIKE']
            },
        ]
    elif dias_semana == 5:
        return [
            {
                'nombre': 'Push Metabólico + Finisher Cinta',
                'enfoque': 'Pectoral, deltoides y remate en cinta rodante',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BASE', 'PEC_INC', 'HOM_PRESS', 'CAL_PUSH', 'CAR_RUN']
            },
            {
                'nombre': 'Pull Metabólico + Finisher Remo',
                'enfoque': 'Espalda, bíceps y remate en remo ergómetro',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['ESP_JALON', 'ESP_REMO', 'BRA_BICEPS', 'COR_PLANK', 'CAR_ROW']
            },
            {
                'nombre': 'Piernas Quema-Grasa + Finisher Comba',
                'enfoque': 'Cuádriceps y glúteos con intervalos de salto a la comba',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['PIE_QUAD_BASE', 'PIE_POST', 'GLU_BASE', 'CAL_LEGS', 'CAR_COMBA']
            },
            {
                'nombre': 'Hombros & Core Metabólico',
                'enfoque': 'Deltoides, abdominales y elíptica de bajo impacto',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['HOM_PRESS', 'HOM_LAT', 'COR_CRUNCH', 'COR_SIDE_PLANK', 'CAR_ELLIPTIC']
            },
            {
                'nombre': 'Cardio HIIT & Acondicionamiento Cruzado',
                'enfoque': 'Circuito integral cardiovascular y resistencia de core',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['CAR_RUN', 'CAR_ROW', 'CAR_BIKE', 'COR_PLANK']
            },
        ]
    else:  # 6 días
        return [
            {
                'nombre': 'Push Metabólico + Cinta',
                'enfoque': 'Empuje con descansos cortos y carrera continua',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['PEC_BASE', 'PEC_INC', 'HOM_PRESS', 'CAR_RUN']
            },
            {
                'nombre': 'Pull Metabólico + Remo',
                'enfoque': 'Tracción dorsal y remo ergómetro',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['ESP_JALON', 'ESP_REMO', 'BRA_BICEPS', 'CAR_ROW']
            },
            {
                'nombre': 'Legs Metabólico + Bici',
                'enfoque': 'Piernas en circuito y ciclo indoor',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['PIE_QUAD_BASE', 'PIE_POST', 'GLU_BASE', 'CAR_BIKE']
            },
            {
                'nombre': 'Acondicionamiento Superior + Comba',
                'enfoque': 'Flexiones, remos con mancuerna y comba',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['CAL_PUSH', 'ESP_REMO', 'HOM_LAT', 'CAR_COMBA']
            },
            {
                'nombre': 'Acondicionamiento Inferior + Elíptica',
                'enfoque': 'Sentadillas aéreas, zancadas y elíptica',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['CAL_LEGS', 'PIE_LUNGE', 'COR_PLANK', 'CAR_ELLIPTIC']
            },
            {
                'nombre': 'HIIT Cardiovascular Cruzado',
                'enfoque': 'Bloques combinados de carrera, remo y bicicleta',
                'dias_numeros': [5],
                'dias_str': '5',
                'roles': ['CAR_RUN', 'CAR_ROW', 'CAR_BIKE', 'COR_SIDE_PLANK']
            },
        ]


def _esquema_resistencia(dias_semana: int) -> List[Dict[str, Any]]:
    """Distribuciones predominantemente cardiovasculares y calisténicas de resistencia (RES)"""
    if dias_semana <= 2:
        return [
            {
                'nombre': 'Fondo Cardiovascular & Capacidad Aeróbica',
                'enfoque': 'Sesión principal de carrera continua, remo ergómetro y estabilizadores de core',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['CAR_RUN', 'CAR_ROW', 'COR_PLANK', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Circuito de Resistencia Muscular & Calistenia',
                'enfoque': 'Rondas de flexiones, sentadillas aéreas, jalón y salto a la comba a altas repeticiones',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['CAL_PUSH', 'CAL_LEGS', 'ESP_JALON', 'PIE_LUNGE', 'CAR_COMBA']
            },
        ]
    elif dias_semana == 3:
        return [
            {
                'nombre': 'Running & Intervalos Cardiovasculares',
                'enfoque': 'Carrera continua o cambios de ritmo, salto a la comba y planchas isométricas',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['CAR_RUN', 'CAR_COMBA', 'COR_PLANK', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Circuito de Resistencia Muscular Funcional',
                'enfoque': 'Flexiones, sentadillas aéreas, dominadas/jalón y zancadas a altas repeticiones',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['CAL_PUSH', 'CAL_LEGS', 'ESP_PULLUP', 'PIE_LUNGE', 'COR_CRUNCH']
            },
            {
                'nombre': 'Capacidad Aeróbica — Ciclismo & Remo Ergómetro',
                'enfoque': 'Bloque de fondo continuo en bicicleta estática/spinning y remo Concept2',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['CAR_BIKE', 'CAR_ROW', 'CAR_ELLIPTIC', 'COR_PLANK']
            },
        ]
    elif dias_semana == 4:
        return [
            {
                'nombre': 'Running & Fondo Aeróbico',
                'enfoque': 'Sesión de carrera en cinta rodante o exterior con fortalecimiento de core',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['CAR_RUN', 'CAR_COMBA', 'COR_PLANK', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Resistencia Calisténica Tren Superior',
                'enfoque': 'Flexiones de pecho, dominadas o jalón, remo mancuerna y fondos',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['CAL_PUSH', 'ESP_PULLUP', 'ESP_REMO', 'BRA_TRICEPS', 'COR_CRUNCH']
            },
            {
                'nombre': 'Ciclismo & Remo Ergómetro (Capacidad)',
                'enfoque': 'Sesión combinada de ciclo indoor y remo ergómetro para potencia oxidativa',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['CAR_BIKE', 'CAR_ROW', 'CAR_ELLIPTIC']
            },
            {
                'nombre': 'Resistencia Muscular Tren Inferior & Core',
                'enfoque': 'Sentadillas aéreas a altas reps, zancadas, prensa y elevaciones colgado',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['CAL_LEGS', 'PIE_QUAD_BASE', 'PIE_LUNGE', 'PIE_CALF', 'COR_HANGING']
            },
        ]
    elif dias_semana == 5:
        return [
            {
                'nombre': 'Running Continuo & Base Aeróbica',
                'enfoque': 'Carrera continua prolongada para optimizar el volumen sistólico',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['CAR_RUN', 'COR_PLANK', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Resistencia Muscular Tren Superior',
                'enfoque': 'Calistenia de empuje y tracción a altas repeticiones',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['CAL_PUSH', 'ESP_PULLUP', 'ESP_REMO', 'HOM_PRESS', 'COR_CRUNCH']
            },
            {
                'nombre': 'Ciclismo / Spinning & Intervalos',
                'enfoque': 'Pedaleo continuo y cambios de cadencia con salto a la comba',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['CAR_BIKE', 'CAR_COMBA', 'COR_PLANK']
            },
            {
                'nombre': 'Resistencia Muscular Tren Inferior',
                'enfoque': 'Sentadillas aéreas, zancadas y curls femorales a altas repeticiones',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['CAL_LEGS', 'PIE_QUAD_BASE', 'PIE_POST', 'PIE_LUNGE']
            },
            {
                'nombre': 'Remo Ergómetro & Cross-Training',
                'enfoque': 'Potencia cardiorrespiratoria integral en remo Concept2 y elíptica',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['CAR_ROW', 'CAR_ELLIPTIC', 'COR_HANGING']
            },
        ]
    else:  # 6 días
        return [
            {
                'nombre': 'Running Fondo Aeróbico',
                'enfoque': 'Carrera continua de larga duración y core',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['CAR_RUN', 'CAR_COMBA', 'COR_PLANK', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Calistenia Resistencia Superior',
                'enfoque': 'Flexiones, dominadas y fondos en circuito',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['CAL_PUSH', 'ESP_PULLUP', 'ESP_REMO', 'BRA_TRICEPS']
            },
            {
                'nombre': 'Ciclismo & Cadencia',
                'enfoque': 'Sesión en bicicleta estática o ciclismo exterior con remo',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['CAR_BIKE', 'CAR_ROW', 'CAR_COMBA']
            },
            {
                'nombre': 'Resistencia Muscular Piernas',
                'enfoque': 'Sentadillas aéreas y zancadas con peso corporal',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['CAL_LEGS', 'PIE_LUNGE', 'PIE_CALF', 'COR_CRUNCH']
            },
            {
                'nombre': 'Remo Ergómetro & Potencia',
                'enfoque': 'Intervalos de remo ergómetro de alta demanda y elíptica',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['CAR_ROW', 'CAR_ELLIPTIC', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Recuperación Activa & Senderismo',
                'enfoque': 'Caminata continua o senderismo suave con core y movilidad',
                'dias_numeros': [5],
                'dias_str': '5',
                'roles': ['CAR_WALK', 'FLL_YOGA', 'COR_PLANK']
            },
        ]


def _esquema_salud(dias_semana: int) -> List[Dict[str, Any]]:
    """Distribuciones protectoras de articulaciones, movilidad/yoga y cardio suave (SAL)"""
    if dias_semana <= 2:
        return [
            {
                'nombre': 'Movilidad Articular, Core & Fuerza Segura',
                'enfoque': 'Bloque de yoga/movilidad articular, tonificación guiada en máquina y planchas',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['FLL_YOGA', 'PIE_QUAD', 'ESP_REMO', 'CAL_PUSH', 'COR_PLANK']
            },
            {
                'nombre': 'Salud Cardiovascular Suave & Bienestar',
                'enfoque': 'Caminata/senderismo, bicicleta estática suave y activación de cadera/abductores',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['CAR_WALK', 'CAR_BIKE', 'CAL_LEGS', 'GLU_BASE', 'COR_SIDE_PLANK']
            },
        ]
    elif dias_semana == 3:
        return [
            {
                'nombre': 'Movilidad Articular & Tren Superior Postural',
                'enfoque': 'Yoga y movilidad, remo en polea baja y press de pecho en máquina guiado',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['FLL_YOGA', 'ESP_REMO', 'PEC_BASE', 'COR_PLANK']
            },
            {
                'nombre': 'Estabilidad de Cadera, Piernas & Glúteos',
                'enfoque': 'Prensa de piernas guiada con soporte lumbar, abductores y caminata activa',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['PIE_QUAD', 'GLU_BASE', 'PIE_POST', 'CAR_WALK']
            },
            {
                'nombre': 'Salud Cardiovascular Sin Impacto & Core',
                'enfoque': 'Bicicleta estática suave, elíptica y fortalecimiento abdominal controlado',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['CAR_BIKE', 'CAR_ELLIPTIC', 'COR_CRUNCH', 'COR_SIDE_PLANK']
            },
        ]
    elif dias_semana == 4:
        return [
            {
                'nombre': 'Movilidad & Tren Superior Postural',
                'enfoque': 'Yoga, remo con mancuerna o polea con apoyo de pecho y flexiones asistidas',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['FLL_YOGA', 'ESP_REMO', 'PEC_BASE', 'COR_PLANK']
            },
            {
                'nombre': 'Piernas Seguras & Cadena Lumbar',
                'enfoque': 'Prensa de piernas, máquina de abductores, curl femoral y caminata activa',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['PIE_QUAD', 'GLU_BASE', 'PIE_POST', 'CAR_WALK']
            },
            {
                'nombre': 'Cardio Aeróbico Moderado & Salud Cardíaca',
                'enfoque': 'Bicicleta estática suave y elíptica con planchas laterales suaves',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['CAR_BIKE', 'CAR_ELLIPTIC', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Tonificación Global & Flexibilidad Profunda',
                'enfoque': 'Sentadillas aéreas suaves, remo con apoyo, abductores y sesión de yoga',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['CAL_LEGS', 'ESP_REMO', 'GLU_ABD', 'FLL_YOGA']
            },
        ]
    elif dias_semana == 5:
        return [
            {
                'nombre': 'Movilidad & Fuerza Tren Superior',
                'enfoque': 'Yoga y movilidad con tonificación de espalda y pecho en máquina',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['FLL_YOGA', 'ESP_REMO', 'PEC_BASE', 'COR_PLANK']
            },
            {
                'nombre': 'Caminata Activa & Salud Cardiovascular',
                'enfoque': 'Caminata o senderismo continuo con elíptica sin impacto',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['CAR_WALK', 'CAR_ELLIPTIC', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Piernas Guiadas & Faja Lumbar',
                'enfoque': 'Prensa de piernas segura, abductores y curl femoral con apoyo',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['PIE_QUAD', 'GLU_BASE', 'PIE_POST', 'COR_CRUNCH']
            },
            {
                'nombre': 'Bicicleta Estática & Cardio Suave',
                'enfoque': 'Pedaleo continuo suave sin impacto articular y planchas',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['CAR_BIKE', 'COR_PLANK', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Yoga, Estiramientos & Bienestar',
                'enfoque': 'Secuencia profunda de relajación, respiración y elongación de columna',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['FLL_YOGA', 'CAL_LEGS', 'COR_PLANK']
            },
        ]
    else:  # 6 días
        return [
            {
                'nombre': 'Movilidad Postural & Tren Superior',
                'enfoque': 'Yoga y máquinas guiadas de torso con soporte lumbar',
                'dias_numeros': [0],
                'dias_str': '0',
                'roles': ['FLL_YOGA', 'ESP_REMO', 'PEC_BASE', 'COR_PLANK']
            },
            {
                'nombre': 'Caminata Activa & Core',
                'enfoque': 'Caminata o senderismo continuo con fortalecimiento de faja abdominal',
                'dias_numeros': [1],
                'dias_str': '1',
                'roles': ['CAR_WALK', 'COR_PLANK', 'COR_SIDE_PLANK']
            },
            {
                'nombre': 'Tonificación Tren Inferior Guiada',
                'enfoque': 'Prensa de piernas, abductores y femoral con apoyo',
                'dias_numeros': [2],
                'dias_str': '2',
                'roles': ['PIE_QUAD', 'GLU_BASE', 'PIE_POST', 'CAR_WALK']
            },
            {
                'nombre': 'Bicicleta Estática Suave',
                'enfoque': 'Pedaleo aeróbico moderado sin sobrecarga articular y core',
                'dias_numeros': [3],
                'dias_str': '3',
                'roles': ['CAR_BIKE', 'COR_SIDE_PLANK', 'COR_CRUNCH']
            },
            {
                'nombre': 'Tonificación Funcional Suave',
                'enfoque': 'Sentadillas aéreas suaves, remos y flexiones en banco',
                'dias_numeros': [4],
                'dias_str': '4',
                'roles': ['CAL_LEGS', 'ESP_REMO', 'CAL_PUSH', 'COR_PLANK']
            },
            {
                'nombre': 'Yoga Profundo & Longevidad Articular',
                'enfoque': 'Sesión restaurativa de flexibilidad, respiración y relajación',
                'dias_numeros': [5],
                'dias_str': '5',
                'roles': ['FLL_YOGA', 'CAR_WALK', 'COR_PLANK']
            },
        ]


def _obtener_esquema_dias(dias_semana: int, objetivo: str = 'HIP') -> List[Dict[str, Any]]:
    """
    Determina la distribución de rutinas y los días de la semana recomendados
    cruzando la meta de días con el objetivo específico del usuario.
    0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo.
    """
    if objetivo == 'FUE':
        return _esquema_fuerza(dias_semana)
    elif objetivo == 'DEF':
        return _esquema_definicion(dias_semana)
    elif objetivo == 'RES':
        return _esquema_resistencia(dias_semana)
    elif objetivo == 'SAL':
        return _esquema_salud(dias_semana)
    else:  # 'HIP' o por defecto
        return _esquema_hipertrofia(dias_semana)


def _obtener_descripcion_esquema(dias_semana: int, objetivo: str = 'HIP') -> str:
    """Devuelve un nombre amigable y descriptivo del esquema semanal para la interfaz"""
    nombres = {
        'HIP': {
            2: 'Esquema Full Body A/B (Hipertrofia)',
            3: 'Esquema Push / Pull / Legs (Hipertrofia Clásica)',
            4: 'Esquema Torso / Pierna Frecuencia 2',
            5: 'Esquema PPL + Especialización Deltoides/Glúteos',
            6: 'Esquema Push / Pull / Legs x2 Alto Rendimiento',
        },
        'FUE': {
            2: 'Esquema Fuerza Básica A/B (Banca & Sentadilla / Muerto & Militar)',
            3: 'Esquema Tríada de Levantamientos Básicos & Potencia',
            4: 'Esquema Torso / Pierna Fuerza Máxima (Básicos con Barra)',
            5: 'Esquema Especialización en Levantamientos Pesados',
            6: 'Esquema Heavy / Light Powerbuilding',
        },
        'DEF': {
            2: 'Esquema Full Body Metabólico + Remate Cardio HIIT',
            3: 'Esquema Push/Pull/Legs Densidad + Finisher Cardiovascular',
            4: 'Esquema Torso/Pierna Metabólico Quema-Grasa',
            5: 'Esquema Alta Densidad + Remates Cardio Cruzados',
            6: 'Esquema Metabólico Avanzado Quema-Grasa x6',
        },
        'RES': {
            2: 'Esquema Cardio Fondo + Circuito de Resistencia Muscular',
            3: 'Esquema Running + Calistenia Funcional + Ciclismo/Remo',
            4: 'Esquema Endurance 4 Días (Running, Calistenia, Ciclismo, Piernas)',
            5: 'Esquema Atleta Resistencia Integral (5 Disciplinas)',
            6: 'Esquema Triatlón & Calistenia de Fondo x6',
        },
        'SAL': {
            2: 'Esquema Movilidad Articular + Cardio Suave sin Impacto',
            3: 'Esquema Salud Postural + Piernas Seguras + Cardio Ligero',
            4: 'Esquema Bienestar Integral (Yoga, Tonificación Guiada, Cardio)',
            5: 'Esquema Longevidad & Movilidad 5 Días',
            6: 'Esquema Bienestar Activo Diario 30 min',
        },
    }
    return nombres.get(objetivo, {}).get(dias_semana, f"Esquema Personalizado {dias_semana} días")


# =============================================================================
# MAPEO INTELIGENTE DE ROLES A CONSULTAS EN EL CATÁLOGO OFICIAL
# =============================================================================

ROLE_QUERIES = {
    # Pectoral
    'PEC_BENCH_BAR': [
        {'nombre__icontains': 'Press de Banca Plano con Barra'},
        {'nombre__icontains': 'Press Inclinado con Mancuernas'},
        {'nombre__icontains': 'Press de Pecho en Máquina'},
        {'grupo_muscular': 'PEC'},
    ],
    'PEC_BASE': [
        {'nombre__icontains': 'Press de Banca Plano', 'tipo': 'LIB'},
        {'nombre__icontains': 'Press de Pecho en Máquina', 'tipo': 'MAQ'},
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
    # Espalda
    'ESP_DEADLIFT_BAR': [
        {'nombre__icontains': 'Peso Muerto Convencional (Deadlift)'},
        {'nombre__icontains': 'Peso Muerto Rumano con Mancuernas'},
        {'grupo_muscular': 'ESP'},
    ],
    'ESP_PULLUP': [
        {'nombre__icontains': 'Dominadas Pronas'},
        {'nombre__icontains': 'Dominadas Supinas'},
        {'nombre__icontains': 'Jalón al Pecho en Polea'},
        {'grupo_muscular': 'ESP'},
    ],
    'ESP_ROW_HEAVY': [
        {'nombre__icontains': 'Remo con Mancuerna a una Mano'},
        {'nombre__icontains': 'Remo en Polea Baja'},
        {'grupo_muscular': 'ESP'},
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
    # Piernas
    'PIE_SQUAT_BAR': [
        {'nombre__icontains': 'Sentadilla Trasera con Barra (Back Squat)'},
        {'nombre__icontains': 'Prensa de Piernas'},
        {'grupo_muscular': 'PIE'},
    ],
    'PIE_QUAD': [
        {'nombre__icontains': 'Prensa de Piernas'},
        {'nombre__icontains': 'Sentadilla Trasera'},
        {'grupo_muscular': 'PIE'},
    ],
    'PIE_QUAD_BASE': [
        {'nombre__icontains': 'Sentadilla Trasera con Barra'},
        {'nombre__icontains': 'Prensa de Piernas'},
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
    # Hombros
    'HOM_PRESS_BAR': [
        {'nombre__icontains': 'Press Militar de Hombros'},
        {'nombre__icontains': 'Press de Hombros en Máquina'},
        {'grupo_muscular': 'HOM'},
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
    # Brazos
    'BRA_TRICEPS': [
        {'nombre__icontains': 'Extensión de Tríceps en Polea'},
        {'nombre__icontains': 'Fondos en Paralelas'},
        {'nombre__icontains': 'Press Francés'},
        {'grupo_muscular': 'BRA'},
    ],
    'BRA_TRICEPS_ACC': [
        {'nombre__icontains': 'Press Francés'},
        {'nombre__icontains': 'Fondos de Tríceps en Banco'},
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
    # Glúteos
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
    # Calistenia & Funcional
    'CAL_PUSH': [
        {'nombre__icontains': 'Flexiones de Pecho'},
        {'nombre__icontains': 'Fondos en Paralelas'},
        {'nombre__icontains': 'Fondos de Tríceps en Banco'},
        {'tipo': 'CAL', 'grupo_muscular': 'PEC'},
    ],
    'CAL_LEGS': [
        {'nombre__icontains': 'Sentadillas Aéreas'},
        {'nombre__icontains': 'Zancadas con Mancuernas'},
        {'tipo': 'CAL', 'grupo_muscular': 'PIE'},
    ],
    # Core
    'COR_PLANK': [
        {'nombre__icontains': 'Plancha Abdominal Isométrica'},
        {'nombre__icontains': 'Plancha Lateral'},
        {'grupo_muscular': 'COR'},
    ],
    'COR_SIDE_PLANK': [
        {'nombre__icontains': 'Plancha Lateral'},
        {'nombre__icontains': 'Plancha Abdominal Isométrica'},
        {'grupo_muscular': 'COR'},
    ],
    'COR_CRUNCH': [
        {'nombre__icontains': 'Abdominales Crunch en Suelo'},
        {'nombre__icontains': 'Elevaciones de Piernas Colgado'},
        {'grupo_muscular': 'COR'},
    ],
    'COR_HANGING': [
        {'nombre__icontains': 'Elevaciones de Piernas Colgado'},
        {'nombre__icontains': 'Abdominales Crunch en Suelo'},
        {'grupo_muscular': 'COR'},
    ],
    # Cardiovascular & Outdoor
    'CAR_RUN': [
        {'nombre__icontains': 'Correr en Cinta'},
        {'nombre__icontains': 'Correr al Aire Libre'},
        {'grupo_muscular': 'CAR'},
    ],
    'CAR_BIKE': [
        {'nombre__icontains': 'Bicicleta Estática / Ciclo Indoor'},
        {'nombre__icontains': 'Ciclismo al Aire Libre'},
        {'grupo_muscular': 'CAR'},
    ],
    'CAR_ROW': [
        {'nombre__icontains': 'Remo Ergómetro'},
        {'grupo_muscular': 'CAR'},
    ],
    'CAR_ELLIPTIC': [
        {'nombre__icontains': 'Elíptica'},
        {'nombre__icontains': 'Escaladora'},
        {'grupo_muscular': 'CAR'},
    ],
    'CAR_COMBA': [
        {'nombre__icontains': 'Salto a la Comba'},
        {'nombre__icontains': 'Remo Ergómetro'},
        {'grupo_muscular': 'CAR'},
    ],
    'CAR_WALK': [
        {'nombre__icontains': 'Caminata / Senderismo'},
        {'nombre__icontains': 'Elíptica'},
        {'grupo_muscular': 'CAR'},
    ],
    # Flexibilidad & Movilidad
    'FLL_YOGA': [
        {'nombre__icontains': 'Yoga y Movilidad Articular'},
        {'nombre__icontains': 'Danza Contemporánea'},
        {'tipo': 'FLL'},
    ],
}


def _buscar_ejercicio_por_rol(
    rol: str,
    ya_usados_ids: set,
    preferir_maquinas: bool = False,
    objetivo: str = 'HIP'
) -> Optional[Ejercicio]:
    """
    Localiza en el catálogo oficial el ejercicio más idóneo para un rol dado,
    evitando duplicarlo en la misma sesión y respetando preferencias biomecánicas y de objetivo.
    """
    consultas = ROLE_QUERIES.get(rol, [{'nombre__icontains': rol}])
    es_rol_no_pesas = rol.startswith(('FLL', 'CAR', 'OUT', 'DEP', 'DAN', 'COR'))

    # 1. Si se prefieren máquinas (principiante o senior), priorizar tipo MAQ solo en roles de sobrecarga
    if preferir_maquinas and not es_rol_no_pesas:
        for q in consultas:
            if 'tipo' in q and q['tipo'] != 'MAQ':
                continue
            q_maq = {**q, 'tipo': 'MAQ'}
            ej = Ejercicio.objects.filter(**q_maq).exclude(id__in=ya_usados_ids).first()
            if ej:
                return ej

    # 2. Si el objetivo es FUERZA y no se fuerzan máquinas, priorizar peso libre (LIB) o calistenia (CAL)
    if objetivo == 'FUE' and not preferir_maquinas and not es_rol_no_pesas:
        for q in consultas:
            if 'tipo' in q and q['tipo'] not in ['LIB', 'CAL']:
                continue
            q_fuerza = {**q, 'tipo__in': ['LIB', 'CAL']}
            ej = Ejercicio.objects.filter(**q_fuerza).exclude(id__in=ya_usados_ids).first()
            if ej:
                return ej

    # 3. Búsqueda normal según la lista de prioridades de cada rol
    for q in consultas:
        ej = Ejercicio.objects.filter(**q).exclude(id__in=ya_usados_ids).first()
        if ej:
            return ej

    # 4. Fallback por grupo muscular o tipo
    grupo_prefijo = rol.split('_')[0]
    if grupo_prefijo in ['PEC', 'ESP', 'PIE', 'HOM', 'BRA', 'GLU', 'COR', 'CAR']:
        ej = Ejercicio.objects.filter(grupo_muscular=grupo_prefijo).exclude(id__in=ya_usados_ids).first()
        if ej:
            return ej
    elif grupo_prefijo == 'FLL':
        ej = Ejercicio.objects.filter(tipo__in=['FLL', 'DAN']).exclude(id__in=ya_usados_ids).first()
        if ej:
            return ej

    # 5. Fallback final
    return Ejercicio.objects.exclude(id__in=ya_usados_ids).first()


# =============================================================================
# ESTIMACIÓN INTELIGENTE DE CARGAS (HISTORIAL O PESOS DE PARTIDA)
# =============================================================================

def estimar_peso_partida(ejercicio: Ejercicio, nivel: str = 'PR', genero: str = 'H') -> Optional[float]:
    """
    Calcula un peso de partida biomecánicamente seguro y realista en kg para un ejercicio
    cuando el usuario no tiene historial previo, basado en:
    - Nivel del usuario: 'PR' (Principiante), 'IN' (Intermedio), 'AV' (Avanzado).
    - Género / Sexo: 'H' (Hombre) / 'M' (Mujer) / 'O' (Otro).
    - Tipo de ejercicio, grupo muscular y patrón de movimiento.
    """
    if ejercicio.modalidad != 'REPS_PESO' or ejercicio.tipo == 'CAL':
        return None

    nombre_lower = (ejercicio.nombre or '').lower()

    # Si es ejercicio calisténico o con peso corporal (dominadas, flexiones, fondos, planchas)
    if any(k in nombre_lower for k in ['dominada', 'flexion', 'flexión', 'fondo', 'abdomina', 'plancha', 'rueda']):
        return None

    # Normalizar género ('H' o 'M')
    es_mujer = (genero == 'M')

    # Factores por nivel (0: PR, 1: IN, 2: AV)
    idx_nivel = 0 if nivel == 'PR' else (1 if nivel == 'IN' else 2)

    # 1. Grandes levantamientos y Tren Inferior
    if 'prensa' in nombre_lower:
        # Prensa de piernas: PR / IN / AV
        pesos_h = [70.0, 120.0, 170.0]
        pesos_m = [40.0, 75.0, 110.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'sentadilla con barra' in nombre_lower or ('sentadilla' in nombre_lower and 'barra' in nombre_lower):
        pesos_h = [40.0, 70.0, 100.0]
        pesos_m = [25.0, 45.0, 65.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'sentadilla' in nombre_lower and ('mancuerna' in nombre_lower or 'goblet' in nombre_lower):
        pesos_h = [12.0, 20.0, 28.0]
        pesos_m = [8.0, 14.0, 20.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'peso muerto' in nombre_lower:
        pesos_h = [50.0, 85.0, 120.0]
        pesos_m = [30.0, 50.0, 75.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'hip thrust' in nombre_lower:
        pesos_h = [40.0, 70.0, 100.0]
        pesos_m = [35.0, 60.0, 90.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if any(k in nombre_lower for k in ['zancada', 'lunge', 'búlgar', 'bulgar']):
        pesos_h = [8.0, 14.0, 20.0]
        pesos_m = [5.0, 10.0, 14.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'extensi' in nombre_lower and 'cuadricep' in nombre_lower:
        pesos_h = [30.0, 50.0, 70.0]
        pesos_m = [20.0, 35.0, 50.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'curl femoral' in nombre_lower or 'femoral' in nombre_lower:
        pesos_h = [25.0, 45.0, 60.0]
        pesos_m = [15.0, 30.0, 45.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if any(k in nombre_lower for k in ['abductor', 'aductor']):
        pesos_h = [30.0, 50.0, 70.0]
        pesos_m = [25.0, 45.0, 65.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if any(k in nombre_lower for k in ['gemelo', 'talon', 'talón', 'pantorrilla']):
        pesos_h = [40.0, 70.0, 100.0]
        pesos_m = [25.0, 45.0, 70.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    # 2. Pectoral y Empuje Horizontal
    if ('press' in nombre_lower and 'mancuerna' in nombre_lower) or 'press con mancuernas' in nombre_lower:
        pesos_h = [12.0, 20.0, 28.0]
        pesos_m = [6.0, 12.0, 16.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'press de banca' in nombre_lower or 'press banca' in nombre_lower or ('banca' in nombre_lower and 'press' in nombre_lower):
        pesos_h = [35.0, 60.0, 85.0]
        pesos_m = [17.5, 30.0, 45.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'press de pecho' in nombre_lower or ('press' in nombre_lower and 'máquina' in nombre_lower):
        pesos_h = [35.0, 55.0, 75.0]
        pesos_m = [20.0, 35.0, 50.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if any(k in nombre_lower for k in ['apertura', 'contractora', 'pec deck', 'cruces', 'cruce de polea']):
        pesos_h = [25.0, 40.0, 60.0]
        pesos_m = [15.0, 25.0, 35.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    # 3. Espalda y Tracción
    if 'jalón' in nombre_lower or 'jalon' in nombre_lower:
        pesos_h = [35.0, 55.0, 75.0]
        pesos_m = [20.0, 35.0, 45.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'remo con barra' in nombre_lower:
        pesos_h = [35.0, 60.0, 80.0]
        pesos_m = [20.0, 35.0, 50.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'remo' in nombre_lower and ('polea' in nombre_lower or 'gironda' in nombre_lower or 'máquina' in nombre_lower or 'maquina' in nombre_lower):
        pesos_h = [35.0, 55.0, 75.0]
        pesos_m = [20.0, 35.0, 45.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'remo con mancuerna' in nombre_lower:
        pesos_h = [14.0, 22.0, 30.0]
        pesos_m = [8.0, 14.0, 20.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'pull-over' in nombre_lower or 'pullover' in nombre_lower:
        pesos_h = [14.0, 20.0, 28.0]
        pesos_m = [8.0, 12.0, 18.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    # 4. Hombro y Deltoides
    if 'press militar' in nombre_lower or ('hombro' in nombre_lower and 'barra' in nombre_lower):
        pesos_h = [25.0, 40.0, 55.0]
        pesos_m = [15.0, 22.5, 32.5]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'press de hombro' in nombre_lower or ('press' in nombre_lower and 'hombro' in nombre_lower):
        pesos_h = [25.0, 45.0, 65.0]
        pesos_m = [15.0, 25.0, 35.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'lateral' in nombre_lower:
        pesos_h = [6.0, 10.0, 14.0]
        pesos_m = [3.0, 6.0, 9.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if any(k in nombre_lower for k in ['pájaro', 'pajaro', 'posterior', 'face pull']):
        pesos_h = [15.0, 25.0, 40.0]
        pesos_m = [10.0, 15.0, 25.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    # 5. Brazos (Bíceps y Tríceps)
    if 'curl' in nombre_lower and 'bíceps' in nombre_lower:
        pesos_h = [16.0, 26.0, 36.0]
        pesos_m = [8.0, 14.0, 20.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    if 'tríceps' in nombre_lower or 'triceps' in nombre_lower:
        pesos_h = [20.0, 35.0, 50.0]
        pesos_m = [10.0, 20.0, 30.0]
        return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]

    # 6. Fallback General por Grupo Muscular si no hubo coincidencia específica
    grupo = ejercicio.grupo_muscular
    if grupo == 'PIE':
        pesos_h = [35.0, 60.0, 90.0]
        pesos_m = [20.0, 40.0, 60.0]
    elif grupo in ['PEC', 'ESP']:
        pesos_h = [30.0, 50.0, 70.0]
        pesos_m = [18.0, 30.0, 45.0]
    elif grupo in ['HOM', 'BRA']:
        pesos_h = [12.0, 20.0, 30.0]
        pesos_m = [6.0, 12.0, 18.0]
    elif grupo == 'GLU':
        pesos_h = [35.0, 60.0, 85.0]
        pesos_m = [30.0, 50.0, 75.0]
    else:
        pesos_h = [20.0, 35.0, 50.0]
        pesos_m = [12.0, 20.0, 30.0]

    return pesos_m[idx_nivel] if es_mujer else pesos_h[idx_nivel]


def obtener_peso_objetivo_recomendado(usuario: User, ejercicio: Ejercicio, nivel: str = 'PR', genero: str = 'H'):
    """
    Obtiene el peso objetivo sugerido para el recomendador:
    1. Si el usuario ya entrenó este ejercicio, devuelve el peso de su última sesión ('historial').
    2. Si nunca lo ha entrenado, estima el peso de partida según nivel y género ('sugerido').
    3. Si es calistenia pura o por tiempo, devuelve None ('corporal' o 'tiempo').
    """
    if ejercicio.modalidad != 'REPS_PESO':
        return None, 'tiempo'

    nombre_lower = (ejercicio.nombre or '').lower()
    if ejercicio.tipo == 'CAL' and not any(k in nombre_lower for k in ['lastre', 'mancuerna', 'peso']):
        return None, 'corporal'

    # 1. Buscar en el historial de entrenamiento del usuario
    if usuario and usuario.is_authenticated:
        ultima_serie_con_peso = Serie.objects.filter(
            registro__usuario=usuario,
            registro__ejercicio=ejercicio,
            peso_kg__isnull=False,
            peso_kg__gt=0
        ).order_by('-registro__fecha', '-id').first()

        if ultima_serie_con_peso and ultima_serie_con_peso.peso_kg:
            return float(ultima_serie_con_peso.peso_kg), 'historial'

    # 2. Si no hay historial, calcular peso de partida por nivel y género
    peso_partida = estimar_peso_partida(ejercicio, nivel=nivel, genero=genero)
    if peso_partida is not None:
        return float(peso_partida), 'sugerido'

    return None, 'corporal'


def obtener_distancia_objetivo_recomendada(usuario: User, ejercicio: Ejercicio, nivel: str = 'PR') -> Optional[float]:
    """
    Obtiene la distancia objetivo para ejercicios que involucran carrera o desplazamiento.
    """
    if not getattr(ejercicio, 'es_distancia', False):
        return None

    if usuario and usuario.is_authenticated:
        ult_serie_dist = Serie.objects.filter(
            registro__usuario=usuario,
            registro__ejercicio=ejercicio,
            distancia_km__isnull=False,
            distancia_km__gt=0
        ).order_by('-registro__fecha', '-id').first()
        if ult_serie_dist and ult_serie_dist.distancia_km:
            return float(ult_serie_dist.distancia_km)

    # Distancia de partida por nivel (3k, 5k, 8k)
    if nivel == 'PR':
        return 3.0
    elif nivel == 'IN':
        return 5.0
    else:
        return 8.0


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

    # 4. Obtención del Esquema de División (Split) Adaptado al Objetivo
    esquema = _obtener_esquema_dias(dias_semana, objetivo)
    descripcion_esquema = _obtener_descripcion_esquema(dias_semana, objetivo)
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
        roles = list(rut_data['roles'])

        # Ajuste de cantidad de ejercicios según nivel y duración
        max_ej = cfg_niv['max_ejercicios']
        if duracion == 'RAPIDO':
            max_ej = min(max_ej, 4)
        elif duracion == 'COMPLETO':
            max_ej = min(max_ej + 1, 7)
        roles = roles[:max_ej]

        # Ajuste de roles si el usuario es mujer (mayor presencia de glúteos/isquios si es día de pierna)
        if genero == 'M' and any('PIE' in r for r in roles) and objetivo not in ['RES', 'SAL']:
            if 'GLU_BASE' not in roles and len(roles) >= 3:
                roles[-1] = 'GLU_BASE'

        ejercicios_rutina = []
        ya_usados = set()

        for orden, rol in enumerate(roles, start=1):
            ej = _buscar_ejercicio_por_rol(
                rol,
                ya_usados,
                preferir_maquinas=preferir_maquinas,
                objetivo=objetivo
            )
            if not ej:
                continue

            ya_usados.add(ej.id)

            nombre_lower = ej.nombre.lower()
            es_cardio_prolongado = any(k in nombre_lower for k in [
                'correr', 'cinta', 'running', 'bicicleta', 'ciclismo', 'spinning',
                'elíptica', 'caminata', 'senderismo', 'hiking', 'yoga', 'danza',
                'partido', 'pádel', 'fútbol', 'baloncesto'
            ])

            # Cálculo de series, repeticiones y tiempo
            if ej.modalidad == 'TIEMPO':
                reps = None
                if es_cardio_prolongado:
                    # Sesiones continuas de cardio o movilidad
                    series = 1
                    if objetivo == 'DEF':
                        # Finisher metabólico quema-grasa
                        tiempo_seg = 720 if nivel == 'PR' else (900 if nivel == 'IN' else 1200)  # 12, 15, 20 min
                    elif objetivo == 'RES':
                        # Fondo cardiovascular principal
                        tiempo_seg = 1200 if nivel == 'PR' else (1800 if nivel == 'IN' else 2400)  # 20, 30, 40 min
                    elif objetivo == 'SAL':
                        # Cardio suave o yoga para salud
                        tiempo_seg = 900 if nivel == 'PR' else (1200 if nivel == 'IN' else 1500)  # 15, 20, 25 min
                    else:
                        tiempo_seg = 900  # 15 min por defecto
                elif any(k in nombre_lower for k in ['remo ergómetro', 'escaladora']):
                    # Cardio de alta intensidad / ergómetro
                    if objetivo == 'RES':
                        series = 1
                        tiempo_seg = 900 if nivel == 'PR' else (1200 if nivel == 'IN' else 1500)  # 15-20 min
                    else:
                        series = 1
                        tiempo_seg = 600 if nivel == 'PR' else 900  # 10-15 min
                elif 'comba' in nombre_lower:
                    # Intervalos de salto a la comba
                    series = 3
                    tiempo_seg = 60 if nivel == 'PR' else (90 if nivel == 'IN' else 120)  # 60s, 90s, 120s
                else:
                    # Planchas y ejercicios isométricos de core
                    series = 3
                    tiempo_seg = 30 if nivel == 'PR' else (45 if nivel == 'IN' else 60)

                # Formateo amigable para la interfaz
                if tiempo_seg >= 60:
                    mins = tiempo_seg // 60
                    rest_s = tiempo_seg % 60
                    tiempo_display = f"{mins} min" if rest_s == 0 else f"{mins}m {rest_s}s"
                else:
                    tiempo_display = f"{tiempo_seg}s"
            else:
                tiempo_seg = None
                tiempo_display = None
                # Cálculo de series y repeticiones para peso y reps
                series = max(2, cfg_obj['series_base'] + cfg_niv['delta_series'])

                # Para ejercicios básicos pesados en Fuerza, aumentar series
                es_compuesto = (orden == 1) or any(k in nombre_lower for k in [
                    'sentadilla', 'prensa', 'press', 'jalón', 'peso muerto', 'remo', 'dominadas', 'fondos'
                ])
                if objetivo == 'FUE' and es_compuesto and orden <= 2:
                    series = min(series + 1, 5)

                reps = cfg_obj['reps_compuesto'] if es_compuesto else cfg_obj['reps_aislamiento']

            # Cálculo de peso por defecto (historial -> partida por nivel/género -> corporal)
            peso_obj, origen_peso = obtener_peso_objetivo_recomendado(
                usuario=usuario,
                ejercicio=ej,
                nivel=nivel,
                genero=genero
            )
            distancia_obj = obtener_distancia_objetivo_recomendada(
                usuario=usuario,
                ejercicio=ej,
                nivel=nivel
            )

            ejercicios_rutina.append({
                'orden': orden,
                'ejercicio_id': ej.id,
                'nombre': ej.nombre,
                'grupo_muscular': ej.grupo_muscular,
                'grupo_muscular_display': ej.get_grupo_muscular_display(),
                'tipo': ej.tipo,
                'tipo_display': ej.get_tipo_display(),
                'modalidad': ej.modalidad,
                'es_distancia': getattr(ej, 'es_distancia', False),
                'icono': ej.icono,
                'series_objetivo': series,
                'repeticiones_objetivo': reps,
                'tiempo_objetivo_segundos': tiempo_seg,
                'tiempo_display': tiempo_display,
                'peso_objetivo': peso_obj,
                'origen_peso': origen_peso,
                'distancia_objetivo_km': distancia_obj,
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
        'descripcion_esquema': descripcion_esquema,
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
