from django import forms
from .models import Ejercicio


class EjercicioForm(forms.ModelForm):
    class Meta:
        model = Ejercicio
        fields = [
            'nombre',
            'modalidad',
            'grupo_muscular',
            'tipo',
            'dificultad',
            'equipo_necesario',
            'definicion',
            'foto',
            'video'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm font-medium',
                'placeholder': 'Ej: Correr al aire libre, Partido de pádel, Danza contemporánea, Press Militar...'
            }),
            'modalidad': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm'
            }),
            'grupo_muscular': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm'
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm'
            }),
            'dificultad': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm'
            }),
            'equipo_necesario': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
                'placeholder': 'Ej: Zapatillas de running, Pala de pádel, Esterilla, Mancuernas, Ninguno...'
            }),
            'definicion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
                'rows': 3,
                'placeholder': 'Explica brevemente la técnica, intensidad, recomendaciones o estructura de la sesión...'
            }),
            'foto': forms.FileInput(attrs={
                'class': 'w-full text-xs text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-brand-light/10 file:text-brand-light hover:file:bg-brand-light/20 cursor-pointer'
            }),
            'video': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-brand-light text-sm',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
        }
