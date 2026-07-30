#!/bin/bash

# 1. Detener el script inmediatamente si algún comando falla
set -e

echo "🔄 Comprobando el estado de Git..."
git status 

echo "⬇️ Descargando últimos cambios..."
git pull

# 2. Activar entorno virtual (Recomendado)
# Cambia 'venv' por el nombre de tu carpeta si es distinto
# source venv/bin/activate

echo "🗄️ Aplicando migraciones de Base de Datos..."
# OJO: Si esto es un servidor real, borra o comenta la siguiente línea de makemigrations.
python manage.py makemigrations
python manage.py migrate

echo "📂 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

echo "✅ ¡Todo listo! Iniciando el servidor..."
echo "🌐 Abre tu navegador en: http://127.0.0.1:8000/"

# 3. Arrancar el servidor
python manage.py runserver