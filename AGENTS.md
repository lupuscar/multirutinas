# AGENTS.md — Contexto y Memoria de Desarrollo para Antigravity

Este documento sirve como **memoria persistente y guía contextual** de **Multirutinas (FitApp)** para Antigravity y otros asistentes de IA. Cada vez que se inicie una nueva sesión en este repositorio, este archivo proporciona la arquitectura completa, estado actual, convenciones técnicas y comandos clave.

---

## 🎯 1. Visión y Propósito del Proyecto

**Multirutinas (FitApp)** es una plataforma web progresiva desarrollada con **Django 6** para la gestión deportiva integral:
- **Planificación:** Creación y calendarización semanal de rutinas (por días de la semana: Lunes a Domingo) sin duplicar ejercicios.
- **Entrenamientos Híbridos:** Fuerza clásica con sobrecarga progresiva, deportes (Pádel, Baloncesto, Fútbol), danza contemporánea/baile, actividades outdoor (running, senderismo) y movilidad/yoga.
- **Ejecución en Vivo (Modo Gym):** Registro de series en tiempo real vía AJAX, cronómetro de descanso interactivo con aviso sonoro y presets rápidos de tiempo.
- **Analítica Avanzada (Dashboard):** Cálculo científico del 1RM con fórmula de Epley, Salón de Récords Personales (PRs), rachas semanales, comparativas de volumen ($\pm\%$) y recomendación priorizada según el día actual.
- **Auditoría e Incidencias:** Captura automática de excepciones 500 con traceback, monitorización de logins/logouts y panel administrativo de logs.

---

## 🏗️ 2. Arquitectura de Aplicaciones y Modelos

### `core` (Configuración Global, Mantenimiento y Operaciones)
- **`ConfiguracionSitio`:** Modelo Singleton (ID=1) con almacenamiento en caché (`django.core.cache`) para 0 overhead por petición.
  - Campos: `modo_mantenimiento`, `mensaje_mantenimiento`, `tiempo_estimado_reapertura`, `registro_abierto`, `mensaje_registro_cerrado`, `banner_activo`, `banner_texto`, `banner_tipo`, `usuarios_pueden_crear_ejercicios`, `nombre_sitio`, `email_soporte`.
- **`middleware.py` (`MaintenanceModeMiddleware`):** Intercepta peticiones cuando el modo mantenimiento está activo. Ofrece bypass a Staff/Superusuarios y rutas `/admin/`, login y estáticos; para el resto devuelve respuesta HTTP 503 personalizada (`templates/core/503.html`).
- **`context_processors.py` (`configuracion_sitio`):** Inyecta `config_sitio` globalmente en todas las plantillas para banners y lógica visual.
- **Panel Web de Ajustes (`/configuracion/sistema/`):** Pantalla administrativa con estética FitApp, métricas en vivo, switches reactivos con Alpine.js y botones de 1 clic (limpiar sesiones caducadas y purga de logs antiguos).
- **Django Admin (`/admin/core/configuracionsitio/`):** Administración nativa con restricciones singleton (no permite añadir más ni borrar).

### `users` (Usuarios, Salud y Auditoría)
- **`Profile`:** Extensión del modelo `User` con ficha antropométrica (`peso_kg`, `altura_cm`, `fecha_nacimiento`, `foto`), meta semanal (`dias_objetivo_semana`), objetivo deportivo (`HIP`, `FUE`, `DEF`, `RES`, `SAL`), nivel, membresía comercial (`tipo_suscripcion`: `FREE`, `PRO`, `COACH`) y estado de verificación de correo (`email_verificado`).
  - `@property categoria_imc`: Clasificación dinámica del IMC (*Bajo peso*, *Peso normal*, *Sobrepeso*, *Obesidad*).
- **`LogActividad`:** Sistema de auditoría y captura de incidencias.
  - Campos: `usuario`, `nivel` (INFO, WARNING, ERROR, CRITICAL), `tipo` (LOGIN, LOGOUT, LOGIN_FAIL, REGISTRO, PERFIL_EDIT, PASSWORD_CHANGE, ERROR_500), `ruta`, `metodo`, `ip`, `user_agent`, `mensaje`, `traceback`, `creado_en`.
- **`middleware.py` (`AuditAndErrorLoggingMiddleware`):** Captura en `process_exception` cualquier error 500 no controlado y registra la traza completa.
- **`signals.py`:** Crea automáticamente el `Profile` al registrarse un usuario y registra eventos de autenticación.
- **`backends.py` (`EmailOrUsernameModelBackend`):** Permite autenticación insensible a mayúsculas tanto por correo electrónico como por nombre de usuario tradicional.
- **`tokens.py` (`EmailVerificationTokenGenerator`):** Genera tokens seguros de un solo uso vinculados al estado `is_active` y al email.
- **`utils.py`:** Funciones `get_client_ip(request)`, `registrar_log(...)` (tolerante a fallos), `enviar_correo_activacion(user, request)` y `enviar_correo_bienvenida(user, request)`.

