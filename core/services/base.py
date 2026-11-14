from abc import abstractmethod
from typing import Protocol

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from django.db.models import Model


class ServiceBase(Protocol):
    @abstractmethod
    def create(self, validated_data: dict) -> dict:
        pass

    @abstractmethod
    def update(self, validated_data: dict) -> dict:
        pass

    def save(self):
        pass


class Service(ServiceBase):
    def __init__(self, user: AbstractBaseUser, instance: Model, action: str) -> None:
        self.user = user
        self.action = action

    @transaction.atomic
    def action_controller(self, validated_data):
        method = getattr(self, self.action)
        return method(validated_data)


class ServiceGenerics(Service):
    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, validated_data: dict):
        return super().update(validated_data)
