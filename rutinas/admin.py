from django.contrib import admin, messages
from rutinas.models import Rutina, RutinaEjercicio
from ejercicios.models import RegistroEjercicio, Serie


# =====================================================================
# INLINE PARA AÑADIR EJERCICIOS DENTRO DE UNA RUTINA
# =====================================================================
class RutinaEjercicioInline(admin.TabularInline):
    model = RutinaEjercicio
    extra = 1
    ordering = ('orden',)
    fields = ('orden', 'ejercicio', 'series_objetivo', 'repeticiones_objetivo', 'tiempo_objetivo_segundos')
    autocomplete_fields = ['ejercicio']


# =====================================================================
# ACCIÓN PERSONALIZADA PARA INICIAR LA RUTINA
# =====================================================================
@admin.action(description="Iniciar rutina seleccionada para hoy")
def iniciar_rutina_hoy(modeladmin, request, queryset):
    """
    Toma las rutinas seleccionadas y crea un RegistroEjercicio y sus Series objetivo
    para cada uno de sus ejercicios en el día actual.
    """
    total_creados = 0
    for rutina in queryset:
        ejercicios_rutina = RutinaEjercicio.objects.filter(rutina=rutina).order_by('orden')
        
        for item in ejercicios_rutina:
            registro = RegistroEjercicio.objects.create(
                usuario=request.user,
                ejercicio=item.ejercicio,
                etiqueta=f"Sesión: {rutina.nombre}"
            )
            
            num_series = item.series_objetivo or 3
            reps = item.repeticiones_objetivo if item.ejercicio.modalidad == 'REPS_PESO' else None
            tiempo = item.tiempo_objetivo_segundos if item.ejercicio.modalidad == 'TIEMPO' else None

            for n_serie in range(1, num_series + 1):
                Serie.objects.create(
                    registro=registro,
                    numero_serie=n_serie,
                    repeticiones=reps,
                    peso_kg=None,
                    tiempo_segundos=tiempo
                )
            total_creados += 1


    if total_creados > 0:
        modeladmin.message_user(
            request,
            f"¡Rutina iniciada! Se han preparado {total_creados} ejercicio(s) con sus series. Ve a 'Registros de Ejercicios' para rellenar tus pesos.",
            level=messages.SUCCESS
        )
    else:
        modeladmin.message_user(
            request,
            "No se crearon ejercicios. Asegúrate de que la rutina seleccionada tiene ejercicios asignados.",
            level=messages.WARNING
        )


# =====================================================================
# CONFIGURACIÓN DEL PANEL DE ADMINISTRACIÓN DE RUTINAS
# =====================================================================
@admin.register(Rutina)
class RutinaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'usuario', 'total_ejercicios', 'creado_en')
    list_filter = ('usuario', 'creado_en')
    search_fields = ('nombre', 'usuario__username')
    inlines = [RutinaEjercicioInline]
    actions = [iniciar_rutina_hoy]
    exclude = ('usuario',)

    @admin.display(description="Nº Ejercicios")
    def total_ejercicios(self, obj):
        return obj.ejercicios.count()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(usuario=request.user)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)