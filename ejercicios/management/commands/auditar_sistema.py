import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.urls import reverse
from django.contrib.auth import get_user_model
from users.models import Profile, LogActividad
from ejercicios.models import Ejercicio, RegistroEjercicio, Serie
from rutinas.models import Rutina, RutinaEjercicio


class Command(BaseCommand):
    help = "Ejecuta una auditoría integral del sistema, plantillas, datos y casos borde."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.SUCCESS("INICIANDO AUDITORÍA INTEGRAL DE FITAPP"))
        self.stdout.write(self.style.NOTICE("=" * 60))

        # 1. PLANTILLAS
        self.stdout.write("\n[1/5] Verificando sintaxis de plantillas HTML...")
        app_dirs = ['core', 'users', 'ejercicios', 'rutinas', 'dashboard', 'templates']
        errores_tpl = []
        total_tpl = 0

        for app in app_dirs:
            for html_file in Path(app).rglob('*.html'):
                parts = str(html_file).split('templates/')
                tpl_name = parts[-1] if len(parts) > 1 else str(html_file)
                total_tpl += 1
                try:
                    get_template(tpl_name)
                except Exception as e:
                    errores_tpl.append((str(html_file), tpl_name, str(e)))

        self.stdout.write(f"-> Total plantillas analizadas: {total_tpl}")
        if errores_tpl:
            self.stdout.write(self.style.ERROR(f"❌ {len(errores_tpl)} plantillas con error de sintaxis:"))
            for r, t, err in errores_tpl:
                self.stdout.write(f"   * {t}: {err}")
        else:
            self.stdout.write(self.style.SUCCESS("✅ 100% de las plantillas HTML compilan sin errores."))

        # 2. RUTAS
        self.stdout.write("\n[2/5] Verificando resolución de rutas y URLs reversas...")
        rutas_clave = [
            ('login', {}),
            ('logout', {}),
            ('users:perfil', {}),
            ('users:registro', {}),
            ('users:registro_pendiente', {}),
            ('users:reenviar_activacion', {}),
            ('ejercicios:ejercicios', {}),
            ('ejercicios:crear_ejercicio', {}),
            ('rutinas:lista_rutinas', {}),
            ('rutinas:crear_rutina', {}),
            ('dashboard:dashboard', {}),
            ('core:configuracion_sistema', {}),
        ]
        errores_rutas = []
        for n, kw in rutas_clave:
            try:
                reverse(n, kwargs=kw)
            except Exception as e:
                errores_rutas.append((n, str(e)))

        if errores_rutas:
            self.stdout.write(self.style.ERROR(f"❌ {len(errores_rutas)} rutas fallaron:"))
            for n, err in errores_rutas:
                self.stdout.write(f"   * {n}: {err}")
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Las {len(rutas_clave)} rutas principales resuelven correctamente."))

        # 3. BASE DE DATOS
        self.stdout.write("\n[3/5] Verificando integridad de datos en Base de Datos...")
        User = get_user_model()
        self.stdout.write(f"-> Usuarios: {User.objects.count()} (Activos: {User.objects.filter(is_active=True).count()})")
        self.stdout.write(f"-> Ejercicios: {Ejercicio.objects.count()} (Oficiales: {Ejercicio.objects.filter(creado_por=None).count()})")
        self.stdout.write(f"-> Rutinas: {Rutina.objects.count()}")
        self.stdout.write(f"-> Sesiones registradas: {RegistroEjercicio.objects.count()} con {Serie.objects.count()} series")

        # 4. LOGS DE INCIDENCIAS
        self.stdout.write("\n[4/5] Revisando logs de incidencias recientes...")
        logs_error = LogActividad.objects.filter(nivel__in=['ERROR', 'CRITICAL'])
        self.stdout.write(f"-> Incidencias registradas en historial: {logs_error.count()}")
        for lg in logs_error.order_by('-creado_en')[:5]:
            self.stdout.write(f"   [{lg.creado_en.strftime('%d/%m/%Y %H:%M')}] {lg.tipo} en {lg.ruta}: {lg.mensaje[:100]}")

        # 5. CASOS BORDE EN MODELOS
        self.stdout.write("\n[5/5] Analizando casos borde...")
        # Caso borde 1: IMC con altura 0
        p = Profile(peso=70, altura=0)
        try:
            imc = p.imc
            self.stdout.write(f"   * IMC con altura=0: {imc} (OK, no crashea)")
        except ZeroDivisionError:
            self.stdout.write(self.style.ERROR("   ❌ FALLO: ZeroDivisionError al calcular IMC con altura=0"))

        # Caso borde 2: Rutinas sin días
        r = Rutina(nombre="Test", dias_semana="")
        self.stdout.write(f"   * Rutina sin días: lista={r.lista_dias_numeros}, toca_hoy={r.toca_hoy}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("AUDITORÍA FINALIZADA"))
        self.stdout.write("=" * 60)
