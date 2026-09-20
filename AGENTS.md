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
- **PWA (Progressive Web App):**
  - Endpoints raíz: `pwa_manifest_view` (`/manifest.json`), `pwa_service_worker_view` (`/sw.js` con cabecera HTTP `Service-Worker-Allowed: /`), `pwa_offline_view` (`/offline/`).
  - Estrategia Service Worker: Precaching del app shell, Network First para navegación con pantalla de reserva offline (`templates/pwa/offline.html`), y Cache First para estáticos/CDNs.
  - Integración con Mantenimiento: `MaintenanceModeMiddleware` permite siempre `/manifest.json`, `/sw.js` y `/offline/`.

### `users` (Usuarios, Salud y Auditoría)
- **`Profile`:** Extensión del modelo `User` con ficha antropométrica (`genero`: `H`, `M`, `O`; `peso_kg`, `altura_cm`, `fecha_nacimiento`, `foto`), meta semanal (`dias_objetivo_semana`), objetivo deportivo (`HIP`, `FUE`, `DEF`, `RES`, `SAL`), nivel, membresía comercial (`tipo_suscripcion`: `FREE`, `PRO`, `COACH`) y estado de verificación de correo (`email_verificado`).
  - `@property categoria_imc`: Clasificación dinámica del IMC (*Bajo peso*, *Peso normal*, *Sobrepeso*, *Obesidad*).
  - `@property icono_genero`: Ícono FontAwesome correspondiente al sexo / género (`fa-mars`, `fa-venus`, `fa-genderless`, `fa-venus-mars`).
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
- **Registro de Actividad Libre / Sesión Rápida (`registrar_sesion_libre`):**
  - Permite a los usuarios registrar entrenamientos independientes (running, pádel, series sueltas, etc.) sin vincularlos a ninguna rutina predefinida.
  - Accesible desde la ficha del ejercicio (`/ejercicios/detalle/<id>/`) y directamente desde el Dashboard (`/dashboard/`) mediante modal interactivo en Alpine.js con búsqueda reactiva de ejercicios y presets de tiempo.
  - Alimenta de forma automática la racha semanal, el calendario de 7 días, el volumen total y el cálculo de PRs/1RM.

### `rutinas` (Planificación, Calendarización y Modo Gym)
- **`Rutina`:**
  - `dias_semana`: Cadena con los días asignados en formato ordenado separado por comas (ej. `"1,4"` para Martes y Viernes; `0=Lun, ..., 6=Dom`).
  - `lista_dias_numeros`: Propiedad que devuelve lista de enteros `[1, 4]`.
  - `badges_dias`: Propiedad estructurada con `num`, `corto` y `completo` para badges en UI.
  - `toca_hoy`: Determina si hoy (`timezone.now().date().weekday()`) toca entrenar esta rutina.
- **`RutinaEjercicio`:** Tabla intermedia ordenable con `series_objetivo`, `repeticiones_objetivo`, `peso_objetivo` (kg opcional) o `tiempo_objetivo_segundos`.
- **Modo Gym (`ejecutar_rutina.html`):** Interfaz en vivo con llamadas a `guardar_serie_ajax`, autopropagación inteligente de pesos a series siguientes, carga de valores de la última sesión con 1 toque, steppers ágiles (+/- 5kg), timers de descanso y audio synth.
- **Formulario Reactivo (`form_rutina.html`):** Alpine.js controla la selección interactiva de los 7 días de la semana y la configuración de 3 columnas (Series x Reps @ Peso kg) con steppers y chips rápidos.

### `dashboard` (Centro de Mando Analítico Híbrido y Multidisciplinar)
- **Rachas y Calendario:** Algoritmo que calcula semanas continuas entrenando (`racha_semanas`) y desglose Lunes-Domingo de la semana en curso.
- **Métricas Globales Equitativas:** Tiempo total activo (horas y minutos este mes y semana), constancia de días entrenados, volumen de fuerza ($kg \times reps$) y series/bloques completados.
- **Salón de Récords Adaptativo (PRs por Disciplina):**
  - Fuerza: 1RM con fórmula de Epley ($1RM = \text{Peso} \times (1 + \text{Reps} / 30)$) y peso máximo en kg.
  - Cardio & Deportes: Mayor duración continua (minutos / horas) para running, ciclismo, pádel, fútbol, yoga, etc.
  - Calistenia & Corporal: Máximas repeticiones en una sola serie para ejercicios con peso corporal.
  - Filtros interactivos reactivos con Alpine.js por categoría (Todos, Fuerza, Cardio/Deportes, Calistenia).
- **Curva de Progresión Universal (Chart.js):** Detecta automáticamente la modalidad del ejercicio (Fuerza en kg, Tiempo en minutos o Calistenia en repeticiones) y adapta los ejes, tooltips y botones de alternancia.
- **Distribución Multidisciplinar:** Gráfico interactivo tipo *doughnut* con alternancia instantánea entre **Por Disciplina** (Fuerza, Cardio, Deportes, Calistenia, Yoga/Danza) y **Por Grupo Muscular**.
- **Recomendador Prioritario:** Recomienda primero la rutina programada para el día actual (`es_programada_hoy`) si está pendiente; si no, aplica rotación por fecha más antigua.

---

## 🛠️ 3. Comandos Esenciales de Terminal

El entorno virtual se encuentra en `.venv`. Comandos ejecutables:

