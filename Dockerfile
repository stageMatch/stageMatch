FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/database_files \
    && chown appuser:appuser /app/database_files

COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 5000

# Un solo worker: la coda di matching (matching/worker.py) vive in memoria nel
# processo, quindi più worker avrebbero code separate. La concorrenza si ottiene coi thread.
# Il servizio `api` (geo-proxy) sovrascrive il comando in docker-compose.yml.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "60", "app:app"]
