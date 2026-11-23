from typing import Any

from django.db.models import Model

from core.save.base import Save
from core.save.bulk_save import BulkSave


class SingletonMeta(type):
    """Metaclase para implementar el patrón Singleton."""

    def __init__(
        self, name: str, bases: tuple[type, ...], dict: dict[str, Any], /, **kwds: Any
    ) -> None:
        self._instances = {}
        super().__init__(name, bases, dict, **kwds)

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class SaveHandled(Save, BulkSave, metaclass=SingletonMeta):
    def dispach(
        self,
        model_class: type[Model],
        validated_data: dict,
        instance: Model | None = None,
    ) -> Model:
        if not instance:
            instance = self._create(model_class, validated_data)
        else:
            instance = self._update(instance, validated_data)

        return instance

    def bulk_handled(
        self,
        model_class_or_instances: type[Model] | list[Model],
        fields_update: list[str],
        validated_data: list[dict] | None = None,
        batch_size: int = 1000,
        ignore_conflicts: bool = False,
    ):
        if (
            validated_data
            and isinstance(model_class_or_instances, type)
            and issubclass(model_class_or_instances, Model)
        ):
            return self._bulk_create(
                validated_data,
                model_class_or_instances,
                batch_size,
                ignore_conflicts,
            )

        assert isinstance(model_class_or_instances, Model), (
            f"Assert in {self.__class__.__name__}"
            f"Error set model class instance {model_class_or_instances.__class__.__name__}"
        )

        return self._bulk_update(model_class_or_instances, fields_update, batch_size)

    def save(
        self,
        model_class: type[Model],
        validated_data,
        instance: Model | None = None,
    ) -> Model:
        return self.dispach(model_class, validated_data, instance)
