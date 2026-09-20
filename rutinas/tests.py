import json
from django.test import TestCase, RequestFactory, Client
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from django.utils import timezone

from rutinas.models import Rutina, RutinaEjercicio
from ejercicios.models import Ejercicio, RegistroEjercicio, Serie
from rutinas.admin import RutinaAdmin, iniciar_rutina_hoy


class MockModelAdmin:
    def __init__(self):
        self.messages = []

    def message_user(self, request, message, level=None):
        self.messages.append((message, level))


class RutinaAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')

        # Ejercicio de Fuerza (Peso + Reps)
        self.ejercicio_peso = Ejercicio.objects.create(
            nombre='Press de Banca',
            definicion='Técnica pecho',
            modalidad='REPS_PESO',
            grupo_muscular='PEC'
        )

        # Ejercicio de Tiempo
        self.ejercicio_tiempo = Ejercicio.objects.create(
            nombre='Plancha Abdominal',
            definicion='Técnica core',
            modalidad='TIEMPO',
            grupo_muscular='COR'
        )

        # Rutina de prueba
        self.rutina = Rutina.objects.create(nombre='Torso y Core', usuario=self.user)
        RutinaEjercicio.objects.create(
            rutina=self.rutina,
            ejercicio=self.ejercicio_peso,
            orden=1,
            series_objetivo=3,
            repeticiones_objetivo=10
        )
        RutinaEjercicio.objects.create(
            rutina=self.rutina,
            ejercicio=self.ejercicio_tiempo,
            orden=2,
            series_objetivo=3,
            tiempo_objetivo_segundos=45
        )

    def test_iniciar_rutina_hoy_action_admin(self):
        """Verifica la acción del panel admin creando series de peso y de tiempo"""
        request = self.factory.get('/admin/')
        request.user = self.user
        modeladmin = MockModelAdmin()

        iniciar_rutina_hoy(modeladmin, request, Rutina.objects.filter(id=self.rutina.id))

        registros = RegistroEjercicio.objects.filter(usuario=self.user)
        self.assertEqual(registros.count(), 2)

        reg_peso = registros.get(ejercicio=self.ejercicio_peso)
        self.assertEqual(reg_peso.series_detalle.count(), 3)
        self.assertEqual(reg_peso.series_detalle.first().repeticiones, 10)

        reg_tiempo = registros.get(ejercicio=self.ejercicio_tiempo)
        self.assertEqual(reg_tiempo.series_detalle.count(), 3)
        self.assertEqual(reg_tiempo.series_detalle.first().tiempo_segundos, 45)

    def test_crear_rutina_view(self):
        """Verifica la creación interactiva de una rutina desde la web"""
        payload = {
            'nombre': 'Rutina Nueva Web',
            'descripcion': 'Probando creador de rutinas',
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 4,
                    'repeticiones_objetivo': 12,
                    'tiempo_objetivo_segundos': None
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:crear_rutina'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        nueva_rutina = Rutina.objects.filter(nombre='Rutina Nueva Web', usuario=self.user).first()
        self.assertIsNotNone(nueva_rutina)
        self.assertEqual(nueva_rutina.ejercicios.count(), 1)

    def test_crear_ejercicio_rapido_ajax(self):
        """Verifica la creación de un ejercicio personalizado por el usuario"""
        payload = {
            'nombre': 'Dominadas Neutras',
            'modalidad': 'REPS_PESO',
            'grupo_muscular': 'ESP',
            'tipo': 'CAL'
        }
        response = self.client.post(
            reverse('rutinas:crear_ejercicio_rapido_ajax'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['ejercicio']['nombre'], 'Dominadas Neutras')

        # Comprobar que pertenece al usuario
        ej = Ejercicio.objects.get(id=data['ejercicio']['id'])
        self.assertEqual(ej.creado_por, self.user)

    def test_guardar_serie_ajax_peso_y_tiempo(self):
        """Verifica el guardado en directo desde el 'Modo Gym' de series con peso y con tiempo"""
        # Guardar serie con peso y reps
        payload_peso = {
            'ejercicio_id': self.ejercicio_peso.id,
            'numero_serie': 1,
            'repeticiones': 10,
            'peso': 70.5,
            'tiempo_segundos': None,
            'rutina_nombre': 'Torso y Core'
        }
        res1 = self.client.post(
            reverse('rutinas:guardar_serie_ajax'),
            data=json.dumps(payload_peso),
            content_type='application/json'
        )
        self.assertEqual(res1.status_code, 200)

        # Guardar serie con tiempo
        payload_tiempo = {
            'ejercicio_id': self.ejercicio_tiempo.id,
            'numero_serie': 1,
            'repeticiones': None,
            'peso': None,
            'tiempo_segundos': 60,
            'rutina_nombre': 'Torso y Core'
        }
        res2 = self.client.post(
            reverse('rutinas:guardar_serie_ajax'),
            data=json.dumps(payload_tiempo),
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 200)

        # Verificar en base de datos
        serie_peso = Serie.objects.filter(registro__ejercicio=self.ejercicio_peso, numero_serie=1).first()
        self.assertIsNotNone(serie_peso)
        self.assertEqual(float(serie_peso.peso_kg), 70.5)

        serie_tiempo = Serie.objects.filter(registro__ejercicio=self.ejercicio_tiempo, numero_serie=1).first()
        self.assertIsNotNone(serie_tiempo)
        self.assertEqual(serie_tiempo.tiempo_segundos, 60)

    def test_dashboard_view(self):
        """Verifica que el dashboard carga sin errores y calcula métricas"""
        # Crear un registro con serie para simular actividad
        reg = RegistroEjercicio.objects.create(usuario=self.user, ejercicio=self.ejercicio_peso)
        Serie.objects.create(registro=reg, numero_serie=1, repeticiones=10, peso_kg=80.0)

        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tu Progreso')
        self.assertIn('volumen_total', response.context)
        self.assertEqual(response.context['volumen_total'], 800.0)

    def test_rutina_dias_semana_model_methods(self):
        """Verifica los métodos y propiedades de días de la semana en el modelo Rutina"""
        hoy_weekday = timezone.now().date().weekday()
        otro_dia = (hoy_weekday + 1) % 7

        # Rutina con días programados
        rutina_programada = Rutina.objects.create(
            nombre='Rutina Programada',
            usuario=self.user,
            dias_semana=f"{hoy_weekday},{otro_dia}"
        )
        self.assertEqual(rutina_programada.lista_dias_numeros, sorted([hoy_weekday, otro_dia]))
        self.assertEqual(len(rutina_programada.badges_dias), 2)
        self.assertTrue(rutina_programada.toca_hoy)

        # Rutina sin días asignados
        rutina_sin_dias = Rutina.objects.create(
            nombre='Rutina Sin Días',
            usuario=self.user,
            dias_semana=""
        )
        self.assertEqual(rutina_sin_dias.lista_dias_numeros, [])
        self.assertEqual(rutina_sin_dias.badges_dias, [])
        self.assertFalse(rutina_sin_dias.toca_hoy)

    def test_crear_rutina_con_dias_semana_view(self):
        """Verifica que al crear una rutina vía JSON se persistan los días seleccionados"""
        payload = {
            'nombre': 'Rutina Con Días',
            'descripcion': 'Martes y Jueves',
            'dias_semana': [1, 3],
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 3,
                    'repeticiones_objetivo': 10
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:crear_rutina'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        creada = Rutina.objects.filter(nombre='Rutina Con Días', usuario=self.user).first()
        self.assertIsNotNone(creada)
        self.assertEqual(creada.dias_semana, '1,3')
        self.assertEqual([b['corto'] for b in creada.badges_dias], ['Mar', 'Jue'])

    def test_editar_rutina_con_dias_semana_view(self):
        """Verifica que al editar una rutina se actualicen los días asignados"""
        payload = {
            'nombre': 'Torso y Core Actualizado',
            'descripcion': 'Nueva descripción',
            'dias_semana': [0, 4],  # Lunes y Viernes
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 4,
                    'repeticiones_objetivo': 8
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:editar_rutina', args=[self.rutina.id]),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.rutina.refresh_from_db()
        self.assertEqual(self.rutina.dias_semana, '0,4')
        self.assertEqual([b['corto'] for b in self.rutina.badges_dias], ['Lun', 'Vie'])

    def test_lista_rutinas_muestra_dias_y_toca_hoy(self):
        """Verifica que en la lista de rutinas se rendericen los badges de días y Toca Hoy"""
        hoy_weekday = timezone.now().date().weekday()
        self.rutina.dias_semana = str(hoy_weekday)
        self.rutina.save()

        response = self.client.get(reverse('rutinas:lista_rutinas'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '¡Toca hoy!')

    def test_crear_rutina_con_peso_objetivo(self):
        """Verifica que al crear una rutina se guarde el peso objetivo planificado"""
        payload = {
            'nombre': 'Rutina Con Cargas',
            'descripcion': 'Fuerza hipertrofia',
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 4,
                    'repeticiones_objetivo': 8,
                    'peso_objetivo': 65.5
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:crear_rutina'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        rutina_creada = Rutina.objects.filter(nombre='Rutina Con Cargas').first()
        self.assertIsNotNone(rutina_creada)
        re = rutina_creada.rutinaejercicio_set.first()
        self.assertEqual(float(re.peso_objetivo), 65.5)

    def test_editar_rutina_actualiza_peso_objetivo(self):
        """Verifica que al editar una rutina se persista la modificación del peso objetivo"""
        payload = {
            'nombre': 'Torso Actualizado',
            'descripcion': 'Incremento de cargas',
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 3,
                    'repeticiones_objetivo': 10,
                    'peso_objetivo': 70.0
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:editar_rutina', args=[self.rutina.id]),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.rutina.refresh_from_db()
        re = self.rutina.rutinaejercicio_set.filter(ejercicio=self.ejercicio_peso).first()
        self.assertEqual(float(re.peso_objetivo), 70.0)

    def test_iniciar_rutina_precarga_peso_objetivo_e_historial(self):
        """Verifica que el Modo Gym inicialice las series con el peso objetivo o datos históricos"""
        # Configuramos peso objetivo en la rutina
        re_peso = self.rutina.rutinaejercicio_set.get(ejercicio=self.ejercicio_peso)
        re_peso.peso_objetivo = 55.0
        re_peso.save()

        # Caso A: Sin historial previo -> Las series deben sugerir 55.0 kg
        res = self.client.get(reverse('rutinas:iniciar_rutina', args=[self.rutina.id]))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '55.0')

        # Caso B: Con historial previo de 60 kg -> Debe sugerir 60 kg y ofrecer peso anterior
        reg = RegistroEjercicio.objects.create(usuario=self.user, ejercicio=self.ejercicio_peso)
        Serie.objects.create(registro=reg, numero_serie=1, repeticiones=8, peso_kg=60.0)

        res_con_historial = self.client.get(reverse('rutinas:iniciar_rutina', args=[self.rutina.id]))
        self.assertEqual(res_con_historial.status_code, 200)
        self.assertContains(res_con_historial, '60.0')

