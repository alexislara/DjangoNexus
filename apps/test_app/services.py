"""Lógica de negocio de la app `test_app` (implementación con la capa `core`).

Acá vive **todo** el dominio. Los viewsets de `apps/test_app/views.py` sólo
orquestan (validar → delegar → responder) y los services son objetos
normales: se pueden ejecutar y testear sin una petición HTTP.
"""

import logging

from django.utils.text import slugify
from rest_framework.exceptions import ValidationError
from rest_framework.utils import model_meta

from core.services import ServiceGenerics

logger = logging.getLogger(__name__)


def clean_text(value: str) -> str:
    """Recorta los bordes y colapsa los espacios internos.

    >>> clean_text("  Ana   Pérez  ")
    'Ana Pérez'
    """
    return " ".join(value.split())


def build_unique_slug(model, value: str, exclude_pk=None) -> str:
    """Devuelve un slug único derivado de `value`.

    Si el slug ya existe le agrega un sufijo numérico: ``ana``, ``ana-2``...
    `exclude_pk` sirve para regenerar el slug de un objeto sin que choque con
    el propio registro.
    """
    base = slugify(value) or "sin-nombre"
    queryset = model.objects.all()
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)

    slug = base
    counter = 2
    while queryset.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1

    return slug


def reflect(instance, validated_data: dict) -> dict:
    """Deja el payload sincronizado con lo que quedó persistido.

    La capa `core` arma la respuesta a partir del dict del payload (no desde
    la instancia), así que el service devuelve ese dict ya completo: de ahí
    salen el `id` y el `slug` autogenerado, que el cliente nunca manda.

    También devuelve las relaciones *many-to-many*: `Save._create` las saca
    del payload antes de escribir (no son argumentos válidos de
    `Model.objects.create()`) y sin esto la respuesta las perdería.
    """
    info = model_meta.get_field_info(instance.__class__)

    # `fields_and_pk` incluye la clave primaria; `fields` no.
    for field_name in info.fields_and_pk:
        if field_name == "pk":
            continue
        validated_data[field_name] = getattr(instance, field_name)

    # Sólo las relaciones *hacia adelante*: las inversas (los `libraries` de un
    # autor) no son parte del payload de este recurso.
    for field_name, relation in info.forward_relations.items():
        if relation.to_many:
            validated_data[field_name] = getattr(instance, field_name).all()

    return validated_data


class AuthorService(ServiceGenerics):
    """Reglas de negocio del autor."""

    def create(self, validated_data):
        data = self._prepare(validated_data, creating=True)
        instance = self.handler.save(self.model_class, data)
        reflect(instance, data)

        logger.info("Autor creado: %s (id=%s)", instance, instance.pk)
        return data

    def update(self, validated_data):
        data = self._prepare(validated_data, creating=False)
        instance = self.handler.save(self.model_class, data, instance=self.instance)
        reflect(instance, data)

        logger.info("Autor actualizado: %s (id=%s)", instance, instance.pk)
        return data

    # --- reglas de negocio ---

    def _prepare(self, validated_data, creating):
        if "name" in validated_data:
            validated_data["name"] = clean_text(validated_data["name"])
            # El serializer de DRF ya rechaza los nombres en blanco cuando la
            # petición viene por HTTP; esta comprobación cubre el caso de que
            # el service se llame directo (un command, el admin, otro service).
            if not validated_data["name"]:
                raise ValidationError({"name": ["El nombre no puede estar vacío."]})

        if "email" in validated_data:
            validated_data["email"] = clean_text(validated_data["email"]).lower()
            self._assert_email_is_free(validated_data["email"])

        # El slug lo deriva el dominio: el cliente no lo manda.
        if creating or "name" in validated_data:
            validated_data["slug"] = build_unique_slug(
                self.model_class,
                self._current_name(validated_data),
                exclude_pk=self._current_pk(),
            )

        return validated_data

    def _current_name(self, validated_data):
        if "name" in validated_data:
            return validated_data["name"]
        return getattr(self.instance, "name", "")

    def _current_pk(self):
        """La clave del objeto que se está actualizando (`None` al crear)."""
        return self.instance.pk if self.instance is not None else None

    def _assert_email_is_free(self, email):
        # La base de datos igual lo va a rechazar por `unique=True`, pero con
        # un error 500. Acá se corta antes, con un 400 y un mensaje de dominio.
        queryset = self.model_class.objects.filter(email=email)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError({"email": ["Este email ya está registrado."]})


class LibraryService(ServiceGenerics):
    """Reglas de negocio de la biblioteca."""

    def create(self, validated_data):
        data = self._prepare(validated_data, creating=True)
        instance = self.handler.save(self.model_class, data)
        reflect(instance, data)

        logger.info("Biblioteca creada: %s (id=%s)", instance, instance.pk)
        return data

    def update(self, validated_data):
        data = self._prepare(validated_data, creating=False)
        instance = self.handler.save(self.model_class, data, instance=self.instance)
        reflect(instance, data)

        logger.info("Biblioteca actualizada: %s (id=%s)", instance, instance.pk)
        return data

    # --- reglas de negocio ---

    def _prepare(self, validated_data, creating):
        if "name" in validated_data:
            validated_data["name"] = clean_text(validated_data["name"])
            if not validated_data["name"]:
                raise ValidationError({"name": ["El nombre no puede estar vacío."]})

        if "address" in validated_data:
            validated_data["address"] = clean_text(validated_data["address"])

        if creating or "name" in validated_data:
            validated_data["slug"] = build_unique_slug(
                self.model_class,
                self._current_name(validated_data),
                exclude_pk=self._current_pk(),
            )

        # Una biblioteca sin autores no es una biblioteca: es un depósito de
        # libros huérfanos. El dominio no lo permite.
        self._assert_has_authors(validated_data, creating)

        return validated_data

    def _current_name(self, validated_data):
        if "name" in validated_data:
            return validated_data["name"]
        return getattr(self.instance, "name", "")

    def _current_pk(self):
        """La clave del objeto que se está actualizando (`None` al crear)."""
        return self.instance.pk if self.instance is not None else None

    def _assert_has_authors(self, validated_data, creating):
        if "authors" not in validated_data:
            # En una actualización no manda `authors`: la biblioteca conserva
            # los que ya tenía.
            if creating:
                raise ValidationError({"authors": ["La biblioteca debe tener al menos un autor."]})
            return

        if not validated_data["authors"]:
            raise ValidationError({"authors": ["La biblioteca debe tener al menos un autor."]})
