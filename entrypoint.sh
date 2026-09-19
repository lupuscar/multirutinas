#!/bin/sh
set -e

# Esperar a PostgreSQL si se han especificado variables de conexión
if [ -n "$POSTGRES_HOST" ]; then
    echo "⏳ Esperando a que PostgreSQL ($POSTGRES_HOST:${POSTGRES_PORT:-5432}) esté listo..."
    while ! python -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('$POSTGRES_HOST', int('${POSTGRES_PORT:-5432}')))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
        sleep 1
    done
    echo "✅ Conexión con PostgreSQL establecida."
fi

# Aplicar migraciones pendientes automáticamente
echo "🗄️ Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

# Recopilar archivos estáticos
echo "📂 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

# Ejecutar el comando principal (por defecto Gunicorn)
exec "$@"
