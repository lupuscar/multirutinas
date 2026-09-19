from django.contrib import admin
from ejercicios.models import Ejercicio, RegistroEjercicio, Serie

# 1. Creamos el Inline para las Series dentro del Registro
class SerieInline(admin.TabularInline):
    model = Serie
    extra = 0  # Muestra 3 filas en blanco listas para rellenar al crear un registro nuevo
    min_num = 3 # Requiere al menos 1 serie grabada
    # 1. ORDEN DE LAS COLUMNAS EN LA TABLA:
    # Definimos el orden exacto de aparición. 'numero_serie' será la 1ª columna.
    fields = ('numero_serie', 'repeticiones', 'peso_kg', 'tiempo_segundos')
    readonly_fields = ('numero_serie',)
    def get_formset(self, request, obj=None, **kwargs):
            """
            Sobrescribimos el FormSet para asignar dinámicamente los números de serie 
            por defecto (1, 2, 3, 4...) en las filas vacías que se muestran al usuario.
            """
            FormSet = super().get_formset(request, obj, **kwargs)
            
            class EvaluatedFormSet(FormSet):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    
                    # Si estamos editando un registro existente, contamos sus series guardadas
                    series_existentes = obj.series_detalle.count() if obj else 0
                    
                    # Asignamos el número por defecto a cada formulario extra/vacío
                    for i, form in enumerate(self.extra_forms, start=1):
                        siguiente_numero = series_existentes + i
                        # Asignamos el valor al campo del modelo/formulario
                        form.initial['numero_serie'] = siguiente_numero
                        
                        # Si la instancia ya tiene objeto, le asignamos la propiedad
                        if not getattr(form.instance, 'numero_serie', None):
                            form.instance.numero_serie = siguiente_numero

            return EvaluatedFormSet
# 2. Configuración del Admin para el Registro
@admin.register(RegistroEjercicio)
class RegistroEjercicioAdmin(admin.ModelAdmin):
    list_display = ('ejercicio', 'usuario', 'fecha', 'obtener_total_series')
    list_filter = ('fecha', 'usuario')
    search_fields = ('ejercicio__nombre', 'usuario__username')
    inlines = [SerieInline]
    
    # Excluimos el campo 'usuario' del formulario para que el usuario no tenga que elegirlo
    exclude = ('usuario',)

    def save_model(self, request, obj, form, change):
        # Asignamos automáticamente el usuario logueado en la sesión
        if not change: # Solo al crear un registro nuevo
            obj.usuario = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        # Garantiza que las series creadas mediante el Inline conozcan y ordenen su número
        instances = formset.save(commit=False)
        for index, instance in enumerate(instances, start=1):
            if isinstance(instance, Serie) and not instance.numero_serie:
                instance.numero_serie = index
            instance.save()
        formset.save_m2m()

    @admin.display(description='Total Series')
    def obtener_total_series(self, instance):
        return instance.series_detalle.count()


@admin.register(Ejercicio)
class EjercicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'modalidad', 'grupo_muscular', 'tipo', 'dificultad', 'creado_por')
    list_filter = ('modalidad', 'grupo_muscular', 'tipo', 'dificultad')
    search_fields = ('nombre',)