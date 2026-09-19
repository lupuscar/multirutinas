from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from users.models import Profile
from users.tokens import email_verification_token

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
        self.user.profile.email_verificado = True
        self.user.profile.save()

    def test_perfil_creado_automaticamente_por_senal(self):
        """Verifica que al crearse un usuario, su Profile se genera de forma automática"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsNotNone(self.user.profile)
        self.assertEqual(self.user.profile.tipo_suscripcion, 'FREE')

    def test_registro_publico_crea_usuario_inactivo_y_envia_activacion(self):
        """Verifica que al registrarse el usuario queda inactivo y se envía el correo con token de activación"""
        mail.outbox = []
        data = {
            'username': 'nuevousuario',
            'first_name': 'Nuevo',
            'email': 'nuevo@fitapp.com',
            'password1': 'MiClaveSecreta99!',
            'password2': 'MiClaveSecreta99!',
        }
        response = self.client.post(reverse('users:registro'), data)
        self.assertRedirects(response, reverse('users:registro_pendiente'))

        nuevo_user = User.objects.filter(email='nuevo@fitapp.com').first()
        self.assertIsNotNone(nuevo_user)
        self.assertFalse(nuevo_user.is_active)
        self.assertFalse(nuevo_user.profile.email_verificado)

        # Comprobar que se envió 1 correo de activación
        self.assertEqual(len(mail.outbox), 1)
        email_activacion = mail.outbox[0]
        self.assertEqual(email_activacion.to, ['nuevo@fitapp.com'])
        self.assertIn('Activa tu cuenta', email_activacion.subject)
        self.assertIn('activar/', email_activacion.body)

    def test_activacion_exitosa_con_token_valido(self):
        """Al hacer clic en el enlace de activación válido, la cuenta se activa y se envía bienvenida"""
        inactivo = User.objects.create_user(
            username='inactivo@fitapp.com',
            email='inactivo@fitapp.com',
            password='Password123!',
            first_name='Pendiente',
            is_active=False
        )
        inactivo.profile.email_verificado = False
        inactivo.profile.save()

        mail.outbox = []
        uid = urlsafe_base64_encode(force_bytes(inactivo.pk))
        token = email_verification_token.make_token(inactivo)

        url = reverse('users:activar_cuenta', kwargs={'uidb64': uid, 'token': token})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('users:perfil'))

        inactivo.refresh_from_db()
        inactivo.profile.refresh_from_db()
        self.assertTrue(inactivo.is_active)
        self.assertTrue(inactivo.profile.email_verificado)

        # Se envía el correo de bienvenida al activarse
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Bienvenido a FitApp', mail.outbox[0].subject)

    def test_activacion_falla_con_token_manipulado(self):
        """Un token no válido o manipulado no activa la cuenta"""
        inactivo = User.objects.create_user(
            username='hacker@fitapp.com',
            email='hacker@fitapp.com',
            password='Password123!',
            first_name='Hacker',
            is_active=False
        )
        inactivo.profile.email_verificado = False
        inactivo.profile.save()

        uid = urlsafe_base64_encode(force_bytes(inactivo.pk))
        url = reverse('users:activar_cuenta', kwargs={'uidb64': uid, 'token': 'token-invalido-123'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/activacion_invalida.html')

        inactivo.refresh_from_db()
        self.assertFalse(inactivo.is_active)
        self.assertFalse(inactivo.profile.email_verificado)

    def test_usuario_inactivo_no_puede_iniciar_sesion(self):
        """Un usuario con is_active=False es rechazado por el sistema de autenticación"""
        User.objects.create_user(
            username='bloqueado@fitapp.com',
            email='bloqueado@fitapp.com',
            password='Password123!',
            is_active=False
        )
        login_exitoso = self.client.login(username='bloqueado@fitapp.com', password='Password123!')
        self.assertFalse(login_exitoso)

    def test_reenviar_activacion(self):
        """Permite reenviar un nuevo enlace de activación a usuarios pendientes"""
        inactivo = User.objects.create_user(
            username='olvidadizo@fitapp.com',
            email='olvidadizo@fitapp.com',
            password='Password123!',
            is_active=False
        )
        inactivo.profile.email_verificado = False
        inactivo.profile.save()

        mail.outbox = []
        response = self.client.post(reverse('users:reenviar_activacion'), {'email': 'olvidadizo@fitapp.com'})
        self.assertRedirects(response, reverse('users:registro_pendiente'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['olvidadizo@fitapp.com'])

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


