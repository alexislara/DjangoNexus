import traceback

from rest_framework.utils import model_meta


class Save:
    def get_many_to_many_fields(self, validated_data, model):
        info = model_meta.get_field_info(model)
        many_to_many = {}
        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the model has already been saved.

        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        return many_to_many

    def save_many_to_many(self, model, many_to_many):
        # Save many-to-many relationships after the model is created or update.
        if many_to_many:
            for field_name, value in many_to_many.items():
                field = getattr(model, field_name)
                field.set(value)

        return model

    def _create(self, model, validated_data):
        many_to_many = self.get_many_to_many_fields(validated_data, model)

        try:
            instance = model._default_manager.create(**validated_data)
        except TypeError as err:
            tb = traceback.format_exc()
            msg = (
                f"Got a `TypeError` when calling `{model.__name__}.{model._default_manager.name}.create()`. "
                f"This may be because you have a writable field on the "
                f"serializer class that is not a valid argument to "
                f"`{model.__name__}.{model._default_manager.name}.create()`. You may need to make the field "
                f"read-only, or override the {self.__class__.__name__}.create() method to handle "
                f"this correctly.\nOriginal exception was:\n {tb}"
            )
            raise TypeError(msg) from err

        self.save_many_to_many(instance, many_to_many)
        return instance

    def _update(self, model, validated_data):
        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an model pk for the relationships to be associated with.

        many_to_many = self.get_many_to_many_fields(validated_data, model)

        for attr, value in validated_data.items():
            setattr(model, attr, value)

        model.save()
        self.save_many_to_many(model, many_to_many)

        return model
