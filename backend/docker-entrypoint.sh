#!/bin/sh
set -e

# Auf die Datenbank warten (Compose-Healthcheck deckt den Normalfall ab,
# die Schleife fängt Neustarts/Race-Conditions ab)
tries=0
until python -c "
from sqlalchemy import create_engine, text
from app.core.config import get_settings
engine = create_engine(get_settings().database_url)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
" 2>/dev/null; do
    tries=$((tries + 1))
    if [ "$tries" -ge 30 ]; then
        echo "Datenbank nicht erreichbar — Abbruch." >&2
        exit 1
    fi
    echo "Warte auf Datenbank … ($tries)"
    sleep 2
done

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
