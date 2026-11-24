import os

from config.settings import *  # noqa: F401,F403

# En desarrollo se mantiene un settings permisivo: cualquier host y CORS
# abierto. Producción (config/settings/production.py) cierra todo esto.
# Si DJANGO_ALLOWED_HOSTS viene definido en el entorno, ese manda.
if not ALLOWED_HOSTS:  # noqa: F405 — importado desde config.settings
    ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("POSTGRES_HOST"),
        "PORT": os.environ.get("POSTGRES_PORT", 5432),
        "NAME": os.environ.get("POSTGRES_DB", "postgres"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
    },
}
