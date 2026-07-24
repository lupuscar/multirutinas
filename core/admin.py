from django.contrib import admin

from .models import Sesion, SesionEjercicio, SerieRealizada


class SesionEjercicioInline(admin.TabularInline):
    """
    Inline simple dentro de Sesion. No incluye las series realizadas
    (Django admin no soporta inlines anidados de serie); para editar
    las series de un ejercicio concreto, se hace desde SesionEjercicioAdmin.
    """
    model = SesionEjercicio
    extra = 1
    fields = ("orden", "ejercicio", "rutina_ejercicio", "notas")
    autocomplete_fields = ("ejercicio", "rutina_ejercicio")
    ordering = ("orden",)


@admin.register(Sesion)
class SesionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "fecha", "rutina", "lugar", "completada")
    list_filter = ("completada", "lugar", "fecha")
    search_fields = ("usuario__username", "rutina__nombre")
    autocomplete_fields = ("usuario", "rutina")
    date_hierarchy = "fecha"
    inlines = (SesionEjercicioInline,)
    readonly_fields = ("creada_en",)


class SerieRealizadaInline(admin.TabularInline):
    model = SerieRealizada
    extra = 1
    fields = ("numero_serie", "repeticiones_realizadas", "peso_kg", "rpe", "al_fallo", "notas")
    ordering = ("numero_serie",)


@admin.register(SesionEjercicio)
class SesionEjercicioAdmin(admin.ModelAdmin):
    """
    Aquí se editan las series realizadas de un ejercicio concreto de una sesión.
    """
    list_display = ("sesion", "ejercicio", "orden", "rutina_ejercicio")
    search_fields = ("sesion__usuario__username", "ejercicio__nombre")
    autocomplete_fields = ("sesion", "ejercicio", "rutina_ejercicio")
    inlines = (SerieRealizadaInline,)


@admin.register(SerieRealizada)
class SerieRealizadaAdmin(admin.ModelAdmin):
    """Registro independiente para poder buscar/filtrar series sueltas."""
    list_display = (
        "sesion_ejercicio",
        "numero_serie",
        "repeticiones_realizadas",
        "peso_kg",
        "rpe",
        "al_fallo",
    )
    list_filter = ("al_fallo", "rpe")
    search_fields = ("sesion_ejercicio__ejercicio__nombre", "sesion_ejercicio__sesion__usuario__username")