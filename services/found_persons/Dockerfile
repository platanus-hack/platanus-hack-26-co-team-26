# Imagen de la API de personas localizadas.
# Corre sin privilegios: este contenedor toca datos personales de gente en una
# emergencia y no hay ninguna razón para que lo haga como root.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 helius \
    && mkdir -p /data && chown helius:helius /data
USER helius

# Persistencia fuera de la capa de imagen. Sin volumen montado, los datos se pierden
# al recrear el contenedor — que para una demo es lo correcto.
ENV FOUND_PERSONS_DB=/data/found_persons.db

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8010/health')"

CMD ["uvicorn", "found_persons.bootstrap.main:app", "--host", "0.0.0.0", "--port", "8010"]
