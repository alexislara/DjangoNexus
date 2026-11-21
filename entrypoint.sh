#!/bin/sh
set -e

OIDC_KEY_FILE="/usr/src/app/oidc.key"

# Each bootstrap step is gated by its own env var, defaulting to "false".
# Set the specific flag(s) to "true" to opt in to that step at container start.
#
#   RUN_OIDC_KEYGEN    — generate the OIDC RSA signing key if missing
#   RUN_COLLECTSTATIC  — run `manage.py collectstatic`
#   RUN_MIGRATIONS     — run `manage.py migrate`
#   RUN_FIXTURES       — run `manage.py loaddata fixtures/*.json`
#   RUN_SUPERUSER      — create the DJANGO_ADMIN_* superuser if missing
#   RUN_LTH_USERS      — load legacy LTH/Clarios users from
#                        fixtures/users-lth-legacy.json via the
#                        `load_lth_legacy_users` management command
#
# With all flags false (the default), the entrypoint execs the CMD directly.
# Cloud Run cold starts benefit from leaving every flag false after the
# one-time bootstrap revision has run.
RUN_OIDC_KEYGEN="${RUN_OIDC_KEYGEN:-false}"
RUN_COLLECTSTATIC="${RUN_COLLECTSTATIC:-false}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-false}"
RUN_FIXTURES="${RUN_FIXTURES:-false}"
RUN_SUPERUSER="${RUN_SUPERUSER:-false}"
RUN_LTH_USERS="${RUN_LTH_USERS:-false}"

# Ensure app directory is writable by django user (only when running setup).
# On fast cold starts (all flags false) we skip this and trust the image build.
if [ "$RUN_OIDC_KEYGEN" = "true" ] || [ "$RUN_COLLECTSTATIC" = "true" ] || \
   [ "$RUN_MIGRATIONS" = "true" ] || [ "$RUN_FIXTURES" = "true" ] || \
   [ "$RUN_SUPERUSER" = "true" ] || [ "$RUN_LTH_USERS" = "true" ]; then
    chown -R 1000:1000 /usr/src/app 2>/dev/null || true
fi

log() { echo "[INFO] $1"; }
warn() { echo "[WARN] $1" >&2; }

generate_oidc_key() {
    if [ -f "$OIDC_KEY_FILE" ]; then
        log "OIDC key already exists, skipping generation..."
        return 0
    fi

    log "Generating OIDC RSA private key..."
    if python -c "
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import os

key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
pem = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)
os.makedirs(os.path.dirname('$OIDC_KEY_FILE'), exist_ok=True)
with open('$OIDC_KEY_FILE', 'wb') as f:
    f.write(pem)
print('OIDC key generated successfully')
"; then
        log "OIDC key generated successfully"
    else
        warn "OIDC key generation failed, continuing anyway..."
    fi
}

run_migrations() {
    log "Running Django migrations..."
    local retries=5
    local count=0
    while [ $count -lt $retries ]; do
        if python manage.py migrate --noinput; then
            return 0
        fi
        count=$((count + 1))
        log "Migration attempt $count failed, retrying in 5s..."
        sleep 5
    done
    warn "Migrations failed after $retries attempts, continuing anyway..."
}

load_fixtures() {
    log "Loading data fixtures..."
    local retries=3
    local count=0
    while [ $count -lt $retries ]; do
        if python manage.py loaddata fixtures/*.json; then
            return 0
        fi
        count=$((count + 1))
        log "Loaddata attempt $count failed, retrying in 3s..."
        sleep 3
    done
    warn "Loaddata failed after $retries attempts, continuing anyway..."
}

create_superuser() {
    DJANGO_ADMIN_EMAIL="${DJANGO_ADMIN_EMAIL:-admin@noreplay.com}"
    export DJANGO_ADMIN_EMAIL

    # El password NO se interpola en el código: se lee del entorno. Antes se
    # embebía en un `python -c` y cualquier comilla o backslash lo rompía
    # con SyntaxError; el error se silenciaba con un `|| warn` y el deploy
    # terminaba en verde sin superuser.
    #
    # El comando se corre siempre, aunque falte el password: así el log del
    # arranque dice siempre en qué estado está la cuenta de bootstrap. Antes,
    # sin secret, el paso se saltaba en silencio y no había ni superuser ni
    # rastro de por qué.
    log "Ensuring admin superuser exists and is in sync..."
    DJANGO_SETTINGS_MODULE_VALUE="${DJANGO_SETTINGS_MODULE:-config.settings.staging}"
    DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE_VALUE" \
        python manage.py ensure_admin_user \
        || warn "ensure_admin_user failed, continuing anyway..."
}

collect_static() {
    log "Collecting static files..."
    local retries=3
    local count=0
    while [ $count -lt $retries ]; do
        if python manage.py collectstatic --noinput; then
            return 0
        fi
        count=$((count + 1))
        log "Collectstatic attempt $count failed, retrying in 3s..."
        sleep 3
    done
    warn "Collectstatic failed after $retries attempts, continuing anyway..."
}

load_lth_users() {
    log "Loading legacy LTH/Clarios users from users-lth-legacy.json..."
    if [ ! -f "fixtures/users-lth-legacy.json" ]; then
        warn "fixtures/users-lth-legacy.json not found, skipping"
        return 0
    fi
    # Idempotente: si el usuario ya existe, actualiza sus datos importados
    # sin modificar su password.
    python manage.py load_lth_legacy_users \
        || warn "load_lth_legacy_users failed, continuing anyway..."
}

main() {
    # Each step runs only if its specific flag is true. With all flags false
    # (the default), the entrypoint logs once and execs directly.
    local any_step=false
    [ "$RUN_OIDC_KEYGEN" = "true" ] && { any_step=true; generate_oidc_key; }
    [ "$RUN_COLLECTSTATIC" = "true" ] && { any_step=true; collect_static; }
    [ "$RUN_MIGRATIONS" = "true" ] && { any_step=true; run_migrations; }
    [ "$RUN_FIXTURES" = "true" ] && { any_step=true; load_fixtures; }
    [ "$RUN_SUPERUSER" = "true" ] && { any_step=true; create_superuser; }
    [ "$RUN_LTH_USERS" = "true" ] && { any_step=true; load_lth_users; }

    if [ "$any_step" = "false" ]; then
        log "All RUN_* flags are false, exec CMD directly (fast cold start)"
    fi

    if [ "$#" -gt 0 ]; then
        log "Executing command: $*"
        exec "$@"
    fi
}

main "$@"