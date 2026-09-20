from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from .models import Profile
from .tokens import email_verification_token
from .utils import registrar_log, enviar_correo_bienvenida, enviar_correo_activacion
from .forms import (
    RegistroUsuarioForm,
    UserUpdateForm,
    ProfileForm,
    CambioPasswordTailwindForm
)
from rutinas.models import Rutina
from ejercicios.models import RegistroEjercicio, Serie
from core.models import ConfiguracionSitio

User = get_user_model()


def registro_view(request):
    """
    Permite el registro público de nuevos usuarios si está habilitado en ConfiguracionSitio.
    Crea la cuenta en estado inactivo (is_active=False) y envía un correo
    con un enlace seguro para activar la cuenta antes del primer acceso.
    """
    if request.user.is_authenticated:
        return redirect('users:perfil')

    config = ConfiguracionSitio.get_config()
    if not config.registro_abierto:
        if request.method == 'POST':
            messages.warning(request, config.mensaje_registro_cerrado)
            return redirect('login')
        return render(request, 'users/registro_cerrado.html', {'config_sitio': config})

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Obligatorio verificar correo antes de acceder
            user.save()

            # Aseguramos que el perfil existe con email_verificado=False
            Profile.objects.get_or_create(user=user, defaults={'email_verificado': False})

            # Registro en auditoría
            registrar_log(
                request=request,
                usuario=user,
                nivel='INFO',
                tipo='REGISTRO',
                mensaje=f"Nuevo usuario registrado (pendiente de activación por email): {user.username} ({user.email})"
            )

            # Envío de correo con enlace de activación
            enviar_correo_activacion(user, request)

            # Guardamos email en sesión para mostrarlo en la pantalla informativa
            request.session['registro_email'] = user.email

            messages.info(
                request,
                f"¡Cuenta creada! Hemos enviado un enlace de activación a {user.email}. Revisa tu bandeja de entrada."
            )
            return redirect('users:registro_pendiente')
        else:
            messages.error(request, "Por favor corrige los errores indicados en el formulario.")
    else:
        form = RegistroUsuarioForm()

    context = {
        'form': form
    }
    return render(request, 'users/registro.html', context)


def registro_pendiente_view(request):
    """
    Pantalla informativa mostrada inmediatamente tras el registro,
    recordando al usuario que debe confirmar su correo antes de acceder.
    """
    if request.user.is_authenticated:
        return redirect('users:perfil')

    email = request.session.get('registro_email', '')
    return render(request, 'users/registro_pendiente.html', {'email': email})


