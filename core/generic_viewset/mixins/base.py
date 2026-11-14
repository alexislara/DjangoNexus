from abc import abstractmethod
from typing import Any, Protocol

from django.db.models import Model
from rest_framework.serializers import Serializer

from core.services import Service


class BaseServiceMixin(Protocol):
    @abstractmethod
    def get_object(self) -> Any:
        pass

    @abstractmethod
    def get_service_class(self, *args, **kwargs) -> Service:
        pass

    @abstractmethod
    def get_serializer(self, *args, **kwargs) -> Serializer:
        pass


class BaseMixin(BaseServiceMixin):
    def __init__(self) -> None:
        self.action=None

    def serializer_data(
        self, data: dict, instance: type[Model] | None = None, partial: bool = True
    ):
        serializer = self.get_serializer(instance=instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)

        return serializer
