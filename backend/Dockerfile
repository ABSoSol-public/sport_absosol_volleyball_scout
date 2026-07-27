FROM python:3.13-slim

WORKDIR /srv/app

COPY pyproject.toml ./
COPY app app
COPY alembic alembic
COPY alembic.ini docker-entrypoint.sh ./

RUN pip install --no-cache-dir . && chmod +x docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
