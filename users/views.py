from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserUpdateForm, ProfileForm

@login_required
def perfil_view(request):
    usuario = request.user
    perfil = request.user.profile

    if request.method == 'POST':
        # Instanciamos ambos formularios con los datos enviados por el usuario (POST y FILES)
        user_form = UserUpdateForm(request.POST, instance=usuario)
        profile_form = ProfileForm(request.POST, request.FILES, instance=perfil)

        # Verificamos que ambos formularios sean válidos antes de guardar
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, '¡Tu perfil y datos personales han sido actualizados correctamente!')
            return redirect('users:perfil')
    else:
        # Petición GET: Cargamos los formularios con los datos actuales del usuario y perfil
        user_form = UserUpdateForm(instance=usuario)
        profile_form = ProfileForm(instance=perfil)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'perfil': perfil,
    }
    return render(request, 'users/perfil.html', context)