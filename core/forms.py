from django import forms
from .models import ConfiguracionSitio


class ConfiguracionSitioForm(forms.ModelForm):
    """
    Formulario estilizado para la edición de la configuración global del sistema desde el panel web de FitApp.
    """
    class Meta:
        model = ConfiguracionSitio
        fields = [
            'modo_mantenimiento',
            'mensaje_mantenimiento',
            'tiempo_estimado_reapertura',
            'registro_abierto',
            'mensaje_registro_cerrado',
            'banner_activo',
            'banner_texto',
            'banner_tipo',
            'usuarios_pueden_crear_ejercicios',
            'nombre_sitio',
            'email_soporte',
        ]
        widgets = {
            'modo_mantenimiento': forms.CheckboxInput(attrs={
                'class': 'sr-only peer',
            }),
            'mensaje_mantenimiento': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
                'placeholder': 'Mensaje mostrado en la pantalla de mantenimiento...',
            }),
            'tiempo_estimado_reapertura': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
                'placeholder': 'Ej. Hoy a las 19:00 o En 45 minutos',
            }),
            'registro_abierto': forms.CheckboxInput(attrs={
                'class': 'sr-only peer',
            }),
            'mensaje_registro_cerrado': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
                'placeholder': 'Mensaje informativo mostrado cuando el registro está cerrado...',
            }),
            'banner_activo': forms.CheckboxInput(attrs={
                'class': 'sr-only peer',
            }),
            'banner_texto': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
                'placeholder': 'Escribe aquí el anuncio visible para todos los usuarios...',
            }),
            'banner_tipo': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
            }),
            'usuarios_pueden_crear_ejercicios': forms.CheckboxInput(attrs={
                'class': 'sr-only peer',
            }),
            'nombre_sitio': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
                'placeholder': 'Nombre de la web / Gimnasio',
            }),
            'email_soporte': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
                'placeholder': 'contacto@tudominio.com',
            }),
        }
