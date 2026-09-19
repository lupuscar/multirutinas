from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from users.models import Profile

User = get_user_model()


class UsersAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='atleta1',
            email='atleta1@fitapp.com',
            password='Password123!',
            first_name='Atleta'
        )

    def test_perfil_creado_automaticamente_por_senal(self):
        """Verifica que al crearse un usuario, su Profile se genera de forma automática"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsNotNone(self.user.profile)
        self.assertEqual(self.user.profile.tipo_suscripcion, 'FREE')

    def test_registro_publico_usuario(self):
        """Verifica el formulario y flujo de registro público de nuevos usuarios"""
        data = {
            'username': 'nuevousuario',
            'first_name': 'Nuevo',
            'email': 'nuevo@fitapp.com',
            'password1': 'MiClaveSecreta99!',
            'password2': 'MiClaveSecreta99!',
        }
        response = self.client.post(reverse('users:registro'), data)
        self.assertRedirects(response, reverse('users:perfil'))

        nuevo_user = User.objects.filter(username='nuevousuario').first()
        self.assertIsNotNone(nuevo_user)
        self.assertTrue(hasattr(nuevo_user, 'profile'))
        self.assertEqual(nuevo_user.email, 'nuevo@fitapp.com')

    def test_registro_email_duplicado(self):
        """No permite registrarse con un email ya existente"""
        data = {
            'username': 'otrouser',
            'first_name': 'Otro',
            'email': 'atleta1@fitapp.com', # Email ya de atleta1
            'password1': 'MiClaveSecreta99!',
            'password2': 'MiClaveSecreta99!',
        }
        response = self.client.post(reverse('users:registro'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'Ya existe una cuenta con este correo electrónico.')

    def test_actualizar_perfil(self):
        """Verifica la actualización de datos personales y físicos en el perfil"""
        self.client.login(username='atleta1', password='Password123!')
        data = {
            'action': 'actualizar_perfil',
            'first_name': 'Atleta Actualizado',
            'last_name': 'Pérez',
            'email': 'atleta1@fitapp.com',
            'biografia': 'Entrenando fuerte cada día',
            'peso': 78.5,
            'altura': 180,
            'nivel': 'IN',
            'objetivo': 'HIP',
            'dias_objetivo_semana': 5
        }
        response = self.client.post(reverse('users:perfil'), data)
        self.assertRedirects(response, reverse('users:perfil'))

        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Atleta Actualizado')
        self.assertEqual(float(self.user.profile.peso), 78.5)
        self.assertEqual(self.user.profile.altura, 180)
        # IMC para 78.5kg y 1.80m = 78.5 / (1.8*1.8) = 24.23 (Normal)
        self.assertEqual(self.user.profile.imc, 24.23)
        self.assertEqual(self.user.profile.categoria_imc['nombre'], 'Peso normal / Saludable')

    def test_cambiar_password_en_perfil(self):
        """Verifica el cambio seguro de contraseña dentro de la pestaña del perfil"""
        self.client.login(username='atleta1', password='Password123!')
        data = {
            'action': 'cambiar_password',
            'old_password': 'Password123!',
            'new_password1': 'NuevaClaveSuperSegura456!',
            'new_password2': 'NuevaClaveSuperSegura456!',
        }
        response = self.client.post(reverse('users:perfil'), data)
        self.assertRedirects(response, reverse('users:perfil'))

        # Comprobar que la nueva contraseña funciona
        self.client.logout()
        login_exitoso = self.client.login(username='atleta1', password='NuevaClaveSuperSegura456!')
        self.assertTrue(login_exitoso)

    def test_pantallas_password_reset_disponibles(self):
        """Verifica que las plantillas de recuperación de contraseña cargan correctamente"""
        # Formulario solicitud
        res_form = self.client.get(reverse('password_reset'))
        self.assertEqual(res_form.status_code, 200)
        self.assertContains(res_form, '¿Olvidaste tu contraseña?')

        # Envío solicitud
        res_post = self.client.post(reverse('password_reset'), {'email': 'atleta1@fitapp.com'})
        self.assertRedirects(res_post, reverse('password_reset_done'))

        # Pantalla de confirmación de envío
        res_done = self.client.get(reverse('password_reset_done'))
        self.assertEqual(res_done.status_code, 200)
        self.assertContains(res_done, '¡Revisa tu bandeja de entrada!')
