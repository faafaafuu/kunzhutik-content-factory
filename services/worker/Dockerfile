FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/api/requirements.txt /app/requirements.txt
COPY packages/shared /app/packages/shared
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/api /app/services/api
COPY services/worker /app/services/worker
ENV PYTHONPATH=/app/services/api:/app/packages/shared/src

WORKDIR /app/services/worker

CMD ["celery", "-A", "app.worker_tasks:celery_app", "worker", "--loglevel=INFO"]
