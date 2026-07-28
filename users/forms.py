from django import forms
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

# Formulario 1: Para editar datos básicos del Usuario (User)
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
        }

# Formulario 2: Para editar datos deportivos del Perfil (Profile)
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['foto_perfil', 'peso', 'altura', 'fecha_nacimiento', 'nivel']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'foto_perfil': 'Foto de perfil',
            'peso': 'Peso (kg)',
            'altura': 'Altura (cm)',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'nivel': 'Nivel de Experiencia',
        }