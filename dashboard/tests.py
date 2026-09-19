import datetime
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from ejercicios.models import Ejercicio, RegistroEjercicio, Serie
from rutinas.models import Rutina, RutinaEjercicio

User = get_user_model()


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='atletadash',
            email='dash@fitapp.com',
            password='Password123!',
            first_name='Carlos'
        )

    def test_dashboard_requiere_login(self):
        """Los usuarios anónimos son redirigidos a la pantalla de login"""
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertRedirects(response, f"/accounts/login/?next={reverse('dashboard:dashboard')}")

    def test_dashboard_usuario_nuevo_sin_datos(self):
        """Un usuario nuevo sin historial puede acceder al dashboard sin errores y con valores en cero"""
        self.client.login(username='atletadash', password='Password123!')
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Centro de Mando')
        self.assertEqual(response.context['dias_entrenados_mes'], 0)
        self.assertEqual(response.context['volumen_total'], 0)
        self.assertEqual(response.context['total_series'], 0)
        self.assertEqual(len(response.context['calendario_semanal']), 7)

    def test_dashboard_calculo_1rm_y_records_personales(self):
        """Verifica el cálculo de Récords Personales y la estimación de 1RM con la fórmula de Epley"""
        self.client.login(username='atletadash', password='Password123!')

        ej = Ejercicio.objects.create(
            nombre='Chest Press',
            tipo='MAQ',
            modalidad='REPS_PESO',
            grupo_muscular='PEC'
        )

        reg = RegistroEjercicio.objects.create(
            usuario=self.user,
            ejercicio=ej,
            etiqueta="Fuerza"
        )

        # Serie: 60 kg x 10 reps -> 1RM = 60 * (1 + 10/30) = 80.0 kg
        Serie.objects.create(
            registro=reg,
            numero_serie=1,
            peso_kg=60.0,
            repeticiones=10
        )

        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

        records = response.context['records_personales']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['ejercicio'].nombre, 'Chest Press')
        self.assertEqual(records[0]['max_peso'], 60.0)
        self.assertEqual(records[0]['max_peso_reps'], 10)
        self.assertEqual(records[0]['max_1rm'], 80.0)

    def test_dashboard_siguiente_rutina_recomendada(self):
        """Verifica que el dashboard recomiende la rutina del usuario"""
        self.client.login(username='atletadash', password='Password123!')

        rutina = Rutina.objects.create(
            usuario=self.user,
            nombre='Rutina Torso Test',
            descripcion='Rutina de prueba'
        )
        ej = Ejercicio.objects.create(nombre='Press Banca', grupo_muscular='PEC')
        RutinaEjercicio.objects.create(rutina=rutina, ejercicio=ej, orden=1)

        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['rutina_sugerida'])
        self.assertEqual(response.context['rutina_sugerida']['rutina'].nombre, 'Rutina Torso Test')