```bash
# Iniciar servidor de desarrollo
.venv/bin/python manage.py runserver

# Aplicar migraciones pendientes
.venv/bin/python manage.py migrate

# Ejecutar la suite completa de pruebas unitarias (100% pasando, 74 tests)
.venv/bin/python manage.py test core.tests users.tests dashboard.tests ejercicios.tests rutinas.tests

# Sincronizar catálogo oficial de ejercicios predeterminados (+52 ejercicios)
.venv/bin/python manage.py poblar_catalogo

# Ejecutar auditoría integral de URLs, plantillas y base de datos
.venv/bin/python manage.py auditar_sistema

# Generar datos de prueba para el Dashboard (todas las cuentas o una específica)
.venv/bin/python manage.py crear_datos_demo
.venv/bin/python manage.py crear_datos_demo --usuario silvia
.venv/bin/python manage.py crear_datos_demo --usuario carlos --limpiar
```

---

## 🎨 4. Convenciones de Frontend, Branding y Estilo

- **Branding Oficial:** **OPTIFIT** (*"Equipamiento para tu mejor versión"*). Recursos en `static/img/logo.png` (logo completo horizontal) y `static/img/logo_icon.png` (emblema de runner para sidebar colapsado y avatares).
- **Modo Oscuro por Defecto:** La plataforma abre en modo oscuro de forma predeterminada mediante comprobación condicional en `<html>` (`class="{% if request.COOKIES.theme != 'light' %}dark{% endif %}"`) y script anti-parpadeo (*Zero-FOUC*) en `<head>`.
- **Sistema Multitema Dinámico (6 Paletas Deportivas):**
  - Controlado por el atributo `[data-theme="..."]` en la raíz `<html>` y variables CSS en `tailwind.config` (`var(--brand-light)` y `var(--brand-dark)`).
  - Paletas disponibles: `lime` (OptiFit Lime Oficial `#84cc16`, por defecto), `cyan` (Cyber Cyan `#06b6d4`), `indigo` (Indigo Power `#6366f1`), `emerald` (Emerald Energy `#10b981`), `amber` (Volcano Amber `#f59e0b`), `crimson` (Crimson Fury `#f43f5e`).
  - Sincronización instantánea mediante eventos personalizados JS (`theme-palette-changed`, `theme-mode-changed`) y persistencia dual en `localStorage` + `cookies`.
- **Selectores de Apariencia:**
  - Pestaña táctil **🎨 Tema & Apariencia** en el perfil de usuario (`/usuario/perfil/?tab=apariencia`) con vista previa en vivo de componentes.
  - Dropdown interactivo de acceso rápido en la cabecera global (`templates/base.html`).
- **Experiencia Móvil PWA & Sensación Nativa:**
  - Web App Manifest completo (`templates/pwa/manifest.json`) con `display: "standalone"`, iconos optimizados (192x192, 512x512, 512x512 maskable, apple-touch-icon 180x180) y accesos directos (Dashboard, Rutinas, Ejercicios, Perfil).
  - **Barra de Navegación Inferior (Bottom Nav):** Componente táctil ergonómico exclusivo para móviles (`md:hidden`) con 5 accesos directos (Inicio, Rutinas, Entrenar central destacado, Ejercicios, Perfil) y respeto por el área segura (*Safe Area Insets* `env(safe-area-inset-bottom)`).
  - **Pantalla Siempre Activa (Screen Wake Lock API):** Modo Gym (`ejecutar_rutina.html`) incorpora conmutador táctil *"💡 Pantalla Activa"* que previene el bloqueo/apagado de pantalla durante series y descansos, con reanudación automática tras `visibilitychange`.
  - **Respuesta Háptica:** Micro-vibraciones táctiles (`navigator.vibrate`) en dispositivos compatibles al confirmar series y al finalizar el temporizador de descanso.
  - **Banner Inteligente de Instalación:** Notificación inferior no invasiva (`pwaMobileBanner`) para navegadores móviles con persistencia en `localStorage` (7 días de gracia al descartar).
  - **Detector de Conectividad en Vivo:** Notificación reactiva inmediata cuando se pierde o restablece la conexión a internet.
  - Soporte de instalación universal para Android/Chrome/Edge y modal paso a paso para iOS Safari.
- **Reactividad Ligera:** **Alpine.js** (`x-data`, `x-show`, `x-bind`, `x-cloak`) para evitar sobrecarga de frameworks SPA pesados.
- **Gráficos:** **Chart.js** con tooltips estilizados y degradados transparentes.
- **Audio:** `AudioContext` sintético del navegador (tonos sinusoidales puros a 440 Hz / 880 Hz) para avisos sonoros sin dependencias de archivos de audio externos.

---

## 🔒 5. Directrices de Seguridad y Buenas Prácticas

1. **Aislamiento por Usuario:** Cualquier consulta a `Rutina`, `RegistroEjercicio`, `Serie` o `Profile` debe filtrar estrictamente por `usuario=request.user`.
2. **Registro No Bloqueante:** Toda auditoría o logging mediante `registrar_log` está encapsulada en `try...except` para garantizar que ningún fallo de telemetría afecte la experiencia del deportista.
3. **Compatibilidad Multiplataforma:** No asumir dispositivos específicos; las interfaces de entrenamiento están optimizadas para pantallas táctiles de móviles (Modo Gym) y pantallas de escritorio (Dashboard y Catálogo).
