# ==========================================================
# 🐍 Backend Django - Optimizado con uv
# ==========================================================

# ---- Base ----
FROM python:3.12-slim AS base

ARG APP_USER=django
ARG SRC_DIR=/usr/src/app
ARG VENV_DIR=/opt/venv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    PATH="${VENV_DIR}/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gettext \
    bash \
    curl \
    && groupadd --system --gid 1000 ${APP_USER} \
    && useradd --system --uid 1000 --gid 1000 --home ${SRC_DIR} --shell /bin/bash ${APP_USER} \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${SRC_DIR}
EXPOSE 8000

# ---- Builder: compila dependencias ----
FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && uv venv ${VENV_DIR}

COPY pyproject.toml ./
RUN uv pip install --python ${VENV_DIR}/bin/python .

# ---- Builder de desarrollo: añade las dependencias de desarrollo ----
# La imagen de producción no debe arrastrar Faker, coverage, markdown ni ruff.
FROM builder AS builder-dev

COPY pyproject.toml ./
RUN uv pip install --python ${VENV_DIR}/bin/python .[dev]

# ---- Development ----
FROM base AS development

COPY --from=builder-dev ${VENV_DIR} ${VENV_DIR}
COPY --chown=1000:1000 . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown ${APP_USER}:${APP_USER} /entrypoint.sh

USER ${APP_USER}
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---- Production ----
FROM base AS production

COPY --from=builder ${VENV_DIR} ${VENV_DIR}
COPY --chown=1000:1000 . .
COPY entrypoint.sh /entrypoint.sh

# FIX 1: Darle la propiedad de toda la carpeta raíz al usuario django
RUN chown -R ${APP_USER}:${APP_USER} ${SRC_DIR} && \
    chmod +x /entrypoint.sh && \
    chown ${APP_USER}:${APP_USER} /entrypoint.sh

USER ${APP_USER}

# Setup steps (collectstatic, OIDC keygen, migrations, fixtures, superuser)
# are NOT executed at build time. They live in entrypoint.sh and are gated by
# per-step env vars (RUN_OIDC_KEYGEN, RUN_COLLECTSTATIC, RUN_MIGRATIONS,
# RUN_FIXTURES, RUN_SUPERUSER), each defaulting to "false". Cloud Run deploy
# sets the ones it needs and flips them off after the one-time bootstrap.

ENV DJANGO_SETTINGS_MODULE=config.settings.production
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]

# FIX 2: Agregar --worker-tmp-dir /dev/shm
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --worker-tmp-dir /dev/shm --max-requests 1000 --max-requests-jitter 100 --limit-request-field_size 32768 --timeout 120"]