### `ejercicios` (Catálogo y Tipos de Actividad)
- **`Ejercicio`:**
  - `tipo`: Máquina (`MAQ`), Peso Libre (`LIB`), Poleas (`POL`), Calistenia (`CAL`), Deporte (`DEP`), Danza (`DAN`), Aire Libre (`OUT`), Flexibilidad/Yoga (`FLL`).
  - `grupo_muscular`: Pecho (`PEC`), Espalda (`ESP`), Pierna (`PIE`), Brazos (`BRA`), Hombro (`HOM`), Core (`COR`), Full Body (`FUL`), Cardiovascular (`CAR`), Agilidad (`AGI`).
  - `modalidad`: Repeticiones + Peso (`REPS_PESO`), Tiempo (`TIEMPO`), Distancia (`DISTANCIA`).
  - `icono`: Asigna dinámicamente iconos FontAwesome según la disciplina.
- **`RegistroEjercicio`:** Registro de una sesión de entrenamiento para un ejercicio y usuario.
- **`Serie`:** Series individuales (`numero_serie`, `repeticiones`, `peso_kg`, `tiempo_segundos`, `distancia_metros`, `rpe`).

### `rutinas` (Planificación, Calendarización y Modo Gym)
- **`Rutina`:**
  - `dias_semana`: Cadena con los días asignados en formato ordenado separado por comas (ej. `"1,4"` para Martes y Viernes; `0=Lun, ..., 6=Dom`).
  - `lista_dias_numeros`: Propiedad que devuelve lista de enteros `[1, 4]`.
  - `badges_dias`: Propiedad estructurada con `num`, `corto` y `completo` para badges en UI.
  - `toca_hoy`: Determina si hoy (`timezone.now().date().weekday()`) toca entrenar esta rutina.
- **`RutinaEjercicio`:** Tabla intermedia ordenable con `series_objetivo`, `repeticiones_objetivo` o `tiempo_objetivo_segundos`.
- **Modo Gym (`ejecutar_rutina.html`):** Interfaz en vivo con llamadas a `guardar_serie_ajax`, timers de descanso y audio synth.
- **Formulario Reactivo (`form_rutina.html`):** Alpine.js controla la selección interactiva de los 7 días de la semana.

### `dashboard` (Centro de Mando Analítico)
- **Rachas y Calendario:** Algoritmo que calcula semanas continuas entrenando (`racha_semanas`) y desglose Lunes-Domingo de la semana en curso.
- **Tendencias Semanales:** Comparativas porcentuales ($\pm\%$) de volumen total ($kg \times reps$) y series respecto a la semana previa.
- **1RM & PRs:** Fórmula de Epley ($1RM = \text{Peso} \times (1 + \text{Reps} / 30)$) sobre el historial de series.
- **Recomendador Prioritario:** Recomienda primero la rutina programada para el día actual (`es_programada_hoy`) si está pendiente; si no, aplica rotación por fecha más antigua.

---

## 🛠️ 3. Comandos Esenciales de Terminal

El entorno virtual se encuentra en `.venv`. Comandos ejecutables:

```bash
# Iniciar servidor de desarrollo
.venv/bin/python manage.py runserver

# Aplicar migraciones pendientes
.venv/bin/python manage.py migrate

# Ejecutar la suite completa de pruebas unitarias (100% pasando, 59 tests)
.venv/bin/python manage.py test core.tests users.tests dashboard.tests ejercicios.tests rutinas.tests

# Generar datos de prueba para el Dashboard (todas las cuentas o una específica)
.venv/bin/python manage.py crear_datos_demo
.venv/bin/python manage.py crear_datos_demo --usuario silvia
.venv/bin/python manage.py crear_datos_demo --usuario carlos --limpiar
```

---

## 🎨 4. Convenciones de Frontend y Estilo

- **Diseño:** Tailwind CSS + Bootstrap / AdminLTE modificado con tema oscuro premium (`brand-dark: #0f172a`, `brand-light: #6366f1`, acentos esmeralda y ámbar).
- **Reactividad Ligera:** Se utiliza **Alpine.js** (`x-data`, `x-show`, `x-bind`, `x-cloak`) para evitar sobrecarga de frameworks pesados.
- **Gráficos:** **Chart.js** con tooltips estilizados y degradados transparentes.
- **Audio:** `AudioContext` sintético del navegador (tonos sinusoidales puros a 440 Hz / 880 Hz) para avisos sonoros sin dependencias de archivos de audio externos.

---

## 🔒 5. Directrices de Seguridad y Buenas Prácticas

1. **Aislamiento por Usuario:** Cualquier consulta a `Rutina`, `RegistroEjercicio`, `Serie` o `Profile` debe filtrar estrictamente por `usuario=request.user`.
2. **Registro No Bloqueante:** Toda auditoría o logging mediante `registrar_log` está encapsulada en `try...except` para garantizar que ningún fallo de telemetría afecte la experiencia del deportista.
3. **Compatibilidad Multiplataforma:** No asumir dispositivos específicos; las interfaces de entrenamiento están optimizadas para pantallas táctiles de móviles (Modo Gym) y pantallas de escritorio (Dashboard y Catálogo).
