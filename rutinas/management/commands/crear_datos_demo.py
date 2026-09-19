import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from ejercicios.models import Ejercicio, RegistroEjercicio, Serie
from rutinas.models import Rutina, RutinaEjercicio


class Command(BaseCommand):
    help = "Crea rutinas y un historial completo de entrenamientos demo con progresión para el Dashboard"

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            help='Nombre de usuario al que asignar los datos demo (por defecto todos los usuarios o el primero disponible)'
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina registros y rutinas demo previas antes de crearlas'
        )

    def handle(self, *args, **options):
        User = get_user_model()
        usuario_param = options.get('usuario')
        limpiar = options.get('limpiar')

        if usuario_param:
            usuarios = User.objects.filter(username=usuario_param)
            if not usuarios.exists():
                self.stderr.write(self.style.ERROR(f"Usuario '{usuario_param}' no encontrado."))
                return
        else:
            # Seleccionamos al usuario principal o a todos los activos
            usuarios = User.objects.all().order_by('id')
            if not usuarios.exists():
                self.stderr.write(self.style.ERROR("No hay usuarios en la base de datos para crear datos demo."))
                return

        self.stdout.write(self.style.SUCCESS("Iniciando generación de datos demo para el Dashboard..."))

        # 1. Asegurar catálogo de Ejercicios
        ejercicios_def = [
            {'nombre': 'Chest Press', 'grupo': 'PEC', 'tipo': 'MAQ', 'mod': 'REPS_PESO'},
            {'nombre': 'Pec Fly', 'grupo': 'PEC', 'tipo': 'MAQ', 'mod': 'REPS_PESO'},
            {'nombre': 'Leg Press', 'grupo': 'PIE', 'tipo': 'MAQ', 'mod': 'REPS_PESO'},
            {'nombre': 'Leg Extensions', 'grupo': 'PIE', 'tipo': 'MAQ', 'mod': 'REPS_PESO'},
            {'nombre': 'Biceps Curl', 'grupo': 'BRA', 'tipo': 'LIB', 'mod': 'REPS_PESO'},
            {'nombre': 'Triceps', 'grupo': 'BRA', 'tipo': 'LIB', 'mod': 'REPS_PESO'},
            {'nombre': 'Jalón al Pecho', 'grupo': 'ESP', 'tipo': 'MAQ', 'mod': 'REPS_PESO'},
            {'nombre': 'Remo con Mancuerna', 'grupo': 'ESP', 'tipo': 'LIB', 'mod': 'REPS_PESO'},
            {'nombre': 'Plancha Abdominal', 'grupo': 'COR', 'tipo': 'CAL', 'mod': 'TIEMPO'},
        ]

        ejercicios_dict = {}
        for ed in ejercicios_def:
            ej, _ = Ejercicio.objects.get_or_create(
                nombre=ed['nombre'],
                defaults={
                    'grupo_muscular': ed['grupo'],
                    'tipo': ed['tipo'],
                    'modalidad': ed['mod'],
                    'definicion': f"Técnica enfocada para el trabajo de {ed['nombre']}.",
                }
            )
            ejercicios_dict[ed['nombre']] = ej

        hoy = timezone.now().date()

        for user in usuarios:
            self.stdout.write(f"\n--- Procesando usuario: {user.username} ({user.email}) ---")

            if limpiar:
                self.stdout.write("Limpiando rutinas e historial demo previos...")
                Rutina.objects.filter(usuario=user, nombre__startswith="[Demo]").delete()
                RegistroEjercicio.objects.filter(usuario=user, etiqueta="Demo").delete()

            # 2. Crear Rutinas estructuradas
            rutinas_data = [
                {
                    'nombre': '[Demo] Torso Potencia (Empuje & Brazos)',
                    'desc': 'Foco en hipertrofia y fuerza para pecho, hombro y tríceps.',
                    'ejercicios': [
                        ('Chest Press', 4, 10),
                        ('Pec Fly', 3, 12),
                        ('Triceps', 4, 12),
                    ]
                },
                {
                    'nombre': '[Demo] Pierna Completa & Estabilidad',
                    'desc': 'Entrenamiento intenso de cuádriceps, glúteos y cadena posterior.',
                    'ejercicios': [
                        ('Leg Press', 4, 10),
                        ('Leg Extensions', 4, 12),
                        ('Plancha Abdominal', 3, None, 45),
                    ]
                },
                {
                    'nombre': '[Demo] Tracción & Brazos',
                    'desc': 'Espalda densa y bíceps con estímulo de alta tensión mecánica.',
                    'ejercicios': [
                        ('Jalón al Pecho', 4, 10),
                        ('Remo con Mancuerna', 3, 10),
                        ('Biceps Curl', 4, 12),
                    ]
                }
            ]

            for rd in rutinas_data:
                rutina, creada = Rutina.objects.get_or_create(
                    usuario=user,
                    nombre=rd['nombre'],
                    defaults={'descripcion': rd['desc']}
                )
                for orden, ej_info in enumerate(rd['ejercicios'], start=1):
                    nombre_ej = ej_info[0]
                    series_obj = ej_info[1]
                    reps_obj = ej_info[2]
                    tiempo_obj = ej_info[3] if len(ej_info) > 3 else None

                    ej_obj = ejercicios_dict.get(nombre_ej)
                    if ej_obj:
                        RutinaEjercicio.objects.get_or_create(
                            rutina=rutina,
                            ejercicio=ej_obj,
                            defaults={
                                'orden': orden,
                                'series_objetivo': series_obj,
                                'repeticiones_objetivo': reps_obj,
                                'tiempo_objetivo_segundos': tiempo_obj,
                            }
                        )

            # 3. Crear Historial de Sesiones con Progresión Realista de Cargas
            # Generamos 16 sesiones a lo largo de las últimas 5 semanas
            sesiones_calendario = []
            # Semanas hacia atrás: -32d, -30d, -28d, -25d, -23d, -21d, -18d, -16d, -14d, -11d, -9d, -7d, -4d, -2d, -1d, hoy
            dias_offsets = [32, 30, 28, 25, 23, 21, 18, 16, 14, 11, 9, 7, 5, 3, 1, 0]

            total_registros_creados = 0
            total_series_creadas = 0

            for idx, offset in enumerate(dias_offsets):
                fecha_sesion = hoy - datetime.timedelta(days=offset)
                # Factor de progresión: va aumentando del 0% al 40% a lo largo de las semanas
                factor = 1.0 + (idx * 0.025)

                tipo_dia = idx % 3  # 0: Torso, 1: Pierna, 2: Tracción

                if tipo_dia == 0:
                    ejercicios_sesion = [
                        ('Chest Press', Decimal('45.0') * Decimal(str(factor)), [10, 10, 8, 8]),
                        ('Pec Fly', Decimal('30.0') * Decimal(str(factor)), [12, 12, 10]),
                        ('Triceps', Decimal('20.0') * Decimal(str(factor)), [12, 10, 10]),
                    ]
                elif tipo_dia == 1:
                    ejercicios_sesion = [
                        ('Leg Press', Decimal('90.0') * Decimal(str(factor)), [10, 10, 10, 8]),
                        ('Leg Extensions', Decimal('35.0') * Decimal(str(factor)), [12, 12, 10]),
                        ('Plancha Abdominal', None, [40, 45, 50]), # Segundos
                    ]
                else:
                    ejercicios_sesion = [
                        ('Jalón al Pecho', Decimal('40.0') * Decimal(str(factor)), [10, 10, 8]),
                        ('Remo con Mancuerna', Decimal('18.0') * Decimal(str(factor)), [10, 10, 10]),
                        ('Biceps Curl', Decimal('12.0') * Decimal(str(factor)), [12, 10, 10]),
                    ]

                for nombre_ej, peso_base, series_data in ejercicios_sesion:
                    ej_obj = ejercicios_dict.get(nombre_ej)
                    if not ej_obj:
                        continue

                    # Creamos el registro del ejercicio
                    reg = RegistroEjercicio.objects.create(
                        usuario=user,
                        ejercicio=ej_obj,
                        etiqueta="Demo",
                        notas=f"Sesión completada con gran técnica y sobrecarga progresiva."
                    )
                    # Actualizamos la fecha mediante QuerySet para saltar auto_now_add
                    RegistroEjercicio.objects.filter(id=reg.id).update(fecha=fecha_sesion)
                    total_registros_creados += 1

                    # Creamos las series correspondientes
                    for num_serie, valor in enumerate(series_data, start=1):
                        if ej_obj.modalidad == 'TIEMPO':
                            Serie.objects.create(
                                registro=reg,
                                numero_serie=num_serie,
                                repeticiones=None,
                                peso_kg=None,
                                tiempo_segundos=int(valor)
                            )
                        else:
                            # Redondeamos el peso al medio kilo más cercano (ej: 47.5 kg)
                            peso_calculado = round(float(peso_base), 1)
                            Serie.objects.create(
                                registro=reg,
                                numero_serie=num_serie,
                                repeticiones=int(valor),
                                peso_kg=Decimal(str(peso_calculado)),
                                tiempo_segundos=None
                            )
                        total_series_creadas += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Completado para {user.username}: {len(rutinas_data)} rutinas demo, "
                    f"{total_registros_creados} registros de ejercicios y {total_series_creadas} series creadas."
                )
            )

        self.stdout.write(self.style.SUCCESS("\n¡Todos los datos demo han sido generados exitosamente!"))
        self.stdout.write("Accede ahora a /dashboard/ para ver todas las métricas, gráficas y progresión de fuerza.")
