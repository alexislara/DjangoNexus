from core.generic_viewset.exceptions import (
    SerializerIsNone,
    ServiceIsNone,
)


class GenericViewsetServiceAbstract:
    services_class = None
    serializer_class = None

    def __init__(self) -> None:
        self.serializer_class_object = {}


class Validates(GenericViewsetServiceAbstract):
    def get_attr_validate(self):
        # Get validation attributes in viewset and filter attributes start with validation
        get_attributes_validations = filter(lambda x: x.startswith("validate_"), dir(self))
        return list(get_attributes_validations)

    def validate_execute(self):
        # item validation atributes in viewset and execute method validation
        return [
            attr
            for attr in dir(self)
            if attr.startswith("validate_") and callable(getattr(self, attr)())
        ]


    def validate_serializer_class(self):
        if self.serializer_class:
            raise SerializerIsNone(
                f"'{self.__class__.__name__}' should either include a `serializer_class` attribute, "
                "or override the `get_serializer_class()` method."
            )

    def validate_service_class(self):
        if not self.services_class:
            raise ServiceIsNone(
                f"'{self.__class__.__name__}' should either include a `services_class` attribute, "
                "or override the `get_services_class()` method."
            )
