FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STORAGE_LOCAL_PATH=/data/storage

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install .
COPY alembic.ini ./
COPY migrations ./migrations

# O volume montado em /data/storage herda o dono desta pasta na primeira montagem.
RUN useradd --create-home --uid 10001 nexus \
    && mkdir -p /data/storage \
    && chown nexus /data/storage
USER nexus

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