def activar_cuenta_view(request, uidb64, token):
    """
    Valida el token de activación recibido por correo. Si es válido, activa la cuenta
    (is_active=True, email_verificado=True), envía el correo de bienvenida y
    conecta la sesión del usuario.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.filter(pk=uid).first()
    except (TypeError, ValueError, OverflowError):
        user = None

    if user and email_verification_token.check_token(user, token):
        # Activar usuario
        user.is_active = True
        user.save(update_fields=['is_active'])

        # Asegurar perfil marcado como verificado
        if not hasattr(user, 'profile'):
            Profile.objects.create(user=user)
        user.profile.email_verificado = True
        user.profile.save(update_fields=['email_verificado'])

        # Registro en auditoría
        registrar_log(
            request=request,
            usuario=user,
            nivel='INFO',
            tipo='REGISTRO',
            mensaje=f"Cuenta activada y correo confirmado exitosamente: {user.email}"
        )

        # Enviar correo de bienvenida completo tras activación
        enviar_correo_bienvenida(user, request)

        # Iniciar sesión automáticamente
        login(request, user, backend='users.backends.EmailOrUsernameModelBackend')

        # Limpiar email temporal de sesión
        request.session.pop('registro_email', None)

        messages.success(
            request,
            f"¡Tu cuenta ha sido activada con éxito, {user.first_name or user.username}! Bienvenido a FitApp."
        )
        return redirect('users:perfil')

    # Si ya estaba activo y verificado
    if user and user.is_active and getattr(user, 'profile', None) and user.profile.email_verificado:
        messages.info(request, "Tu cuenta ya se encuentra activa y verificada. Puedes iniciar sesión.")
        return redirect('login')

    # Token inválido o expirado
    return render(request, 'users/activacion_invalida.html')


def reenviar_activacion_view(request):
    """
    Permite solicitar un nuevo enlace de activación si el anterior caducó o no llegó.
    """
    if request.user.is_authenticated:
        return redirect('users:perfil')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Por favor introduce un correo electrónico válido.")
            return render(request, 'users/reenviar_activacion.html')

        user = User.objects.filter(email__iexact=email).first()

        if user:
            profile = getattr(user, 'profile', None)
            if user.is_active and profile and profile.email_verificado:
                messages.info(request, "Esta cuenta ya está activa y verificada. Puedes iniciar sesión directamente.")
                return redirect('login')
            elif not user.is_active and profile and profile.email_verificado:
                messages.error(request, "Esta cuenta ha sido deshabilitada por un administrador. Contacta con soporte.")
                return redirect('login')
            else:
                # Enviar nuevo enlace de activación
                enviar_correo_activacion(user, request)
                request.session['registro_email'] = user.email
                messages.success(request, f"Hemos enviado un nuevo enlace de activación a {user.email}. Revisa tu bandeja de entrada.")
                return redirect('users:registro_pendiente')
        else:
            # Por privacidad, mostramos mensaje neutro
            messages.info(request, f"Si existe una cuenta registrada con {email}, hemos enviado un nuevo enlace de activación.")
            return redirect('users:registro_pendiente')

    return render(request, 'users/reenviar_activacion.html')


@login_required
def perfil_view(request):
    """
    Vista integral del perfil de usuario:
    - Ficha de salud, métricas físicas (IMC) y plan de suscripción (Monetización).
    - Edición de datos personales y deportivos.
    - Cambio seguro de contraseña dentro de la misma vista.
    - Resumen de actividad deportiva histórica.
    """
    usuario = request.user
    # Garantiza la existencia del perfil sin error 500
    perfil, _ = Profile.objects.get_or_create(user=usuario)

    user_form = UserUpdateForm(instance=usuario)
    profile_form = ProfileForm(instance=perfil)
    password_form = CambioPasswordTailwindForm(user=usuario)
    pestaña_activa = request.GET.get('tab', 'ver')

    if request.method == 'POST':
        action = request.POST.get('action', 'actualizar_perfil')

        if action == 'actualizar_perfil':
            user_form = UserUpdateForm(request.POST, instance=usuario)
            profile_form = ProfileForm(request.POST, request.FILES, instance=perfil)
            pestaña_activa = 'editar'

            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                registrar_log(
                    request=request,
                    usuario=usuario,
                    nivel='INFO',
                    tipo='PERFIL_EDIT',
                    mensaje="Perfil y datos personales actualizados exitosamente."
                )
                messages.success(request, '¡Tu perfil y datos deportivos se han actualizado con éxito!')
                return redirect('users:perfil')
            else:
                messages.error(request, 'Hubo un error al actualizar los datos. Revisa los campos.')

        elif action == 'cambiar_password':
            password_form = CambioPasswordTailwindForm(user=usuario, data=request.POST)
            pestaña_activa = 'seguridad'

            if password_form.is_valid():
                user = password_form.save()
                # Mantiene la sesión iniciada tras cambiar la contraseña
                update_session_auth_hash(request, user)
                registrar_log(
                    request=request,
                    usuario=usuario,
                    nivel='INFO',
                    tipo='PASSWORD_CHANGE',
                    mensaje="Contraseña de usuario cambiada desde el panel de perfil."
                )
                messages.success(request, '¡Tu contraseña ha sido cambiada correctamente!')
                return redirect('users:perfil')
            else:
                messages.error(request, 'No se pudo cambiar la contraseña. Verifica los requisitos.')

        elif action == 'cambiar_foto':
            if request.POST.get('eliminar_foto') == '1':
                if perfil.foto_perfil:
                    perfil.foto_perfil.delete(save=False)
                    perfil.foto_perfil = None
                    perfil.save()
                    registrar_log(
                        request=request,
                        usuario=usuario,
                        nivel='INFO',
                        tipo='PERFIL_EDIT',
                        mensaje="Foto de perfil eliminada por el usuario."
                    )
                    messages.success(request, 'Tu foto de perfil ha sido eliminada.')
                return redirect('users:perfil')

            elif 'foto_perfil' in request.FILES:
                foto = request.FILES['foto_perfil']
                # Validar tipo de archivo
                if not foto.content_type.startswith('image/'):
                    messages.error(request, 'El archivo subido no es una imagen válida (debe ser JPG, PNG o WebP).')
                elif foto.size > 8 * 1024 * 1024:  # 8 MB máx
                    messages.error(request, 'La imagen no debe superar los 8 MB de tamaño.')
                else:
                    perfil.foto_perfil = foto
                    perfil.save()
                    registrar_log(
                        request=request,
                        usuario=usuario,
                        nivel='INFO',
                        tipo='PERFIL_EDIT',
                        mensaje="Foto de perfil actualizada exitosamente."
                    )
                    messages.success(request, '¡Foto de perfil actualizada con éxito!')
                return redirect('users:perfil')
            else:
                messages.warning(request, 'No se ha seleccionado ninguna imagen.')
                return redirect('users:perfil')

    # Resumen de actividad deportiva
    total_rutinas = Rutina.objects.filter(usuario=usuario).count()
    total_dias_entrenados = RegistroEjercicio.objects.filter(usuario=usuario).values('fecha').distinct().count()
    total_series_hechas = Serie.objects.filter(registro__usuario=usuario).count()
    ultimo_registro = RegistroEjercicio.objects.filter(usuario=usuario).order_by('-fecha').first()

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'perfil': perfil,
        'pestaña_activa': pestaña_activa,
        'total_rutinas': total_rutinas,
        'total_dias_entrenados': total_dias_entrenados,
        'total_series_hechas': total_series_hechas,
        'ultimo_registro': ultimo_registro,
    }
    return render(request, 'users/perfil.html', context)