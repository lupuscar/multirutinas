# 🏋️ Multirutinas (FitApp)

Plataforma web moderna y completa desarrollada con **Django 6** para la planificación deportiva, ejecución de entrenamientos en vivo (**Modo Gym** con cronómetro interactivo), analítica avanzada de fuerza (**1RM** mediante fórmula de Epley), ficha de salud y antropometría (clasificación de **IMC**), y un **sistema integral de auditoría de actividad y captura de excepciones en tiempo real**.

---

## 🌟 Características Principales

### 🏋️ 1. Modo Gym en Vivo
- **Registro ágil de series en tiempo real** mediante llamadas asíncronas (AJAX), sin recargar la página.
- Soporte dual para series de **fuerza (peso + repeticiones)** y series de **resistencia/isometría (tiempo en segundos/minutos)**.
- **Cronómetro de descanso interactivo** con avisos sonoros (audio beep sintetizado) y alertas visuales al finalizar la pausa entre series.

### 📊 2. Dashboard Analítico & Métricas de Rendimiento
- **Rachas de entrenamiento:** Detección algorítmica de semanas consecutivas entrenando y seguimiento diario de la semana en curso (Lunes a Domingo).
- **Tendencias semanales ($\pm\%$):** Comparativa porcentual del volumen total levantado y número de series respecto a la semana anterior.
- **Salón de Récords Personales (PRs):** Cálculo automático del **1RM estimado** para cada ejercicio aplicando la fórmula científica de Epley:
  $$\text{1RM} = \text{Peso} \times \left(1 + \frac{\text{Reps}}{30}\right)$$
- **Recomendador inteligente de rutinas:** Sugiere qué rutina entrenar hoy evaluando el historial de sesiones y rotaciones del usuario.
- **Compartir logros:** Modal con tarjeta de resumen de progreso lista para copiar al portapapeles o exportar/imprimir en PDF.

### 👤 3. Gestión de Usuarios & Perfiles Deportivos
- **Registro libre y autónomo:** Formulario público (`/usuario/registro/`) con inicio de sesión automático y validación de correo único.
- **Ficha de salud y antropometría:** Control de peso, altura, clasificación dinámica de IMC (*Bajo peso*, *Peso saludable*, *Sobrepeso*, *Obesidad*) con insignias de color.
- **Objetivos personalizados:** Hipertrofia, Fuerza, Definición, Resistencia o Salud, con meta de días a entrenar por semana.
- **Recuperación de contraseña segura:** Envío de correos HTML con enlaces de caducidad configurable mediante token (`PASSWORD_RESET_TIMEOUT`).
- **Seguridad en perfil:** Cambio directo de contraseña desde la aplicación manteniendo la sesión activa.
- **Modelo de monetización listo:** Estructura para membresías (`FREE`, `PRO`, `COACH`) y control de fecha de suscripción.

### 🛡️ 4. Auditoría, Detección de Incidencias & Logs
- **Registro de actividad (`LogActividad`):** Almacena usuario, severidad (`INFO`, `WARNING`, `ERROR`, `CRITICAL`), tipo de evento (`LOGIN`, `LOGOUT`, `LOGIN_FAIL`, `REGISTRO`, `PERFIL_EDIT`, `PASSWORD_CHANGE`, `ERROR_500`), método HTTP, URL, IP real del cliente y User-Agent.
- **Middleware de captura de excepciones 500:** Intercepta cualquier fallo inesperado del servidor y guarda automáticamente el traceback técnico completo en base de datos.
- **Panel de control en Django Admin (`/admin/users/logactividad/`):**
  - Badges con código de color según severidad.
  - Filtros avanzados por nivel, evento, método HTTP y jerarquía de fechas.
  - Buscador global por usuario, email, IP, ruta o mensaje.
  - Visor `<pre>` de depuración para consultar trazas de error sin salir del navegador.
  - Integridad garantizada: registros de solo lectura (`has_add_permission = False`).
- **Logs rotativos en disco:** Handlers con rotación automática (`logs/django.log` y `logs/errors.log`, 5 MB máx., 5 respaldos).

---

## 🚀 Tecnologías

| Componente | Tecnología / Librería |
|---|---|
| **Backend** | Python 3.12+ / Django 6.0.7 |
| **Base de Datos** | SQLite (desarrollo) / PostgreSQL compatible |
| **Frontend** | Bootstrap 5, Tailwind CSS utilities, AdminLTE 4 components |
| **Gráficas e Iconos** | FontAwesome 6, Chart.js / SVG dinámicos |
| **Entorno y Configuración** | `python-dotenv`, `asgiref`, `sqlparse`, `Pillow` |

---

## ⚙️ Instalación y Puesta en Marcha

### Opción A: Instalación Automática (Script)

El proyecto incluye un script de configuración desatendido:

```bash
chmod +x setup.sh
./setup.sh
```

---

### Opción B: Instalación Manual Paso a Paso

#### 1. Clonar el repositorio y entrar al proyecto
```bash
git clone https://github.com/lupuscar/multirutinas.git
cd multirutinas
```

#### 2. Crear y activar el entorno virtual
```bash
python3 -m venv .venv
source .venv/bin/activate   # En Linux/macOS
# .venv\Scripts\activate    # En Windows
```

#### 3. Instalar dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configurar las variables de entorno
Copia el archivo de ejemplo y ajusta los valores si lo necesitas:
```bash
cp .env.example .env
```

