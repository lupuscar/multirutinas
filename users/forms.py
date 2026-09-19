from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import Profile

User = get_user_model()


# =====================================================================
# 1. FORMULARIO DE REGISTRO PÚBLICO (SIGNUP)
# =====================================================================
class RegistroUsuarioForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        help_text="Necesario para recuperar tu contraseña y enviarte resúmenes de progreso.",
        widget=forms.EmailInput(attrs={
            'placeholder': 'tu@email.com',
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label="Nombre",
        widget=forms.TextInput(attrs={
            'placeholder': 'Tu nombre',
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm'
        })
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'email')
        labels = {
            'username': 'Nombre de usuario',
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Elige un usuario único',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicamos estilos a los campos de contraseña
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
            'placeholder': 'Crea una contraseña segura'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
            'placeholder': 'Repite la contraseña'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo electrónico.")
        return email


# =====================================================================
# 2. EDICIÓN DE DATOS BÁSICOS DEL USUARIO
# =====================================================================
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light'
            }),
        }


# =====================================================================
# 3. EDICIÓN DEL PERFIL DEPORTIVO Y OBJETIVOS
# =====================================================================
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'foto_perfil',
            'biografia',
            'peso',
            'altura',
            'fecha_nacimiento',
            'nivel',
            'objetivo',
            'dias_objetivo_semana'
        ]
        widgets = {
            'foto_perfil': forms.FileInput(attrs={
                'class': 'w-full text-xs text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-brand-light/10 file:text-brand-light hover:file:bg-brand-light/20 cursor-pointer'
            }),
            'biografia': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light',
                'placeholder': 'Ej: Entrenando con foco en salud y fuerza.'
            }),
            'peso': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light',
                'step': '0.1'
            }),
            'altura': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light',
            }),
            'fecha_nacimiento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light'
                }
            ),
            'nivel': forms.Select(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light'
            }),
            'objetivo': forms.Select(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light'
            }),
            'dias_objetivo_semana': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light',
                'min': '1',
                'max': '7'
            }),
        }
        labels = {
            'foto_perfil': 'Foto de perfil',
            'biografia': 'Lema o Biografía',
            'peso': 'Peso corporal (kg)',
            'altura': 'Altura (cm)',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'nivel': 'Nivel de Experiencia',
            'objetivo': 'Objetivo Principal',
            'dias_objetivo_semana': 'Días de entrenamiento por semana',
        }


# =====================================================================
# 4. CAMBIO DE CONTRASEÑA EN EL PERFIL
# =====================================================================
class CambioPasswordTailwindForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white text-sm outline-none focus:ring-2 focus:ring-brand-light',
                'placeholder': '••••••••'
            })