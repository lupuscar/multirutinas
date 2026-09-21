from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from ejercicios.models import Ejercicio, RegistroEjercicio, Serie


class EjerciciosAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='carlos', password='password123')
        self.user2 = User.objects.create_user(username='maria', password='password123')

        # Ejercicio oficial del sistema
        self.ej_oficial = Ejercicio.objects.create(
            nombre='Press Militar Oficial',
            definicion='Técnica básica',
            modalidad='REPS_PESO',
            grupo_muscular='HOM',
            tipo='LIB',
            dificultad='PRI',
            creado_por=None
        )

        # Ejercicio creado por carlos
        self.ej_carlos = Ejercicio.objects.create(
            nombre='Fondos en Paralelas de Carlos',
            definicion='Técnica de tríceps',
            modalidad='REPS_PESO',
            grupo_muscular='BRA',
            tipo='CAL',
            dificultad='INT',
            creado_por=self.user1
        )

    def test_lista_ejercicios(self):
        """Verifica que el catálogo carga correctamente y aplica filtros"""
        self.client.login(username='carlos', password='password123')
        response = self.client.get(reverse('ejercicios:ejercicios'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Press Militar Oficial')
        self.assertContains(response, 'Fondos en Paralelas de Carlos')

        # Filtro de sólo mis ejercicios
        res_mios = self.client.get(reverse('ejercicios:ejercicios') + '?origen=mis_ejercicios')
        self.assertContains(res_mios, 'Fondos en Paralelas de Carlos')
        self.assertNotContains(res_mios, 'Press Militar Oficial')

    def test_crear_ejercicio(self):
        """Verifica que un usuario autenticado puede crear un ejercicio"""
        self.client.login(username='carlos', password='password123')
        data = {
            'nombre': 'Dominadas Australianas',
            'modalidad': 'REPS_PESO',
            'grupo_muscular': 'ESP',
            'tipo': 'CAL',
            'dificultad': 'PRI',
            'equipo_necesario': 'Barra baja',
            'definicion': 'Excelente para empezar en calistenia.',
            'video': ''
        }
        response = self.client.post(reverse('ejercicios:crear_ejercicio'), data)
        self.assertRedirects(response, reverse('ejercicios:ejercicios'))

        nuevo_ej = Ejercicio.objects.filter(nombre='Dominadas Australianas').first()
        self.assertIsNotNone(nuevo_ej)
        self.assertEqual(nuevo_ej.creado_por, self.user1)

    def test_editar_ejercicio_propio(self):
        """Un usuario puede editar un ejercicio que él mismo creó"""
        self.client.login(username='carlos', password='password123')
        data = {
            'nombre': 'Fondos en Paralelas Modificados',
            'modalidad': 'REPS_PESO',
            'grupo_muscular': 'BRA',
            'tipo': 'CAL',
            'dificultad': 'AVA',
            'equipo_necesario': 'Paralelas',
            'definicion': 'Con lastre',
            'video': ''
        }
        response = self.client.post(reverse('ejercicios:editar_ejercicio', args=[self.ej_carlos.id]), data)
        self.assertRedirects(response, reverse('ejercicios:ejercicios'))

        self.ej_carlos.refresh_from_db()
        self.assertEqual(self.ej_carlos.nombre, 'Fondos en Paralelas Modificados')
        self.assertEqual(self.ej_carlos.dificultad, 'AVA')

    def test_no_puede_editar_ejercicio_oficial(self):
        """Un usuario normal NO puede editar un ejercicio del catálogo oficial"""
        self.client.login(username='carlos', password='password123')
        response = self.client.get(reverse('ejercicios:editar_ejercicio', args=[self.ej_oficial.id]))
        self.assertRedirects(response, reverse('ejercicios:ejercicios'))

    def test_no_puede_editar_ejercicio_de_otro_usuario(self):
        """María no puede editar el ejercicio creado por Carlos"""
        self.client.login(username='maria', password='password123')
        response = self.client.get(reverse('ejercicios:editar_ejercicio', args=[self.ej_carlos.id]))
        self.assertRedirects(response, reverse('ejercicios:ejercicios'))

    def test_eliminar_ejercicio_propio(self):
        """Un usuario puede eliminar su propio ejercicio"""
        self.client.login(username='carlos', password='password123')
        response = self.client.post(reverse('ejercicios:eliminar_ejercicio', args=[self.ej_carlos.id]))
        self.assertRedirects(response, reverse('ejercicios:ejercicios'))
        self.assertFalse(Ejercicio.objects.filter(id=self.ej_carlos.id).exists())

    def test_detalle_ejercicio_con_record(self):
        """Verifica que la vista de detalle carga la información y los récords personales"""
        self.client.login(username='carlos', password='password123')
        
        # Simulamos una serie grabada
        reg = RegistroEjercicio.objects.create(usuario=self.user1, ejercicio=self.ej_carlos)
        Serie.objects.create(registro=reg, numero_serie=1, repeticiones=12, peso_kg=25.0)

        response = self.client.get(reverse('ejercicios:detalle_ejercicio', args=[self.ej_carlos.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fondos en Paralelas de Carlos')
        self.assertContains(response, '25 kg')

    def test_crear_ejercicios_deporte_danza_aire_libre(self):
        """Verifica que se pueden crear actividades como pádel, danza y running al aire libre"""
        self.client.login(username='carlos', password='password123')

        # 1. Crear un partido de pádel (Deporte)
        data_padel = {
            'nombre': 'Partido de Pádel Mixto',
            'modalidad': 'TIEMPO',
            'grupo_muscular': 'FUL',
            'tipo': 'DEP',
            'dificultad': 'PRI',
            'equipo_necesario': 'Pala de pádel y pelotas',
            'definicion': 'Partido de fin de semana con amigos.',
            'video': ''
        }
        res_padel = self.client.post(reverse('ejercicios:crear_ejercicio'), data_padel)
        self.assertRedirects(res_padel, reverse('ejercicios:ejercicios'))

        ej_padel = Ejercicio.objects.filter(nombre='Partido de Pádel Mixto').first()
        self.assertIsNotNone(ej_padel)
        self.assertEqual(ej_padel.tipo, 'DEP')
        self.assertEqual(ej_padel.modalidad, 'TIEMPO')
        self.assertEqual(ej_padel.grupo_muscular, 'FUL')
        self.assertEqual(ej_padel.icono, 'fa-solid fa-table-tennis-paddle-ball')

        # 2. Crear Danza Contemporánea
        data_danza = {
            'nombre': 'Clase de Danza Contemporánea',
            'modalidad': 'TIEMPO',
            'grupo_muscular': 'AGI',
            'tipo': 'DAN',
            'dificultad': 'INT',
            'equipo_necesario': 'Ropa elástica',
            'definicion': 'Trabajo de suelo, saltos y secuencias coreográficas.',
            'video': ''
        }
        res_danza = self.client.post(reverse('ejercicios:crear_ejercicio'), data_danza)
        self.assertRedirects(res_danza, reverse('ejercicios:ejercicios'))

        ej_danza = Ejercicio.objects.filter(nombre='Clase de Danza Contemporánea').first()
        self.assertIsNotNone(ej_danza)
        self.assertEqual(ej_danza.tipo, 'DAN')
        self.assertEqual(ej_danza.icono, 'fa-solid fa-person-dancing')

    def test_filtro_por_tipo_de_actividad(self):
        """Verifica que el catálogo permite filtrar por tipo de actividad (deportes, aire libre, etc.)"""
        self.client.login(username='carlos', password='password123')

        # Creamos una actividad deportiva
        Ejercicio.objects.create(
            nombre='Partido de Baloncesto 3x3',
            modalidad='TIEMPO',
            grupo_muscular='FUL',
            tipo='DEP',
            creado_por=self.user1
        )

        # Filtramos por tipo DEP
        response = self.client.get(reverse('ejercicios:ejercicios') + '?tipo=DEP')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Partido de Baloncesto 3x3')
        # No debe aparecer el ejercicio militar (LIB)
        self.assertNotContains(response, 'Press Militar Oficial')

    def test_formato_duracion_en_serie_y_detalle(self):
        """Verifica que sesiones de 90 minutos se formateen como 1h 30m en lugar de segundos crudos"""
        self.client.login(username='carlos', password='password123')

        ej_running = Ejercicio.objects.create(
            nombre='Running 10K',
            modalidad='TIEMPO',
            grupo_muscular='CAR',
            tipo='OUT',
            creado_por=self.user1
        )

        reg = RegistroEjercicio.objects.create(usuario=self.user1, ejercicio=ej_running)
        serie = Serie.objects.create(registro=reg, numero_serie=1, tiempo_segundos=5400) # 90 minutos

        # Comprobar representación __str__ de la serie
        self.assertIn('1h 30m', str(serie))

        # Comprobar vista de detalle con récord formateado
        response = self.client.get(reverse('ejercicios:detalle_ejercicio', args=[ej_running.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1h 30m')

    def test_catalogo_predeterminado_incluye_maquinas_calistenia_cinta_y_bici(self):
        """Verifica que el catálogo predeterminado contiene las máquinas, calistenia, cinta y bici más comunes"""
        self.client.login(username='carlos', password='password123')
        response = self.client.get(reverse('ejercicios:ejercicios'))
        self.assertEqual(response.status_code, 200)

        ejercicios_esperados = [
            'Prensa de Piernas (Leg Press)',
            'Extensión de Cuádriceps (Leg Extension)',
            'Dominadas Pronas (Pull-ups)',
            'Fondos en Paralelas (Dips)',
            'Correr en Cinta (Treadmill Running)',
            'Correr al Aire Libre (Outdoor Running)',
            'Bicicleta Estática / Ciclo Indoor (Spinning)',
            'Ciclismo al Aire Libre',
            'Press de Banca Plano con Barra',
        ]
        for ej_nombre in ejercicios_esperados:
            ej = Ejercicio.objects.filter(nombre=ej_nombre, creado_por=None).first()
            self.assertIsNotNone(ej, f"El ejercicio predeterminado '{ej_nombre}' no existe en el catálogo oficial.")

    def test_iconos_inteligentes_asignados(self):
        """Verifica que los iconos de FontAwesome se asignan contextualmente según la actividad"""
        ej_cinta = Ejercicio.objects.filter(nombre='Correr en Cinta (Treadmill Running)').first()
        if ej_cinta:
            self.assertEqual(ej_cinta.icono, 'fa-solid fa-person-running')

        ej_bici = Ejercicio.objects.filter(nombre='Bicicleta Estática / Ciclo Indoor (Spinning)').first()
        if ej_bici:
            self.assertEqual(ej_bici.icono, 'fa-solid fa-person-biking')

        ej_prensa = Ejercicio.objects.filter(nombre='Prensa de Piernas (Leg Press)').first()
        if ej_prensa:
            self.assertEqual(ej_prensa.icono, 'fa-solid fa-gears')

    def test_comando_poblar_catalogo(self):
        """Verifica la ejecución del comando de gestión poblar_catalogo"""
        from django.core.management import call_command
        import io
        out = io.StringIO()
        call_command('poblar_catalogo', stdout=out)
        self.assertIn("Catálogo oficial sincronizado con éxito", out.getvalue())

    def test_registrar_sesion_libre_tiempo(self):
        """Verifica que un usuario pueda registrar una sesión libre de correr 45 min sin ninguna rutina"""
        self.client.login(username='carlos', password='password123')
        ej_correr = Ejercicio.objects.create(
            nombre='Correr Libre',
            modalidad='TIEMPO',
            grupo_muscular='CAR',
            tipo='OUT'
        )

        data = {
            'duracion_minutos': '45',
            'notas': '5.5 km por el paseo marítimo',
            'fecha': '2026-09-20'
        }
        res = self.client.post(
            reverse('ejercicios:registrar_sesion_libre_ejercicio', args=[ej_correr.id]),
            data
        )
        self.assertRedirects(res, reverse('ejercicios:detalle_ejercicio', args=[ej_correr.id]))

        # Comprobar que se guardó el registro y la serie
        reg = RegistroEjercicio.objects.filter(usuario=self.user1, ejercicio=ej_correr).first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.notas, '5.5 km por el paseo marítimo')
        self.assertEqual(reg.series_detalle.count(), 1)
        self.assertEqual(reg.series_detalle.first().tiempo_segundos, 2700) # 45 min * 60s

    def test_registrar_sesion_libre_reps_peso(self):
        """Verifica que un usuario pueda registrar un ejercicio de fuerza suelto con series y peso"""
        self.client.login(username='carlos', password='password123')

        data = {
            'series_totales': '3',
            'repeticiones': '12',
            'peso_kg': '50',
            'notas': 'Sesión rápida en hotel'
        }
        res = self.client.post(
            reverse('ejercicios:registrar_sesion_libre_ejercicio', args=[self.ej_oficial.id]),
            data
        )
        self.assertRedirects(res, reverse('ejercicios:detalle_ejercicio', args=[self.ej_oficial.id]))

        reg = RegistroEjercicio.objects.filter(usuario=self.user1, ejercicio=self.ej_oficial).first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.series_detalle.count(), 3)
        self.assertEqual(reg.series_detalle.first().repeticiones, 12)
        self.assertEqual(float(reg.series_detalle.first().peso_kg), 50.0)

    def test_registrar_sesion_libre_via_json(self):
        """Verifica que el endpoint de registrar sesión libre responda JSON al enviar datos via API"""
        import json
        self.client.login(username='carlos', password='password123')

        payload = {
            'ejercicio_id': self.ej_oficial.id,
            'duracion_minutos': None,
            'series_totales': 2,
            'repeticiones': 8,
            'peso_kg': 65.0,
            'notas': 'Entrenamiento AJAX libre'
        }
        res = self.client.post(
            reverse('ejercicios:registrar_sesion_libre'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        json_resp = res.json()
        self.assertEqual(json_resp.get('status'), 'success')

    def test_serie_distancia_y_ritmo(self):
        """Verifica el cálculo de ritmo (min/km), velocidad (km/h) y representación de Serie con distancia"""
        reg = RegistroEjercicio.objects.create(
            usuario=self.user1,
            ejercicio=self.ej_oficial
        )
        # 5 km en 25 minutos (1500 segundos) -> 5:00 min/km, 12.0 km/h
        serie = Serie.objects.create(
            registro=reg,
            distancia_km=5.0,
            tiempo_segundos=1500
        )
        self.assertEqual(serie.ritmo_min_km, "5:00 min/km")
        self.assertEqual(serie.velocidad_kmh, 12.0)
        self.assertIn("5.0 km", str(serie))
        self.assertIn("25m", str(serie))
        self.assertIn("5:00 min/km", str(serie))

    def test_registrar_sesion_libre_con_distancia_km(self):
        """Verifica que registrar una actividad de correr almacene correctamente los km recorridos"""
        self.client.login(username='carlos', password='password123')
        ej_correr = Ejercicio.objects.create(
            nombre='Running Exterior',
            modalidad='TIEMPO',
            grupo_muscular='CAR',
            tipo='OUT'
        )

        data = {
            'duracion_minutos': '30',
            'distancia_km': '6.0',
            'notas': 'Entrenamiento de fondo',
            'fecha': '2026-09-21'
        }
        res = self.client.post(
            reverse('ejercicios:registrar_sesion_libre_ejercicio', args=[ej_correr.id]),
            data
        )
        self.assertRedirects(res, reverse('ejercicios:detalle_ejercicio', args=[ej_correr.id]))

        reg = RegistroEjercicio.objects.filter(usuario=self.user1, ejercicio=ej_correr).first()
        self.assertIsNotNone(reg)
        serie = reg.series_detalle.first()
        self.assertIsNotNone(serie)
        self.assertEqual(float(serie.distancia_km), 6.0)
        self.assertEqual(serie.tiempo_segundos, 1800)
        self.assertEqual(serie.ritmo_min_km, "5:00 min/km")
        self.assertEqual(serie.velocidad_kmh, 12.0)

    def test_registrar_sesion_libre_json_con_distancia(self):
        """Verifica que el API JSON registre correctamente distancia_km en carrera"""
        import json
        self.client.login(username='carlos', password='password123')
        ej_cinta = Ejercicio.objects.create(
            nombre='Correr en Cinta',
            modalidad='TIEMPO',
            grupo_muscular='CAR',
            tipo='CAR'
        )

        payload = {
            'ejercicio_id': ej_cinta.id,
            'duracion_minutos': 25,
            'distancia_km': 5.0,
            'notas': '5k en cinta a ritmo constante'
        }
        res = self.client.post(
            reverse('ejercicios:registrar_sesion_libre'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)

        reg = RegistroEjercicio.objects.filter(usuario=self.user1, ejercicio=ej_cinta).first()
        self.assertIsNotNone(reg)
        serie = reg.series_detalle.first()
        self.assertEqual(float(serie.distancia_km), 5.0)
        self.assertEqual(serie.ritmo_min_km, "5:00 min/km")
