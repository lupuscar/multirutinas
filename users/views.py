# users/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from users.models import Profile

@login_required
def perfil_view(request):  # <-- Asegúrate de que se llame 'perfil_view'
    perfil = request.user.profile
    return render(request, 'users/perfil.html', {'perfil': perfil})



