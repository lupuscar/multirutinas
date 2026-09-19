import json
from django.test import TestCase, RequestFactory, Client
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.urls import reverse

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
