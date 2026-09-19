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


def enviar_correo_bienvenida(user, request=None):
    """
    Envía un correo electrónico de bienvenida en formato HTML y texto plano
    al nuevo deportista registrado.
    Es tolerante a fallos: no bloquea ni rompe el registro si el servidor SMTP falla.
    """
    if not user or not user.email:
        return False

    try:
        protocol = 'https' if (request and request.is_secure()) else 'http'
        if request:
            domain = request.get_host()
        else:
            domain = '127.0.0.1:8000'

        nombre = user.first_name or user.username or 'Atleta'
        from django.urls import reverse
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings

        login_url = f"{protocol}://{domain}{reverse('login')}"
        perfil_url = f"{protocol}://{domain}{reverse('users:perfil')}"

        context = {
            'user': user,
            'nombre': nombre,
            'domain': domain,
            'protocol': protocol,
            'login_url': login_url,
            'perfil_url': perfil_url,
        }

        asunto = f"¡Bienvenido a FitApp, {nombre}! 🏋️‍♂️ Tu entrenamiento empieza hoy"
        mensaje_texto = render_to_string('emails/bienvenida.txt', context)
        mensaje_html = render_to_string('emails/bienvenida.html', context)

        email = EmailMultiAlternatives(
            subject=asunto,
            body=mensaje_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(mensaje_html, "text/html")
        email.send(fail_silently=False)

        registrar_log(
            request=request,
            usuario=user,
            nivel='INFO',
            tipo='REGISTRO',
            mensaje=f"Correo de bienvenida enviado exitosamente a {user.email}"
        )
        return True
    except Exception as e:
        registrar_log(
            request=request,
            usuario=user,
            nivel='WARNING',
            tipo='OTRO',
            mensaje=f"Fallo al enviar correo de bienvenida a {user.email}: {str(e)}"
        )
        return False


def enviar_correo_activacion(user, request=None):
    """
    Genera un token seguro y envía un correo electrónico al usuario para
    que active su cuenta antes de poder iniciar sesión.
    """
    if not user or not user.email:
        return False

    try:
        from django.urls import reverse
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from .tokens import email_verification_token

        protocol = 'https' if (request and request.is_secure()) else 'http'
        if request:
            domain = request.get_host()
        else:
            domain = '127.0.0.1:8000'

        nombre = user.first_name or user.username or 'Atleta'
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        activacion_url = f"{protocol}://{domain}{reverse('users:activar_cuenta', kwargs={'uidb64': uid, 'token': token})}"

        timeout_segundos = int(getattr(settings, 'PASSWORD_RESET_TIMEOUT', 86400))
        timeout_horas = max(1, timeout_segundos // 3600)

        context = {
            'user': user,
            'nombre': nombre,
            'domain': domain,
            'protocol': protocol,
            'activacion_url': activacion_url,
            'timeout_horas': timeout_horas,
        }

        asunto = f"Activa tu cuenta en FitApp 🚀 — Confirma tu correo"
        mensaje_texto = render_to_string('emails/activar_cuenta.txt', context)
        mensaje_html = render_to_string('emails/activar_cuenta.html', context)

        email = EmailMultiAlternatives(
            subject=asunto,
            body=mensaje_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(mensaje_html, "text/html")
        email.send(fail_silently=False)

        registrar_log(
            request=request,
            usuario=user,
            nivel='INFO',
            tipo='REGISTRO',
            mensaje=f"Correo de activación de cuenta enviado exitosamente a {user.email}"
        )
        return True
    except Exception as e:
        registrar_log(
            request=request,
            usuario=user,
            nivel='WARNING',
            tipo='OTRO',
            mensaje=f"Fallo al enviar correo de activación a {user.email}: {str(e)}"
        )
        return False


