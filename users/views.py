from django.shortcuts import render, redirect
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count

from .models import Profile
from .utils import registrar_log, enviar_correo_bienvenida
from .forms import (
    RegistroUsuarioForm,
    UserUpdateForm,
    ProfileForm,
    CambioPasswordTailwindForm
)
from rutinas.models import Rutina
from ejercicios.models import RegistroEjercicio, Serie


def registro_view(request):
    """
    Permite el registro público de nuevos usuarios de forma autónoma.
    Al crearse la cuenta, inicia sesión automáticamente y redirige al perfil.
    """
    if request.user.is_authenticated:
        return redirect('users:perfil')

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Aseguramos que el perfil existe
            Profile.objects.get_or_create(user=user)
            # Registro en auditoría
            registrar_log(
                request=request,
                usuario=user,
                nivel='INFO',
                tipo='REGISTRO',
                mensaje=f"Nuevo usuario registrado en la app: {user.username} ({user.email})"
            )
            # Envío de correo de bienvenida (tolerante a fallos)
            enviar_correo_bienvenida(user, request)

            # Iniciamos sesión automáticamente
            login(request, user, backend='users.backends.EmailOrUsernameModelBackend')
            messages.success(
                request,
                f"¡Bienvenido a FitApp, {user.first_name or user.username}! Tu cuenta ha sido creada exitosamente."
            )
            return redirect('users:perfil')
        else:
            messages.error(request, "Por favor corrige los errores indicados en el formulario.")
    else:
        form = RegistroUsuarioForm()

    context = {
        'form': form
    }
    return render(request, 'users/registro.html', context)


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