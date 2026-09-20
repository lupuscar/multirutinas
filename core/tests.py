from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from core.models import ConfiguracionSitio
from users.models import LogActividad

User = get_user_model()


class ConfiguracionSitioModelTest(TestCase):
    def setUp(self):
        cache.clear()
        ConfiguracionSitio.objects.all().delete()

    def tearDown(self):
        cache.clear()

    def test_singleton_get_config_crea_instancia(self):
        """Verifica que get_config genera la instancia por defecto con id=1"""
        config = ConfiguracionSitio.get_config()
        self.assertIsNotNone(config)
        self.assertEqual(config.id, 1)
        self.assertEqual(config.nombre_sitio, "FitApp")
        self.assertTrue(config.registro_abierto)
        self.assertFalse(config.modo_mantenimiento)

    def test_singleton_solo_permite_un_registro(self):
        """Verifica que al guardar cualquier instancia se fuerza pk=1"""
        config1 = ConfiguracionSitio.get_config()
        config1.nombre_sitio = "Gimnasio Master"
        config1.save()

        segunda = ConfiguracionSitio(nombre_sitio="Otro Gimnasio")
        segunda.save()

        self.assertEqual(ConfiguracionSitio.objects.count(), 1)
        self.assertEqual(ConfiguracionSitio.get_config().nombre_sitio, "Otro Gimnasio")

    def test_delete_protegido(self):
        """Verifica que delete no elimine la configuración"""
        config = ConfiguracionSitio.get_config()
        config.delete()
        self.assertEqual(ConfiguracionSitio.objects.count(), 1)


class MaintenanceModeMiddlewareTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.usuario_normal = User.objects.create_user(
            username='deportista',
            email='deportista@test.com',
            password='Password123!',
            is_active=True
        )
        self.usuario_staff = User.objects.create_user(
            username='admin_staff',
            email='staff@test.com',
            password='Password123!',
            is_staff=True,
            is_active=True
        )
        self.config = ConfiguracionSitio.get_config()
        self.config.modo_mantenimiento = False
        self.config.save()

    def tearDown(self):
        cache.clear()

    def test_sitio_accesible_cuando_mantenimiento_inactivo(self):
        """Verifica que las vistas respondan normalmente cuando mantenimiento está en False"""
        self.client.login(username='deportista', password='Password123!')
        res = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(res.status_code, 200)

    def test_usuario_anonimo_recibe_503_en_mantenimiento(self):
        """Verifica que un visitante anónimo reciba HTTP 503 en modo mantenimiento"""
        self.config.modo_mantenimiento = True
        self.config.save()

        res = self.client.get(reverse('users:perfil'))
        self.assertEqual(res.status_code, 503)
        self.assertIn('Ajustando las máquinas', res.content.decode('utf-8'))
        self.assertEqual(res['Retry-After'], '300')

    def test_usuario_normal_recibe_503_en_mantenimiento(self):
        """Verifica que un deportista autenticado no-staff reciba HTTP 503"""
        self.client.login(username='deportista', password='Password123!')
        self.config.modo_mantenimiento = True
        self.config.save()

        res = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(res.status_code, 503)

    def test_staff_tiene_bypass_en_mantenimiento(self):
        """Verifica que el personal de staff pueda navegar sin bloqueo 503"""
        self.client.login(username='admin_staff', password='Password123!')
        self.config.modo_mantenimiento = True
        self.config.save()

        res = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'MODO MANTENIMIENTO ACTIVO')

    def test_rutas_login_y_admin_siempre_accesibles(self):
        """Verifica que /usuario/login/ y /admin/ no queden bloqueadas en mantenimiento"""
        self.config.modo_mantenimiento = True
        self.config.save()

        res_login = self.client.get(reverse('login'))
        self.assertEqual(res_login.status_code, 200)

        res_admin = self.client.get('/admin/login/')
        self.assertEqual(res_admin.status_code, 200)


class RegistroPublicoToggleTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.config = ConfiguracionSitio.get_config()

    def tearDown(self):
        cache.clear()

    def test_registro_bloqueado_cuando_desactivado(self):
        """Verifica que cuando registro_abierto=False no se permita crear cuentas"""
        self.config.registro_abierto = False
        self.config.save()

        # GET debe mostrar aviso de cerrado
        res_get = self.client.get(reverse('users:registro'))
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, "Acceso Temporalmente Cerrado")

        # POST directo debe ser rechazado
        data = {
            'username': 'nuevointento',
            'email': 'nuevo@test.com',
            'password1': 'MiClaveSegura123!',
            'password2': 'MiClaveSegura123!',
        }
        res_post = self.client.post(reverse('users:registro'), data)
        self.assertRedirects(res_post, reverse('login'))
        self.assertFalse(User.objects.filter(username='nuevointento').exists())

    def test_login_muestra_estado_de_registro(self):
        """Verifica que el enlace de registro desaparezca en el login si está cerrado"""
        self.config.registro_abierto = False
        self.config.save()

        res = self.client.get(reverse('login'))
        self.assertContains(res, "cerrado temporalmente")
        self.assertNotContains(res, "Regístrate gratis aquí")


class PermisoCrearEjerciciosToggleTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.usuario = User.objects.create_user(
            username='atleta',
            email='atleta@test.com',
            password='Password123!',
            is_active=True
        )
        self.staff = User.objects.create_user(
            username='entrenador',
            email='entrenador@test.com',
            password='Password123!',
            is_staff=True,
            is_active=True
        )
        self.config = ConfiguracionSitio.get_config()

    def tearDown(self):
        cache.clear()

    def test_usuario_normal_bloqueado_para_crear_ejercicios_si_esta_desactivado(self):
        """Verifica que el usuario no pueda crear ejercicios si está desactivado globalmente"""
        self.config.usuarios_pueden_crear_ejercicios = False
        self.config.save()

        self.client.login(username='atleta', password='Password123!')
        res = self.client.get(reverse('ejercicios:crear_ejercicio'))
        self.assertRedirects(res, reverse('ejercicios:ejercicios'))

    def test_staff_si_puede_crear_ejercicios_aunque_este_desactivado(self):
        """Verifica que el staff conserve el derecho de crear ejercicios"""
        self.config.usuarios_pueden_crear_ejercicios = False
        self.config.save()

        self.client.login(username='entrenador', password='Password123!')
        res = self.client.get(reverse('ejercicios:crear_ejercicio'))
        self.assertEqual(res.status_code, 200)


class PanelConfiguracionWebTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.usuario_normal = User.objects.create_user(
            username='normalito',
            email='normal@test.com',
            password='Password123!',
            is_active=True
        )
        self.staff = User.objects.create_user(
            username='adminweb',
            email='adminweb@test.com',
            password='Password123!',
            is_staff=True,
            is_active=True
        )

    def tearDown(self):
        cache.clear()

    def test_solo_staff_accede_al_panel_web(self):
        """Verifica que usuarios normales no puedan acceder al panel de configuración"""
        self.client.login(username='normalito', password='Password123!')
        res = self.client.get(reverse('core:configuracion_sistema'))
        # user_passes_test redirige a login
        self.assertEqual(res.status_code, 302)

        self.client.login(username='adminweb', password='Password123!')
        res_staff = self.client.get(reverse('core:configuracion_sistema'))
        self.assertEqual(res_staff.status_code, 200)
        self.assertContains(res_staff, "Configuración del Sistema")

    def test_staff_actualiza_configuracion_desde_panel_web(self):
        """Verifica que guardar el formulario desde el panel web actualice el singleton"""
        self.client.login(username='adminweb', password='Password123!')
        data = {
            'nombre_sitio': 'Iron Gym Pro',
            'email_soporte': 'admin@irongym.com',
            'modo_mantenimiento': True,
            'mensaje_mantenimiento': 'Actualizando pesas...',
            'tiempo_estimado_reapertura': '20 mins',
            'registro_abierto': False,
            'mensaje_registro_cerrado': 'Solo socios presenciales',
            'banner_activo': True,
            'banner_texto': '¡Oferta de verano!',
            'banner_tipo': 'SUCCESS',
            'usuarios_pueden_crear_ejercicios': True,
        }
        res = self.client.post(reverse('core:configuracion_sistema'), data)
        self.assertRedirects(res, reverse('core:configuracion_sistema'))

        config = ConfiguracionSitio.get_config()
        self.assertEqual(config.nombre_sitio, 'Iron Gym Pro')
        self.assertTrue(config.modo_mantenimiento)
        self.assertFalse(config.registro_abierto)
        self.assertEqual(config.banner_texto, '¡Oferta de verano!')

    def test_accion_mantenimiento_purgar_logs(self):
        """Verifica la acción de purga de logs antiguos"""
        self.client.login(username='adminweb', password='Password123!')
        
        # Crear log antiguo y log reciente
        log_antiguo = LogActividad.objects.create(
            nivel='INFO',
            tipo='OTRO',
            mensaje='Evento muy viejo'
        )
        LogActividad.objects.filter(id=log_antiguo.id).update(
            creado_en=timezone.now() - timedelta(days=90)
        )

        LogActividad.objects.create(
            nivel='INFO',
            tipo='OTRO',
            mensaje='Evento de ayer'
        )

        res = self.client.post(reverse('core:accion_mantenimiento', args=['purgar_logs']))
        self.assertRedirects(res, reverse('core:configuracion_sistema'))

        self.assertFalse(LogActividad.objects.filter(mensaje='Evento muy viejo').exists())
        self.assertTrue(LogActividad.objects.filter(mensaje='Evento de ayer').exists())


class PWATests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_manifest_disponible_y_valido(self):
        """Verifica que el manifest.json se sirve con application/manifest+json y contiene configuración válida"""
        response = self.client.get('/manifest.json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/manifest+json', response['Content-Type'])
        data = response.json()
        self.assertEqual(data['short_name'], 'OPTIFIT')
        self.assertEqual(data['display'], 'standalone')
        self.assertTrue(len(data['icons']) >= 3)

    def test_service_worker_disponible_y_valido(self):
        """Verifica que sw.js se sirve con application/javascript y cabecera de alcance root"""
        response = self.client.get('/sw.js')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/javascript', response['Content-Type'])
        self.assertEqual(response.get('Service-Worker-Allowed'), '/')
        self.assertIn('CACHE_NAME', response.content.decode('utf-8'))

    def test_pagina_offline_disponible(self):
        """Verifica que la pantalla offline responde con HTTP 200"""
        response = self.client.get('/offline/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sin conexión a Internet', response.content.decode('utf-8'))

