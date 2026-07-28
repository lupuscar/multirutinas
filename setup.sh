#!/bin/bash
#chmod +x setup.sh
#./setup.sh
# Salir inmediatamente si ocurre algún error
set -e

echo "🚀 Iniciando la configuración de Multirutinas..."

# 1. Crear carpeta de proyectos e ingresar
mkdir -p ~/proyectos
cd ~/proyectos

# 2. Clonar el repositorio si no existe aún
if [ ! -d "multirutinas" ]; then
    echo "📦 Clonando repositorio..."
    git clone https://github.com/lupuscar/multirutinas
fi

cd multirutinas

# 3. Crear el entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "🐍 Creando entorno virtual..."
    python3 -m venv .venv
fi

# 4. Activar el entorno virtual
echo "🔌 Activando entorno virtual..."
source .venv/bin/activate

# 5. Configurar archivo de variables de entorno (.env)
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "⚙️ Creando archivo .env a partir de .env.example..."
    cp .env.example .env
    echo "⚠️ RECUERDA: Revisa y edita el archivo .env si necesitas cambiar credenciales/claves."
fi

# 6. Instalar dependencias
echo "📥 Instalando dependencias desde requirements.txt..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Por si acaso Pillow no estaba en el requirements.txt original
pip install Pillow

# 7. Crear carpeta de estáticos si no existe
mkdir -p static

# 8. Migraciones de Django
echo "🗄️ Aplicando migraciones de Base de Datos..."
python manage.py makemigrations
python manage.py migrate

# 9. Recopilar archivos estáticos
echo "📂 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

# 10. Crear superusuario (Opcional/Interactivo)
read -p "❓ ¿Deseas crear un superusuario para Django ahora? (s/n): " respuesta
if [[ "$respuesta" =~ ^[Ss]$ ]]; then
    python manage.py createsuperuser
fi

echo "✅ ¡Todo listo! Iniciando el servidor de desarrollo..."
echo "🌐 Abre tu navegador en: http://127.0.0.1:8000/"

# 11. Arrancar el servidor
python manage.py runserver