#### 5. Aplicar migraciones de base de datos
```bash
python manage.py migrate
```

#### 6. Crear un superusuario administrador
```bash
python manage.py createsuperuser
```

#### 7. Cargar datos de prueba (Demo) *(Opcional)*
Para poblar la base de datos con rutinas estructuradas, ejercicios y 16 sesiones de historial con sobrecarga progresiva (+2.5% semanal):
```bash
python manage.py crear_datos_demo
```
*Parámetros opcionales:*
- `--usuario <nombre>`: Asigna los datos a un usuario específico.
- `--limpiar`: Borra rutinas y sesiones previas antes de regenerar.

#### 8. Iniciar el servidor de desarrollo
```bash
python manage.py runserver
```

Abre tu navegador en:
- **Plataforma web:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Panel de administración:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
- **Registro público:** [http://127.0.0.1:8000/usuario/registro/](http://127.0.0.1:8000/usuario/registro/)
- **Auditoría e incidencias:** [http://127.0.0.1:8000/admin/users/logactividad/](http://127.0.0.1:8000/admin/users/logactividad/)

---

## 🔐 Configuración de Variables de Entorno (`.env`)

Ejemplo de configuración disponible en `.env.example`:

```ini
# Clave secreta de Django y modo depuración
SECRET_KEY=tu-clave-secreta-super-segura
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Configuración de Correo Electrónico
# En desarrollo (sin credenciales), los correos se muestran en la consola de Django.
# Para producción, configura tu proveedor SMTP (Brevo, SendGrid, Gmail, Mailgun, etc.):
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=tu-usuario-smtp
EMAIL_HOST_PASSWORD=tu-contraseña-smtp
DEFAULT_FROM_EMAIL=FitApp <no-reply@fitapp.com>

# Caducidad de enlaces de restablecimiento de clave (segundos, por defecto 3600 = 1 hora)
PASSWORD_RESET_TIMEOUT=3600
```

---

## 🧪 Pruebas Unitarias y Validación (Tests)

El proyecto cuenta con una completa suite de pruebas automatizadas con 34 tests unitarios (100% pasando):

```bash
python manage.py test users.tests dashboard.tests ejercicios.tests rutinas.tests
```

**Cobertura de pruebas:**
- **`users.tests`:** Registro libre, unicidad de correo, actualización de perfil antropométrico (peso, altura), cambio seguro de clave, expiración de tokens de reseteo, generación de logs en login/logout, captura de intentos fallidos de autenticación y captura de excepciones 500 por el middleware.
- **`dashboard.tests`:** Control de acceso, métricas a cero en perfiles nuevos, cálculo matemático del 1RM con fórmula de Epley, detección de mejores levantamientos (PRs), recomendación por rotación de descanso y priorización algorítmica de la rutina programada para el día actual.
- **`rutinas.tests`:** Creación y edición interactiva de rutinas, calendarización semanal de días (`dias_semana`), badges dinámicos y "¡Toca hoy!", guardado asíncrono AJAX de series en Modo Gym (fuerza y tiempo) y acciones de administración.
- **`ejercicios.tests`:** Catálogo oficial ampliado con deportes (Pádel), danza contemporánea y actividades al aire libre (Running), formato legible de duraciones en series y detalle con récords.

---

## 📁 Estructura del Proyecto

```text
multirutinas/
├── config/                  # Configuración central (settings, urls, wsgi, asgi)
├── users/                   # Autenticación, perfiles de salud, auditoría y middleware
│   ├── models.py            # Modelos Profile y LogActividad
│   ├── middleware.py        # Captura automática de errores 500
│   ├── signals.py           # Señales de inicio/cierre de sesión y login fallido
│   ├── utils.py             # Registro universal de logs e IP del cliente
│   ├── admin.py             # Panel de auditoría con badges y visor de traceback
│   └── templates/users/     # Vistas de registro, login, perfil y reseteo de clave
├── rutinas/                 # Rutinas, sesiones, series y ejecución en Modo Gym
│   └── management/commands/ # Comando CLI para generar datos demo realistas
├── ejercicios/              # Catálogo oficial y ejercicios personalizados
├── dashboard/               # Analítica, rachas, 1RM, recomendador y compartir logros
├── templates/               # Plantillas base, modales, correos y navbar
├── static/                  # Archivos CSS, JavaScript, imágenes y sonidos
├── logs/                    # Archivos de log rotativos (ignorado en Git)
├── setup.sh                 # Script de instalación automática
├── requirements.txt         # Dependencias Python fijadas
└── manage.py                # Gestor CLI de Django
```

---

## 🔄 Flujo de Trabajo con Git

El proyecto sigue el modelo de ramas:
- `main`: Versión estable en producción.
- `develop`: Rama de integración para desarrollo activo.
- `feature/<nombre>`: Nuevas funcionalidades.
- `bugfix/<nombre>`: Corrección de errores.

Comandos habituales:
```bash
# Obtener últimas actualizaciones
git pull origin main

# Crear una nueva rama de funcionalidad
git checkout -b feature/nueva-mejora

# Confirmar y subir cambios
git add .
git commit -m "feat: descripción del cambio"
git push origin feature/nueva-mejora
```

---

## 👨‍💻 Autor y Licencia

Desarrollado por **Lupuscar**.  
Proyecto de uso personal y formativo.