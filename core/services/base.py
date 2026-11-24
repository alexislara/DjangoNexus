from abc import abstractmethod
from typing import Protocol

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.db.models import Model

from core.save.handled import SaveHandled

save_handler = SaveHandled()


class ServiceBase(Protocol):
    @abstractmethod
    def create(self, validated_data: dict) -> dict:
        pass

    @abstractmethod
    def update(self, validated_data: dict) -> dict:
        pass


class Service(ServiceBase):
    def __init__(
        self,
        user: AbstractBaseUser | None,
        instance: Model | None,
        action: str,
        model: type[Model],
    ) -> None:
        self.user = user
        self.action = action
        self.instance = instance
        self.model_class = model
        self._save_handler = save_handler

    @property
    def handler(self) -> SaveHandled:
        return self._save_handler

    @transaction.atomic
    def action_controller(self, validated_data):
        method = getattr(self, self.action)
        return method(validated_data)


class ServiceGenerics(Service):
    def create(self, validated_data):
        self.handler.save(self.model_class, validated_data)
        return validated_data

    def update(self, validated_data):
        self.handler.save(
            self.model_class,
            validated_data,
            instance=self.instance,
        )
        return validated_data
