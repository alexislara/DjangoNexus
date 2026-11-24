# `django-base`

Base de **Django 6.1** + **Django REST Framework** con la capa de abstracción
`core`, que reemplaza el CRUD repetitivo por una cadena de responsabilidades
explícita:

```
Vista (ViewSet)  →  Mixin  →  Service  →  Save handler  →  Modelo Django
```

La documentación de la capa `core` está en [`core/README.md`](core/README.md).
Este README explica **cómo levantar el servidor** y qué hace cada variable de
entorno.

---

## 1. Requisitos

| Herramienta | Versión | Notas |
|---|---|---|
| Python | 3.12+ | `.python-version` fija la versión del proyecto |
| [uv](https://docs.astral.sh/uv/) | 0.13+ | Gestor de entorno y dependencias |
| Docker + Compose | v2+ | Sólo para la Opción C |

Instalación de `uv` (si no lo tenés):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. Puesta en marcha

### Opción A — Local con SQLite (la más rápida, cero dependencias)

No necesita Postgres, ni `.env`, ni Docker. `manage.py` usa por defecto el
módulo `config.settings`, que apunta a SQLite (`config/db.sqlite3`).

```bash
uv sync                              # crea .venv e instala dependencias
uv run python manage.py migrate      # crea las tablas
uv run python manage.py runserver    # http://127.0.0.1:8000/
```

Para probarlo:

```bash
curl http://127.0.0.1:8000/v1/authors/
curl http://127.0.0.1:8000/v1/libraries/
```

> Con esta opción **no se lee el `.env`**: sin `--env-file`, el archivo queda
> afuera y se usan los defaults de `config.settings`.

### Opción B — Local con Postgres, usando el `.env`

Postgres en Docker, la app corriendo en la máquina (con autoreload):

```bash
# 1. Levantar Postgres con el puerto publicado
docker run -d --name django-base-db \
  -e POSTGRES_DB=db-base \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD="tu-password" \
  -p 5432:5432 postgres:17

# 2. Preparar el .env
cp .env.example .env
```

Editá `.env` y poné **`POSTGRES_HOST=localhost`** (no `db-base`, que es el nombre
de red de Docker), junto con la password que usaste arriba:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=db-base
POSTGRES_USER=postgres
POSTGRES_PASSWORD="tu-password"
```

```bash
# 3. Migrar y levantar, pasando el .env explícitamente
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py runserver
```

> `uv run --env-file .env` es **necesario**: el proyecto no tiene `python-dotenv`
> ni `django-environ`, así que Django solo no lee el `.env`.
> Si definís la variable en la shell, tiene prioridad sobre el archivo:
> `DJANGO_SETTINGS_MODULE=config.settings uv run --env-file .env ...`

### Opción C — Todo en Docker Compose

```bash
cp .env.example .env
# editá .env: DJANGO_SECRET_KEY, POSTGRES_PASSWORD, credenciales de MinIO, etc.

# La red del compose es externa: hay que crearla una sola vez
docker network create reverse-proxy-net

docker compose up --build
```

El servicio `django` publica el puerto `8000`:

```bash
curl http://127.0.0.1:8000/v1/authors/
```

Notas:

- `docker-compose.yml` extiende `docker-compose.base.yml`; el archivo base
  define la imagen y las variables, el derivado agrega el mapeo de puertos.
- Docker Compose **lee el `.env` del directorio del proyecto automáticamente**
  y lo usa para completar las variables declaradas sin valor en `environment:`.
  No hace falta exportarlas a mano.
- El código del proyecto está montado (`.:/usr/src/app`), así que los cambios
  se reflejan sin reconstruir la imagen.

Para parar y limpiar:

```bash
docker compose down            # conserva el volumen de Postgres
docker compose down -v         # borra también el volumen postgres_data
```

---

## 3. Variables de entorno

El archivo `.env` real **no se versiona** (está en `.gitignore`); lo que se
versiona es la plantilla `.env.example`. Para empezar:

```bash
cp .env.example .env
```

Generá una `DJANGO_SECRET_KEY` nueva con:

```bash
uv run python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

### Referencia

| Variable | Default en `.env.example` | Default si no está definida | Quién la consume |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | placeholder | clave de desarrollo hardcodeada | Django |
| `DJANGO_SETTINGS_MODULE` | `config.settings.local` | `config.settings` (vía `manage.py`) | Django |
| `DJANGO_ENV` | `development` | `development` | Django |
| `DJANGO_DEBUG` | `True` | `True` | Django |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | `[]` → `["*"]` en `config.settings.local` | Django |
| `DJANGO_PERMISSION_ENABLED` | `True` | — | stack de permisos (aún no implementado) |
| `POSTGRES_HOST` / `_PORT` / `_DB` / `_USER` / `_PASSWORD` | ver `.env.example` | `None` (socket local) / `5432` / `postgres` / `postgres` / `None` | `config.settings.local` |
| `MINIO_STORAGE_*`, `STATICFILES_STORAGE`, `DEFAULT_FILE_STORAGE` | ver `.env.example` | — | declaradas, sin código que las lea todavía |
| `EMAIL_*` | ver `.env.example` | — | declaradas, sin código que las lea todavía |
| `RABBITMQ_DEFAULT_*`, `WORKER_MQ_URL` | ver `.env.example` | — | declaradas, sin código que las lea todavía |
| `FRONTEND_URL` | `http://localhost:3000` | — | declarada, sin código que la lea todavía |
| `DJANGO_OAUTH2_*`, `OIDC_ISS_ENDPOINT` | ver `.env.example` | — | declaradas, sin código que las lea todavía |
| `DJANGO_ADMIN_EMAIL` | `admin@example.com` | `admin@noreplay.com` | `entrypoint.sh` |
| `DJANGO_ADMIN_PASSWORD` | placeholder | — | la leería `ensure_admin_user` (ver *Pendientes*) |
| `RUN_MIGRATIONS`, `RUN_COLLECTSTATIC`, `RUN_OIDC_KEYGEN`, `RUN_FIXTURES`, `RUN_SUPERUSER`, `RUN_LTH_USERS` | `false` | `false` | `entrypoint.sh` |

### Qué se lee hoy y qué no

Vale la pena ser explícito, porque no todo lo que está en `.env.example` está
implementado todavía:

**Se leen de verdad hoy**

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` y `DJANGO_ENV`
  → `config/settings/__init__.py`.
- `POSTGRES_*` → `config/settings/local.py`.

**Todavía no lo lee nadie**

- `MINIO_STORAGE_*`, `EMAIL_*`, `RABBITMQ_DEFAULT_*`, `WORKER_MQ_URL`,
  `FRONTEND_URL`, `DJANGO_OAUTH2_*`, `OIDC_ISS_ENDPOINT` y
  `DJANGO_PERMISSION_ENABLED`: están declaradas para los módulos de settings
  que faltan (ver *Pendientes*) y para el `entrypoint.sh`, pero ningún módulo
  Python las consulta hoy.

**Ojo con CORS**: `config/settings/local.py` define
`CORS_ALLOW_ALL_ORIGINS = True`, pero `django-cors-headers` no está en
`pyproject.toml` ni en `INSTALLED_APPS`, así que **CORS no está activo**. Para
habilitarlo hay que instalar el paquete y sumarlo a `INSTALLED_APPS` y a
`MIDDLEWARE`.

---

## 4. Comandos habituales

```bash
# Entorno
uv sync                          # instalar dependencias
uv run --env-file .env <cmd>      # ejecutar un comando con el .env cargado

# Django
uv run python manage.py migrate
uv run python manage.py makemigrations
uv run python manage.py createsuperuser
uv run python manage.py shell
uv run python manage.py check

# Tests
uv run python manage.py test apps

# Servidor
uv run python manage.py runserver                  # 127.0.0.1:8000
uv run python manage.py runserver 0.0.0.0:8000     # accesible desde la red

# Linting
uv run ruff check .
uv run ruff format .
```

`manage.py check` no revisa la configuración de despliegue. Para eso:

```bash
uv run --env-file .env python manage.py check --deploy
```

Entre otras cosas, avisa si `SECRET_KEY` sigue siendo el de desarrollo
(`security.W009`) o si `ALLOWED_HOSTS` quedó vacío con `DEBUG=False`
(`security.W020`, que rompe **todas** las peticiones con un `DisallowedHost`).

### Endpoints disponibles

| Ruta | Qué es |
|---|---|
| `/v1/authors/` | CRUD de `Author` — ejemplo con la capa `core` |
| `/v1/libraries/` | CRUD de `Library` — ejemplo con la capa `core` |
| `/v1/subscriptions/` | CRUD de `Subscription` |
| `/v1/users/` | datos del usuario de la petición |
| `/v1/` | raíz de la API (DefaultRouter) |
| `/admin/` | panel de administración de Django |
| `/api-authz/login/` | login de la browsable API de DRF (`/logout/` sólo acepta POST) |

---

## 5. Estructura

```
.
├── apps/
│   ├── test_app/           # ejemplo funcional de integración con `core`
│   └── subscription/       # ejemplo de app real (Subscription, Comment)
├── config/
│   ├── settings/
│   │   ├── __init__.py     # settings base (lee DJANGO_* del entorno)
│   │   └── local.py        # desarrollo: Postgres, ALLOWED_HOSTS permisivo
│   ├── v1/api.py           # rutas del router
│   └── urls.py
├── core/                   # capa de abstracción sobre DRF (ver core/README.md)
├── .env.example            # plantilla de variables (versionada)
├── Dockerfile              # targets: development, production
├── docker-compose.yml      # stack de desarrollo (extiende docker-compose.base.yml)
├── docker-compose.base.yml # definición compartida de servicios y variables
├── entrypoint.sh           # pasos de bootstrap, activados por flags RUN_*
└── manage.py
```

---

---

## 6. Pendientes conocidos

Cosas que el código y la infraestructura referencian pero que **todavía no
existen** en el repo. No bloquean el arranque en desarrollo, pero conviene
saberlo:

1. **`config/settings/production.py` no existe.** El target `production` del
   `Dockerfile` exporta `DJANGO_SETTINGS_MODULE=config.settings.production`:
   esa imagen no arranca hasta que el módulo exista.
2. **No hay endpoint `/health/`.** El `HEALTHCHECK` del `Dockerfile` consulta
   `http://localhost:8000/health/`, que devuelve 404 y marca el contenedor como
   *unhealthy*.
3. **Faltan los comandos `ensure_admin_user` y `load_lth_legacy_users`.**
   `entrypoint.sh` los invoca con `RUN_SUPERUSER=true` / `RUN_LTH_USERS=true`;
   hoy fallan en silencio (el entrypoint los envuelve con `|| warn`).
4. **La red `reverse-proxy-net` es externa.** Hay que crearla a mano
   (`docker network create reverse-proxy-net`) antes del primer `docker compose up`.
5. **`config.settings` (SQLite) es el default de `manage.py`.** Si dejás
   `DJANGO_SETTINGS_MODULE=config.settings.local` en el `.env` sin levantar
   Postgres, el server arranca pero toda consulta a la base falla.
6. **`config.settings` no define `ALLOWED_HOSTS`.** Combinado con
   `DJANGO_DEBUG=False` (que sí trae el `.env` por defecto), Django responde
   `DisallowedHost` a **todas** las peticiones. Para esa combinación hay que
   setear `DJANGO_ALLOWED_HOSTS`, o usar `config.settings.local`, que tiene el
   fallback `["*"]`.
7. **`.gitignore` no está versionado.** El propio `.gitignore` se ignora a sí
   mismo (línea `.gitignore`), así que en un clon nuevo no existe y nada
   impide commitear un `.env` con secretos por accidente. Conviene agregarlo al
   repo con `git add -f .gitignore`.

---

## 7. Checklists

### Antes de un deploy

- [ ] `DJANGO_SECRET_KEY` generado y único por entorno (no el de `.env.example`).
- [ ] `DJANGO_DEBUG=False`.
- [ ] `DJANGO_ALLOWED_HOSTS` con los dominios reales (no `*`). Con `DEBUG=False`
      y `ALLOWED_HOSTS` vacío, Django rechaza **todas** las peticiones.
- [ ] `uv run --env-file .env python manage.py check --deploy` sin errores.
- [ ] `DJANGO_SETTINGS_MODULE=config.settings.production` (requiere el módulo, ver *Pendientes*).
- [ ] Passwords de Postgres, MinIO y OAuth2 rotados y fuera del repo.
- [ ] `config/settings/production.py` creado: sin `ALLOWED_HOSTS=["*"]`, sin
      `CORS_ALLOW_ALL_ORIGINS`, con `SECRET_KEY` viniendo del entorno.
- [ ] `/health/` implementado si el orquestador usa el `HEALTHCHECK`.

### Al empezar un proyecto nuevo con esta base

1. `cp .env.example .env` y completar los valores.
2. `uv sync`.
3. `uv run python manage.py migrate`.
4. Reemplazar `apps/test_app` por la app del dominio.
5. Levantar con `uv run --env-file .env python manage.py runserver`.
