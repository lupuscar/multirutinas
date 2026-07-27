# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from users.models import Profile

User = get_user_model()

# 1. Definimos un Inline para el perfil
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil Deportivo'
    fk_name = 'user'
    readonly_fields = ('imc',)

# 2. Definimos una nueva vista de Admin para el Usuario que incluye el Inline
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]

    # Opcional: Mostrar campos del perfil en la lista general de usuarios
    list_display = BaseUserAdmin.list_display + ('get_peso', 'get_altura', 'get_imc')

    @admin.display(description='Peso (kg)')
    def get_peso(self, instance):
        return getattr(instance.profile, 'peso', None) if hasattr(instance, 'profile') else None

    @admin.display(description='Altura (cm)')
    def get_altura(self, instance):
        return getattr(instance.profile, 'altura', None) if hasattr(instance, 'profile') else None
    # Método para obtener el IMC en la lista
    @admin.display(description='IMC')
    def get_imc(self, instance):
        if hasattr(instance, 'profile') and instance.profile.imc:
            return instance.profile.imc
        return '-'


# 3. Desregistramos el Admin por defecto y registramos el personalizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# 4. (Opcional) Registrar también el modelo Profile de forma independiente si prefieres gestionarlo por separado
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'peso', 'altura', 'nivel', 'imc')
    list_filter = ('nivel',)
    search_fields = ('user__username', 'user__email')