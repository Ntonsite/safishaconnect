# --- build stage: compile wheels once, keep compilers out of the runtime image -------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# --- runtime stage -------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies change rarely: this layer stays cached across code-only rebuilds.
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* && rm -rf /wheels \
    && useradd --create-home --uid 10001 safisha

COPY --chown=safisha:safisha alembic.ini pyproject.toml docker-entrypoint.sh ./
COPY --chown=safisha:safisha alembic ./alembic
COPY --chown=safisha:safisha app ./app

RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh
USER safisha

EXPOSE 8000
# Readiness of the API (the worker overrides this in docker-compose).
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=6 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4).status == 200 else 1)"

# SIGTERM -> uvicorn stops accepting, drains in-flight requests, runs shutdown hooks.
STOPSIGNAL SIGTERM
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["serve"]
