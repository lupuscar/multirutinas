from django.db import migrations

def crear_ejercicios_iniciales(apps, schema_editor):
    Ejercicio = apps.get_model('ejercicios', 'Ejercicio')

    actividades = [
        {
            'nombre': 'Correr al aire libre',
            'definicion': 'Carrera continua o con cambios de ritmo en exterior (parques, asfalto o senderos). Desarrolla la resistencia cardiovascular, la capacidad pulmonar y la quema calórica global.',
            'tipo': 'OUT',
            'modalidad': 'TIEMPO',
            'dificultad': 'PRI',
            'grupo_muscular': 'CAR',
            'equipo_necesario': 'Zapatillas de running',
            'creado_por': None,
        },
        {
            'nombre': 'Danza contemporánea',
            'definicion': 'Sesión de expresión corporal, técnica de suelo, fluidez de movimiento y coreografía. Desarrolla la flexibilidad, el control del core, la fuerza isométrica y la coordinación dinámica.',
            'tipo': 'DAN',
            'modalidad': 'TIEMPO',
            'dificultad': 'INT',
            'grupo_muscular': 'FUL',
            'equipo_necesario': 'Ropa cómoda / Esterilla opcional',
            'creado_por': None,
        },
        {
            'nombre': 'Partido de pádel',
            'definicion': 'Partido individual o por parejas en pista reglamentaria. Entrenamiento aeróbico y anaeróbico de alta intensidad con sprints cortos, frenadas bruscas, golpeos de derecha, revés, voleas y bandejas.',
            'tipo': 'DEP',
            'modalidad': 'TIEMPO',
            'dificultad': 'PRI',
            'grupo_muscular': 'FUL',
            'equipo_necesario': 'Pala de pádel, pelotas, calzado de pádel',
            'creado_por': None,
        },
    ]

    for act in actividades:
        Ejercicio.objects.get_or_create(
            nombre=act['nombre'],
            defaults=act
        )


def revertir_ejercicios(apps, schema_editor):
    Ejercicio = apps.get_model('ejercicios', 'Ejercicio')
    Ejercicio.objects.filter(
        nombre__in=['Correr al aire libre', 'Danza contemporánea', 'Partido de pádel'],
        creado_por=None
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ejercicios', '0007_alter_ejercicio_equipo_necesario_and_more'),
    ]

    operations = [
        migrations.RunPython(crear_ejercicios_iniciales, revertir_ejercicios),
    ]
