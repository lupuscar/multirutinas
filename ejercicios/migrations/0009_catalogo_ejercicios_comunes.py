from django.db import migrations
from ejercicios.catalogo_datos import CATALOGO_EJERCICIOS

# Mapeo para actualizar ejercicios demo o anteriores a sus nombres canónicos completos
MAPEO_NOMBRES_ANTERIORES = {
    'Chest Press': 'Press de Pecho en Máquina (Chest Press)',
    'Leg Press': 'Prensa de Piernas (Leg Press)',
    'Leg Extensions': 'Extensión de Cuádriceps (Leg Extension)',
    'Pec Fly': 'Contractora de Pecho / Pec Deck (Aperturas)',
    'Jalón al Pecho': 'Jalón al Pecho en Polea (Lat Pulldown)',
    'Biceps Curl': 'Curl de Bíceps en Polea / Máquina Scott',
    'Triceps': 'Extensión de Tríceps en Polea (Triceps Pushdown)',
    'Plancha Abdominal': 'Plancha Abdominal Isométrica (Plank)',
    'Remo con Mancuerna': 'Remo con Mancuerna a una Mano',
    'Correr al aire libre': 'Correr al Aire Libre (Outdoor Running)',
    'Partido de pádel': 'Partido de Pádel',
    'Danza contemporánea': 'Danza Contemporánea',
}


def poblar_catalogo_ejercicios(apps, schema_editor):
    Ejercicio = apps.get_model('ejercicios', 'Ejercicio')

    # 1. Renombrar / unificar nombres previos de demo si existen para no duplicar
    for nombre_antiguo, nombre_nuevo in MAPEO_NOMBRES_ANTERIORES.items():
        ej_antiguo = Ejercicio.objects.filter(nombre=nombre_antiguo, creado_por=None).first()
        if ej_antiguo:
            ej_nuevo = Ejercicio.objects.filter(nombre=nombre_nuevo, creado_por=None).first()
            if not ej_nuevo:
                ej_antiguo.nombre = nombre_nuevo
                ej_antiguo.save()

    # 2. Crear o actualizar todos los ejercicios del catálogo oficial
    for item in CATALOGO_EJERCICIOS:
        nombre = item['nombre']
        defaults = {
            'tipo': item['tipo'],
            'modalidad': item['modalidad'],
            'grupo_muscular': item['grupo_muscular'],
            'dificultad': item.get('dificultad', 'PRI'),
            'equipo_necesario': item.get('equipo_necesario', ''),
            'definicion': item.get('definicion', ''),
            'creado_por': None,  # Ejercicio oficial
        }

        ejercicio, creado = Ejercicio.objects.get_or_create(
            nombre=nombre,
            creado_por=None,
            defaults=defaults
        )

        # Si ya existía pero con campos en blanco o incompletos, los completamos
        if not creado:
            actualizado = False
            for campo, valor in defaults.items():
                if campo != 'creado_por' and not getattr(ejercicio, campo):
                    setattr(ejercicio, campo, valor)
                    actualizado = True
            if actualizado:
                ejercicio.save()


def revertir_catalogo(apps, schema_editor):
    # En reversión no eliminamos para proteger historiales de entrenamientos creados
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ejercicios', '0008_crear_actividades_deporte_danza_running'),
    ]

    operations = [
        migrations.RunPython(poblar_catalogo_ejercicios, revertir_catalogo),
    ]
