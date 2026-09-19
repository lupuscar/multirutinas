#!/bin/bash
set -e

echo "=========================================================="
echo "🚀 INICIANDO DESPLIEGUE DE MULTIRUTINAS EN PRODUCCIÓN"
echo "=========================================================="

# 1. Verificar existencia del archivo de entorno
if [ ! -f ".env" ]; then
    echo "❌ ERROR: No se encontró el archivo .env en el directorio actual."
    echo "💡 Crea tu archivo .env copiando .env.prod.example:"
    echo "   cp .env.prod.example .env"
    echo "   nano .env"
    exit 1
fi

# 2. Descargar últimos cambios del repositorio Git
echo "📥 1/3 Descargando últimos cambios desde Git..."
git pull origin main

# 3. Construir y desplegar contenedores con Docker Compose
echo "🐳 2/3 Reconstruyendo y actualizando contenedores con Docker Compose..."
docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

# 4. Limpieza de imágenes huérfanas
echo "🧹 3/3 Limpiando imágenes residuales antiguas..."
docker image prune -f

echo "=========================================================="
echo "✅ ¡DESPLIEGUE COMPLETADO CON ÉXITO!"
echo "🌐 Comprueba el estado con: docker compose -f docker-compose.prod.yml ps"
echo "📜 Puedes ver los logs con: docker compose -f docker-compose.prod.yml logs -f web"
echo "=========================================================="
