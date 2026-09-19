from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
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

    def test_registro_solo_con_email_sin_username(self):
        """Verifica que el usuario se puede registrar solo con nombre, email y contraseña"""
        data = {
            'first_name': 'Carlos',
            'email': 'carlos@fitapp.com',
            'password1': 'MiClaveSecreta99!',
            'password2': 'MiClaveSecreta99!',
        }
        response = self.client.post(reverse('users:registro'), data)
        self.assertRedirects(response, reverse('users:perfil'))

        carlos = User.objects.filter(email='carlos@fitapp.com').first()
        self.assertIsNotNone(carlos)
        self.assertEqual(carlos.username, 'carlos@fitapp.com')
        self.assertEqual(carlos.first_name, 'Carlos')
        self.assertTrue(hasattr(carlos, 'profile'))

    def test_envio_correo_bienvenida_al_registrarse(self):
        """Verifica que se envía el correo HTML de bienvenida al registrarse"""
        mail.outbox = []
        data = {
            'first_name': 'Laura',
            'email': 'laura@fitapp.com',
            'password1': 'MiClaveSecreta99!',
            'password2': 'MiClaveSecreta99!',
        }
        response = self.client.post(reverse('users:registro'), data)
        self.assertRedirects(response, reverse('users:perfil'))

        # Comprobar que se envió 1 correo
        self.assertEqual(len(mail.outbox), 1)
        email_enviado = mail.outbox[0]
        self.assertEqual(email_enviado.to, ['laura@fitapp.com'])
        self.assertIn('Laura', email_enviado.subject)
        self.assertIn('Bienvenido a FitApp', email_enviado.subject)
        # Comprobar que contiene alternativa HTML
        self.assertTrue(any(content_type == 'text/html' for _, content_type in email_enviado.alternatives))

    def test_login_con_email(self):
        """Verifica que el usuario puede iniciar sesión usando su correo electrónico"""
        login_exitoso = self.client.login(username='atleta1@fitapp.com', password='Password123!')
        self.assertTrue(login_exitoso)

    def test_login_con_email_case_insensitive(self):
        """Verifica que el login por email es insensible a mayúsculas/minúsculas"""
        login_exitoso = self.client.login(username='ATLETA1@FITAPP.COM', password='Password123!')
        self.assertTrue(login_exitoso)

    def test_login_con_username_tradicional(self):
        """Verifica que el usuario también puede iniciar sesión con su username tradicional"""
        login_exitoso = self.client.login(username='atleta1', password='Password123!')
        self.assertTrue(login_exitoso)

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

    def test_password_reset_token_caducidad_e_invalidez(self):
        """Verifica que el token de recuperación expire según PASSWORD_RESET_TIMEOUT y tras cambio de clave"""
        from django.contrib.auth.tokens import default_token_generator
        from django.test.utils import override_settings

        # 1. Token válido recién emitido
        token = default_token_generator.make_token(self.user)
        self.assertTrue(default_token_generator.check_token(self.user, token))

        # 2. Token caducado cuando expira el tiempo límite
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            self.assertFalse(default_token_generator.check_token(self.user, token))

        # 3. Token queda invalidado inmediatamente en cuanto el usuario cambia su contraseña
        self.user.set_password('OtraClaveDistinta999!')
        self.user.save()
        self.assertFalse(default_token_generator.check_token(self.user, token))

    def test_log_creado_en_login_y_logout(self):
        """Verifica que el login y logout exitosos generen registros de auditoría"""
        from users.models import LogActividad

        # Login
        self.client.login(username='atleta1', password='Password123!')
        log_login = LogActividad.objects.filter(usuario=self.user, tipo='LOGIN').first()
        self.assertIsNotNone(log_login)
        self.assertEqual(log_login.nivel, 'INFO')

        # Logout
        self.client.logout()
        log_logout = LogActividad.objects.filter(usuario=self.user, tipo='LOGOUT').first()
        self.assertIsNotNone(log_logout)
        self.assertEqual(log_logout.nivel, 'INFO')

    def test_log_creado_en_login_fallido(self):
        """Verifica que un intento con contraseña errónea genere una advertencia WARNING"""
        from users.models import LogActividad

        self.client.post('/accounts/login/', {'username': 'atleta1', 'password': 'ClaveIncorrecta!'})
        log_fail = LogActividad.objects.filter(tipo='LOGIN_FAIL').first()
        self.assertIsNotNone(log_fail)
        self.assertEqual(log_fail.nivel, 'WARNING')
        self.assertIn('atleta1', log_fail.mensaje)

    def test_middleware_captura_error_500(self):
        """Verifica que el middleware capture excepciones no controladas y cree un registro ERROR_500"""
        from users.models import LogActividad
        from django.test import RequestFactory
        from users.middleware import AuditAndErrorLoggingMiddleware

        factory = RequestFactory()
        request = factory.get('/ruta-con-error/')
        request.user = self.user

        middleware = AuditAndErrorLoggingMiddleware(lambda r: None)
        try:
            raise ValueError("Fallo forzado de prueba técnica")
        except ValueError as e:
            middleware.process_exception(request, e)

        log_err = LogActividad.objects.filter(tipo='ERROR_500').first()
        self.assertIsNotNone(log_err)
        self.assertEqual(log_err.nivel, 'ERROR')
        self.assertEqual(log_err.usuario, self.user)
        self.assertIn("Fallo forzado de prueba técnica", log_err.mensaje)
        self.assertIsNotNone(log_err.traceback)
        self.assertIn("ValueError", log_err.traceback)


