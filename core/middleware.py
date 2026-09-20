from django.shortcuts import render
from django.urls import reverse
from .models import ConfiguracionSitio


class MaintenanceModeMiddleware:
    """
    Middleware que intercepta las peticiones cuando el modo mantenimiento está activado en ConfiguracionSitio.
    - Los usuarios con rol Staff o Superuser pueden navegar con normalidad (bypass).
    - Se permite el acceso a /admin/, rutas de login/logout y archivos estáticos/media.
    - Para los demás usuarios o visitantes anónimos, se devuelve una respuesta HTTP 503 con una plantilla personalizada.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        config = ConfiguracionSitio.get_config()

        if config.modo_mantenimiento:
            path = request.path_info

            # 1. Recursos estáticos, multimedia y PWA siempre permitidos
            if path.startswith('/static/') or path.startswith('/media/') or path in ['/manifest.json', '/sw.js', '/offline/']:
                return self.get_response(request)

            # 2. Panel administrativo siempre accesible para permitir desactivar el mantenimiento
            if path.startswith('/admin/'):
                return self.get_response(request)

            # 3. Rutas de autenticación (para permitir al staff iniciar sesión)
            rutas_auth_permitidas = [
                '/usuario/login/',
                '/usuario/logout/',
                '/accounts/login/',
                '/accounts/logout/',
            ]
            if path in rutas_auth_permitidas:
                return self.get_response(request)

            # 4. Si el usuario ya está autenticado y es Staff o Superuser, permitir el paso
            if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
                request.modo_mantenimiento_activo = True
                return self.get_response(request)

            # 5. Para el resto de usuarios o visitantes, devolver pantalla 503
            response = render(
                request,
                'core/503.html',
                {
                    'config_sitio': config,
                },
                status=503
            )
            response['Retry-After'] = '300'
            return response

        return self.get_response(request)
