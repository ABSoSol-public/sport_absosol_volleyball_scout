#!/bin/sh
# Benutzer anlegen bzw. Passwort zurücksetzen (Muster wie im yugioh_database-Projekt).
#
#   ./create-user.sh <username> <passwort> [admin|viewer]
#
# Läuft bevorzugt im Backend-Container (docker compose / docker-compose),
# alternativ über die lokale venv gegen die in .env konfigurierte DB.
set -e

if [ $# -lt 2 ]; then
    echo "Aufruf: $0 <username> <passwort> [admin|viewer]" >&2
    exit 1
fi

cd "$(dirname "$0")"

if docker compose ps backend 2>/dev/null | grep -q backend; then
    exec docker compose exec -T backend python -m app.cli create-user "$@"
elif [ -x /usr/local/bin/docker-compose ] && sudo /usr/local/bin/docker-compose ps backend 2>/dev/null | grep -q backend; then
    exec sudo /usr/local/bin/docker-compose exec -T backend python -m app.cli create-user "$@"
elif [ -x backend/.venv/bin/python ]; then
    exec backend/.venv/bin/python -m app.cli create-user "$@"
else
    echo "Weder laufender Backend-Container noch backend/.venv gefunden." >&2
    exit 1
fi
