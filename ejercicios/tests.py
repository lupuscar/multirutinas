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

