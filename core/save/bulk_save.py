from collections.abc import Sequence

from django.db.models import Model


class BulkSave:
    def _bulk_create(
        self,
        validated_data: list[dict],
        instance: type[Model],
        batch_size: int = 1000,
        ignore_conflicts: bool = False,
    ) -> list[Model]:
        # Convertimos la lista de diccionarios en una lista de objetos en memoria
        objects_to_create = [instance(**item) for item in validated_data]

        # Ejecutamos el bulk_create nativo de Django
        created_objects = instance._default_manager.bulk_create(
            objects_to_create, batch_size=batch_size, ignore_conflicts=ignore_conflicts
        )

        return created_objects

    def _bulk_update(
        self,
        instance: Model | Sequence[Model],
        fields: list[str],
        batch_size: int = 1000,
    ) -> int:
        """
        Realiza una actualización masiva (bulk_update) en la base de datos para una
        o múltiples instancias de un modelo de Django.

        :param instance: Una instancia individual o una lista/QuerySet de instancias del mismo modelo.
        :param fields: Lista con los nombres de los campos que se van a actualizar en la BD.
        :param batch_size: Cantidad de objetos a actualizar por cada consulta SQL (por defecto 1000).
        :return: Número de instancias procesadas.
        """
        # Si se pasa una sola instancia, la convertimos en lista
        if isinstance(instance, Model):
            instances = [instance]
        else:
            instances = list(instance)

        if not instances or not fields:
            return 0

        # Obtenemos la clase del modelo a partir del primer objeto
        model_class = instances[0].__class__

        # Ejecutamos el bulk_update nativo de Django
        updated_count = model_class._default_manager.bulk_update(
            instances, fields=fields, batch_size=batch_size
        )

        return updated_count
