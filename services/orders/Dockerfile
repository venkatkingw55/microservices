# Build from the repository root:
#   docker build -f services/orders/Dockerfile -t orders:dev .
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY services/__init__.py /app/services/__init__.py
COPY services/platformhttp /app/services/platformhttp
COPY services/orders/__init__.py services/orders/__main__.py services/orders/handlers.py /app/services/orders/

USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["python", "-m", "services.orders"]
