from django.core.management.base import BaseCommand
from ejercicios.models import Ejercicio
from ejercicios.catalogo_datos import CATALOGO_EJERCICIOS


class Command(BaseCommand):
    help = "Puebla o actualiza el catálogo oficial de ejercicios predeterminados de FitApp."

    def add_arguments(self, parser):
        parser.add_argument(
            '--actualizar-descripciones',
            action='store_true',
            help='Sobrescribe definiciones y equipo necesario de los ejercicios oficiales existentes con los valores por defecto del catálogo.'
        )

    def handle(self, *args, **options):
        actualizar_descripciones = options.get('actualizar_descripciones')
        self.stdout.write(self.style.NOTICE("Iniciando carga de ejercicios en el catálogo oficial..."))

        creados = 0
        actualizados = 0

        for item in CATALOGO_EJERCICIOS:
            nombre = item['nombre']
            defaults = {
                'tipo': item['tipo'],
                'modalidad': item['modalidad'],
                'grupo_muscular': item['grupo_muscular'],
                'dificultad': item.get('dificultad', 'PRI'),
                'equipo_necesario': item.get('equipo_necesario', ''),
                'definicion': item.get('definicion', ''),
                'creado_por': None,
            }

            ejercicio, fue_creado = Ejercicio.objects.get_or_create(
                nombre=nombre,
                creado_por=None,
                defaults=defaults
            )

            if fue_creado:
                creados += 1
            else:
                hubo_cambio = False
                if actualizar_descripciones:
                    for campo, val in defaults.items():
                        if campo != 'creado_por' and getattr(ejercicio, campo) != val:
                            setattr(ejercicio, campo, val)
                            hubo_cambio = True
                else:
                    # Rellenar solo campos que estuvieran vacíos
                    for campo, val in defaults.items():
                        if campo != 'creado_por' and not getattr(ejercicio, campo):
                            setattr(ejercicio, campo, val)
                            hubo_cambio = True

                if hubo_cambio:
                    ejercicio.save()
                    actualizados += 1

        total_oficiales = Ejercicio.objects.filter(creado_por=None).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Catálogo oficial sincronizado con éxito: {creados} creados, {actualizados} actualizados. "
                f"Total de ejercicios oficiales en catálogo: {total_oficiales}."
            )
        )
