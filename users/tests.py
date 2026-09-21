from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from users.models import Profile, LogActividad
from users.tokens import email_verification_token
from users.utils import resetear_datos_usuario
from rutinas.models import Rutina, RutinaEjercicio
from ejercicios.models import RegistroEjercicio, Serie, Ejercicio

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

    def test_admin_changelist_vista_usuarios(self):
        """Verifica que la lista de usuarios en Django Admin renderice los badges sin errores"""
        User.objects.create_superuser(
            username='superadmin',
            email='superadmin@fitapp.com',
            password='AdminPassword123!'
        )
        self.client.login(username='superadmin', password='AdminPassword123!')
        response = self.client.get('/admin/auth/user/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estado de Cuenta')

    def test_cambiar_foto_perfil_exitoso(self):
        """Verifica la actualización de la foto de perfil desde el modal interactivo"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='atleta1', password='Password123!')
        
        fake_img = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        foto = SimpleUploadedFile("avatar.gif", fake_img, content_type="image/gif")
        
        res = self.client.post(reverse('users:perfil'), {
            'action': 'cambiar_foto',
            'foto_perfil': foto,
        })
        self.assertRedirects(res, reverse('users:perfil'))
        self.user.profile.refresh_from_db()
        self.assertTrue(bool(self.user.profile.foto_perfil))

    def test_eliminar_foto_perfil(self):
        """Verifica que un usuario pueda eliminar su foto de perfil actual"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='atleta1', password='Password123!')
        
        fake_img = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        self.user.profile.foto_perfil = SimpleUploadedFile("avatar.gif", fake_img, content_type="image/gif")
        self.user.profile.save()
        self.assertTrue(bool(self.user.profile.foto_perfil))

        res = self.client.post(reverse('users:perfil'), {
            'action': 'cambiar_foto',
            'eliminar_foto': '1'
        })
        self.assertRedirects(res, reverse('users:perfil'))
        self.user.profile.refresh_from_db()
        self.assertFalse(bool(self.user.profile.foto_perfil))

    def test_genero_icono_y_propiedades(self):
        """Verifica que las opciones de género y sus iconos correspondientes se calculan adecuadamente"""
        perfil = self.user.profile
        
        perfil.genero = 'H'
        perfil.save()
        self.assertEqual(perfil.icono_genero, 'fa-solid fa-mars')
        self.assertEqual(perfil.get_genero_display(), 'Hombre')

        perfil.genero = 'M'
        perfil.save()
        self.assertEqual(perfil.icono_genero, 'fa-solid fa-venus')
        self.assertEqual(perfil.get_genero_display(), 'Mujer')

        perfil.genero = 'O'
        perfil.save()
        self.assertEqual(perfil.icono_genero, 'fa-solid fa-genderless')
        self.assertEqual(perfil.get_genero_display(), 'Otro / Prefiero no decir')

    def test_genero_actualizar_desde_formulario_y_renderizado(self):
        """Verifica la actualización del género vía POST en perfil y su presencia visual en el template"""
        self.client.login(username='atleta1', password='Password123!')
        
        response = self.client.post(reverse('users:perfil'), {
            'action': 'actualizar_perfil',
            'first_name': 'Atleta',
            'last_name': 'Fit',
            'email': 'atleta1@fitapp.com',
            'genero': 'M',
            'peso': '62.5',
            'altura': '168',
            'nivel': 'IN',
            'objetivo': 'DEF',
            'dias_objetivo_semana': 4,
        })
        self.assertRedirects(response, reverse('users:perfil'))
        
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.genero, 'M')

        # Comprobar renderizado en vista GET
        res_get = self.client.get(reverse('users:perfil'))
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, 'Mujer')
        self.assertContains(res_get, 'fa-person-dress')
        self.assertContains(res_get, 'fa-venus')

    def test_edad_calculada_en_profile(self):
        """Verifica que la propiedad edad calcule los años cumplidos de forma precisa"""
        from datetime import date, timedelta
        from django.utils import timezone
        hoy = timezone.now().date()
        perfil = self.user.profile

        # Sin fecha de nacimiento
        perfil.fecha_nacimiento = None
        perfil.save()
        self.assertIsNone(perfil.edad)

        # Exactamente 25 años
        perfil.fecha_nacimiento = date(hoy.year - 25, hoy.month, hoy.day)
        perfil.save()
        self.assertEqual(perfil.edad, 25)

        # Aún no ha cumplido años este año
        manana = hoy + timedelta(days=1)
        perfil.fecha_nacimiento = date(manana.year - 30, manana.month, manana.day)
        perfil.save()
        self.assertEqual(perfil.edad, 29)


class UsersResetDatosTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='atleta_demo',
            email='demo@fitapp.com',
            password='Password123!',
            first_name='Demo'
        )
        self.user.profile.peso = 75.5
        self.user.profile.altura = 180
        self.user.profile.genero = 'H'
        self.user.profile.nivel = 'IN'
        self.user.profile.objetivo = 'FUE'
        self.user.profile.email_verificado = True
        self.user.profile.save()

        # Ejercicio estándar (no creado por el usuario)
        self.ej_estandar = Ejercicio.objects.create(
            nombre='Press de Banca Oficial',
            grupo_muscular='PEC',
            tipo='LIB',
            modalidad='REPS_PESO'
        )

        # Ejercicio personalizado creado por el usuario
        self.ej_personalizado = Ejercicio.objects.create(
            nombre='Mi Ejercicio Casero',
            grupo_muscular='BRA',
            tipo='LIB',
            modalidad='REPS_PESO',
            creado_por=self.user
        )

        # Rutina del usuario
        self.rutina = Rutina.objects.create(
            usuario=self.user,
            nombre='Rutina Pecho y Tríceps',
            dias_semana='0,3'
        )
        RutinaEjercicio.objects.create(
            rutina=self.rutina,
            ejercicio=self.ej_estandar,
            series_objetivo=4,
            repeticiones_objetivo=10,
            peso_objetivo=80
        )

        # Sesión y serie del usuario
        self.registro = RegistroEjercicio.objects.create(
            usuario=self.user,
            ejercicio=self.ej_estandar,
            etiqueta='Fuerza'
        )
        self.serie = Serie.objects.create(
            registro=self.registro,
            numero_serie=1,
            repeticiones=10,
            peso_kg=80
        )

    def test_resetear_datos_usuario_elimina_rutinas_y_registros_conservando_perfil(self):
        """La función utilitaria elimina todo el historial deportivo y conserva el perfil."""
        res = resetear_datos_usuario(self.user)
        self.assertEqual(res['rutinas'], 1)
        self.assertEqual(res['registros'], 1)
        self.assertEqual(res['series'], 1)
        self.assertEqual(res['ejercicios_personalizados'], 1)

        # Verificar que el usuario y perfil siguen existiendo intactos
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.username, 'atleta_demo')
        self.assertEqual(float(self.user.profile.peso), 75.5)
        self.assertEqual(self.user.profile.altura, 180)
        self.assertEqual(self.user.profile.objetivo, 'FUE')

        # Verificar que rutinas, registros y ejercicios personalizados se borraron
        self.assertEqual(Rutina.objects.filter(usuario=self.user).count(), 0)
        self.assertEqual(RegistroEjercicio.objects.filter(usuario=self.user).count(), 0)
        self.assertEqual(Serie.objects.filter(registro__usuario=self.user).count(), 0)
        self.assertEqual(Ejercicio.objects.filter(creado_por=self.user).count(), 0)

        # Verificar que el ejercicio estándar oficial sigue existiendo
        self.assertTrue(Ejercicio.objects.filter(pk=self.ej_estandar.pk).exists())

        # Verificar log de auditoría RESET_DATOS
        log = LogActividad.objects.filter(usuario=self.user, tipo='RESET_DATOS').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.nivel, 'WARNING')
        self.assertIn('restableció', log.mensaje)

    def test_perfil_view_resetear_datos_requiere_confirmacion_exacta(self):
        """Si no se escribe RESETEAR, la vista no elimina datos y muestra error."""
        self.client.login(username='atleta_demo', password='Password123!')
        response = self.client.post(reverse('users:perfil'), {
            'action': 'resetear_datos',
            'confirmacion': 'NO_ES_RESETEAR'
        })
        self.assertRedirects(response, f"{reverse('users:perfil')}?tab=seguridad")

        # Nada se debió eliminar
        self.assertEqual(Rutina.objects.filter(usuario=self.user).count(), 1)
        self.assertEqual(RegistroEjercicio.objects.filter(usuario=self.user).count(), 1)

    def test_perfil_view_resetear_datos_exitoso(self):
        """Al confirmar con RESETEAR, la vista ejecuta el reseteo y muestra mensaje de éxito."""
        self.client.login(username='atleta_demo', password='Password123!')
        response = self.client.post(reverse('users:perfil'), {
            'action': 'resetear_datos',
            'confirmacion': 'RESETEAR'
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Datos eliminados
        self.assertEqual(Rutina.objects.filter(usuario=self.user).count(), 0)
        self.assertEqual(RegistroEjercicio.objects.filter(usuario=self.user).count(), 0)
        self.assertEqual(Ejercicio.objects.filter(creado_por=self.user).count(), 0)

        # Perfil intacto
        self.user.profile.refresh_from_db()
        self.assertEqual(float(self.user.profile.peso), 75.5)

    def test_admin_accion_resetear_datos_usuario(self):
        """Un superusuario puede restablecer los datos de usuarios seleccionados desde el admin."""
        User.objects.create_superuser(
            username='admin_fit',
            email='admin@fitapp.com',
            password='Password123!'
        )
        self.client.login(username='admin_fit', password='Password123!')

        # 1. Petición inicial muestra pantalla de confirmación
        url_changelist = reverse('admin:auth_user_changelist')
        res_confirm = self.client.post(url_changelist, {
            'action': 'resetear_datos_usuario_accion',
            '_selected_action': [self.user.pk]
        })
        self.assertEqual(res_confirm.status_code, 200)
        self.assertContains(res_confirm, '¿Confirmar restablecimiento de datos a cero?')
        self.assertContains(res_confirm, self.user.username)

        # 2. Petición con apply=1 confirma y borra
        res_apply = self.client.post(url_changelist, {
            'action': 'resetear_datos_usuario_accion',
            '_selected_action': [self.user.pk],
            'apply': '1'
        }, follow=True)
        self.assertEqual(res_apply.status_code, 200)

        self.assertEqual(Rutina.objects.filter(usuario=self.user).count(), 0)
        self.assertEqual(RegistroEjercicio.objects.filter(usuario=self.user).count(), 0)

    def test_admin_vista_individual_resetear_datos(self):
        """Un superusuario puede restablecer los datos desde la vista individual en admin."""
        User.objects.create_superuser(
            username='admin_fit2',
            email='admin2@fitapp.com',
            password='Password123!'
        )
        self.client.login(username='admin_fit2', password='Password123!')

        url_individual = reverse('admin:auth_user_resetear_datos', args=[self.user.pk])
        res_get = self.client.get(url_individual)
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, self.user.username)

        res_post = self.client.post(url_individual, {'apply': '1'})
        self.assertRedirects(res_post, reverse('admin:auth_user_change', args=[self.user.pk]))
        self.assertEqual(Rutina.objects.filter(usuario=self.user).count(), 0)

    def test_admin_accion_resetear_datos_profile(self):
        """Un superusuario puede restablecer datos seleccionando perfiles en el admin."""
        User.objects.create_superuser(
            username='admin_fit3',
            email='admin3@fitapp.com',
            password='Password123!'
        )
        self.client.login(username='admin_fit3', password='Password123!')

        url_profile_list = reverse('admin:users_profile_changelist')
        res_confirm = self.client.post(url_profile_list, {
            'action': 'resetear_datos_profile_accion',
            '_selected_action': [self.user.profile.pk]
        })
        self.assertEqual(res_confirm.status_code, 200)
        self.assertContains(res_confirm, self.user.username)

        res_apply = self.client.post(url_profile_list, {
            'action': 'resetear_datos_profile_accion',
            '_selected_action': [self.user.profile.pk],
            'apply': '1'
        }, follow=True)
        self.assertEqual(res_apply.status_code, 200)
        self.assertEqual(Rutina.objects.filter(usuario=self.user).count(), 0)



