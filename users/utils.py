from .models import LogActividad


def get_client_ip(request):
    """Obtiene la dirección IP real del cliente considerando proxies o cabeceras estándar"""
    if not request or not hasattr(request, 'META') or not isinstance(request.META, dict):
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = str(x_forwarded_for).split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def registrar_log(request=None, usuario=None, nivel='INFO', tipo='OTRO', mensaje='', traceback_str=None):
    """
    Función auxiliar universal para registrar cualquier evento o incidencia en la app.
    Puede ser llamada desde vistas, middleware, señales o comandos de manera 100% segura.
    """
    try:
        ruta = ''
        metodo = ''
        ip = None
        user_agent = ''

        if request:
            ruta = (getattr(request, 'path', '') or '')[:255]
            metodo = (getattr(request, 'method', '') or '')[:10]
            ip = get_client_ip(request)
            if hasattr(request, 'META') and isinstance(request.META, dict):
                user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:255]

            if not usuario and hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
                usuario = request.user

        return LogActividad.objects.create(
            usuario=usuario,
            nivel=nivel,
            tipo=tipo,
            ruta=ruta,
            metodo=metodo,
            ip=ip,
            user_agent=user_agent,
            mensaje=mensaje or '',
            traceback=traceback_str
        )
    except Exception as e:
        # En caso de cualquier excepción, nunca rompemos la petición del usuario
        print(f"Error al registrar log de actividad: {e}")
        return None
