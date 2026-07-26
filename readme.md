# Multirutinas

Aplicación web desarrollada con **Django** para la gestión de rutinas, usuarios y administración mediante **AdminLTE 4**.

## 🚀 Tecnologías

- Python 3.12+
- Django 5.2 (preparado para Django 6)
- AdminLTE 4
- Bootstrap 5
- SQLite (desarrollo)
- Git + GitHub
- WSL2 + Ubuntu
- Visual Studio Code

## 📁 Estructura del proyecto

```
multirutinas/
├── apps/
├── config/
├── static/
├── templates/
├── media/
├── .env
├── .env.example
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

## ⚙️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/lupuscar/multirutinas.git
cd multirutinas
```

### 2. Crear el entorno virtual

```bash
python3 -m venv .venv
```

### 3. Activarlo

Linux / WSL

```bash
source .venv/bin/activate
# 3. Instalar Django
pip install --upgrade pip
pip install django

```
### 4. Instalar dependencias

```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser


```

### 5. Configurar variables de entorno

Copiar el archivo de ejemplo:

```bash
cp .env.example .env
```

Editar el archivo `.env` con los valores correspondientes.

### 6. Aplicar migraciones

```bash
python manage.py migrate
```

### 7. Crear un superusuario

```bash
python manage.py createsuperuser
```

### 8. Ejecutar el servidor

```bash
python manage.py runserver
```

Abrir:

```
http://127.0.0.1:8000
```

Panel de administración:

```
http://127.0.0.1:8000/admin/
```

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