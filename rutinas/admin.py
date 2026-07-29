from django.contrib import admin
from django.utils.timezone import now
from rutinas.models import Rutina, RutinaEjercicio
from ejercicios.models import RegistroEjercicio, Ejercicio

# ... (Aquí se mantiene tu código anterior de SerieInline y RegistroEjercicioAdmin) ...

# =====================================================================
# INLINE PARA AÑADIR EJERCICIOS DENTRO DE UNA RUTINA
# =====================================================================
class RutinaEjercicioInline(admin.TabularInline):
    model = RutinaEjercicio
    extra = 2
    ordering = ('orden',) # Muestra los ejercicios ordenados por el campo 'orden'

# =====================================================================
# ACCIÓN PERSONALIZADA PARA INICIAR LA RUTINA
# =====================================================================
@admin.action(description="Iniciar rutina seleccionada para hoy")
def iniciar_rutina_hoy(modeladmin, request, queryset):
    """
    Esta función toma las rutinas seleccionadas y crea un RegistroEjercicio 
    vacío para cada uno de sus ejercicios en el día actual.
    """
    for rutina in queryset:
        # Obtenemos todos los ejercicios de esta rutina ordenados
        ejercicios_rutina = RutinaEjercicio.objects.filter(rutina=rutina).order_by('orden')
        
        for item in ejercicios_rutina:
            # Creamos el registro en blanco para que el usuario luego añada las series
            RegistroEjercicio.objects.create(
                usuario=request.user,
                ejercicio=item.ejercicio,
                rutina=rutina,
                fecha=now().date(),
                etiqueta=f"Sesión: {rutina.nombre}"
            )
            
    # Mensaje de confirmación en la interfaz
    modeladmin.message_user(request, "¡Rutina iniciada! Se han creado los ejercicios. Ve a 'Registros de Ejercicios' para rellenar tus series.")

# =====================================================================
# CONFIGURACIÓN DEL PANEL DE ADMINISTRACIÓN DE RUTINAS
# =====================================================================
@admin.register(Rutina)
class RutinaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'usuario', 'creado_en')
    inlines = [RutinaEjercicioInline]
    actions = [iniciar_rutina_hoy] # Añadimos nuestra acción personalizada
    exclude = ('usuario',)         # Ocultamos el usuario para asignarlo automáticamente

    def save_model(self, request, obj, form, change):
        # Asigna automáticamente el usuario actual al crear la rutina
        if not change:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)