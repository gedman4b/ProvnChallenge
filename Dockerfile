FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

# Runs as a non-root user in the ECS Fargate task, per arrivia's existing
# container baseline.
RUN useradd --create-home --shell /bin/false appuser
USER appuser

EXPOSE 8000

# Liveness probe target for the ALB / ECS task health check — see
# app/api/routes.py::health for why this stays a no-downstream-calls check.
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
