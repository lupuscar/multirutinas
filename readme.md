# Multirutinas

Aplicación web desarrollada con **Django** para la gestión de rutinas, usuarios y administración mediante **AdminLTE 4**.

## 🚀 Tecnologías

- Python 3.12+
- Django 6
- Bootstrap 5
- SQLite (desarrollo)
- Git + GitHub
- WSL2 + Ubuntu
- Visual Studio Code


## ⚙️ Instalación
```bash

chmod +x setup.sh
./setup.sh

```
### 5. Configurar variables de entorno

Copiar el archivo de ejemplo:

```bash
cp .env.example .env
```

Editar el archivo `.env` con los valores correspondientes.


Abrir:

http://127.0.0.1:8000


Panel de administración:

```
http://127.0.0.1:8000/admin/
```

### 6. Cargar datos de prueba (Demo)

Para ver el Dashboard y las rutinas con gráficas de fuerza, volumen y estadísticas reales:

```bash
python manage.py crear_datos_demo
```
*(Opcional: `--usuario carlos` para un usuario específico, o `--limpiar` para regenerarlos).*

---

## 📦 Dependencias

Actualizar:

```bash
pip freeze > requirements.txt
```

Instalar:

```bash
pip install -r requirements.txt
```

---

## 🔄 Flujo de trabajo con Git

Obtener cambios:

```bash
git pull
```

Añadir archivos:

```bash
git add .
```

Crear commit:

```bash
git commit -m "Descripción del cambio"
```

Subir cambios:

```bash
git push
```

---

## 🌿 Ramas

- `main` → versión estable
- `develop` → integración
- `feature/*` → nuevas funcionalidades
- `bugfix/*` → correcciones

Ejemplo:

```bash
git checkout -b feature/login
```

---

## 🔐 Variables de entorno

Ejemplo de `.env`

```text
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Configuración de Email (SMTP para producción / consola en desarrollo)
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=FitApp <no-reply@fitapp.com>

# Caducidad de enlaces de recuperación de contraseña (segundos, por defecto 3600 = 1 hora)
PASSWORD_RESET_TIMEOUT=3600
```


---

## 📂 Archivos ignorados

El proyecto ignora automáticamente:

- `.venv`
- `.env`
- `__pycache__`
- `db.sqlite3`
- `media/`
- `.vscode`

---

## 👨‍💻 Autor

**Lupuscar**

---

## 📄 Licencia

Proyecto de uso personal.