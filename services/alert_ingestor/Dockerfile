# Worker de ingesta de alertas sísmicas. Sin puerto expuesto: no tiene superficie
# HTTP propia (docs/architecture/OVERVIEW.md §11).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 sismomesh
USER sismomesh

CMD ["python", "-m", "alert_ingestor.bootstrap.main"]
