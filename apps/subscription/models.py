from uuid import uuid4 as uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel

User = get_user_model()


class BaseModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid, editable=False)

    class Meta:
        abstract = True


class Subscription(BaseModel):
    """Suscripción de un lector a un libro de la biblioteca.

    Es el equivalente del "reporte" del proyecto de origen, llevado al
    contexto de una biblioteca: un lector pide un libro, la biblioteca lo
    presta y el lector lo devuelve.
    """

    class Status(models.TextChoices):
        REQUESTED = "R", _("Solicitada")
        IN_LOAN = "IL", _("En préstamo")
        RETURNED = "RT", _("Devuelta")

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, related_name="subscriptions"
    )
    book = models.CharField(max_length=255, null=False)
    author = models.CharField(max_length=150, blank=True, default="")
    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    # Una renovación es un segundo préstamo del mismo libro, sin esperar a que
    # el primero termine.
    is_renewal = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)


class Comment(BaseModel):
    """Comentario de un lector sobre una suscripción."""

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    text = models.CharField(max_length=255, null=False)
