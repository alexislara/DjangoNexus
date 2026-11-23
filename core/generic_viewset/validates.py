import logging
from typing import Protocol

from core.generic_viewset.exceptions import (
    ServiceIsNone,
)

logger = logging.getLogger(__name__)


class GenericViewsetServiceAbstract(Protocol):
    queryset = None
    services_class = None
    serializer_class = None
    serializer_class_default = None
    serializer_class_object = {}


class ValidatesAtributes(GenericViewsetServiceAbstract):
    def get_attribute_validate(self):
        # Get validation attributes in viewset and filter attributes start with validation
        validations = filter(
            lambda x: x.startswith("validate_"), dir(self)
        )
        return list(validations)

    def validations_execute(self):
        # item validation atributes in viewset and execute method validation
        logging.debug("Validations_execute in GenericViewSetServices")
        validations = self.get_attribute_validate()
        [getattr(self, validation)() for validation in validations]

    def validate_queryset(self):
        assert self.queryset is not None, (
            f"'{self.__class__.__name__}' should either include a `queryset` attribute, "
            "or override the `get_queryset()` method."
        )

    def validate_serializer_class_default(self):
        assert (
            self.serializer_class_default is not None
        ), f"{self.__class__.__name__}, Attribute expected serializer_class_default is None"

    def validate_service_class(self):
        if not self.services_class:
            raise ServiceIsNone(
                f"'{self.__class__.__name__}' should either include a `services_class` attribute, "
                "or override the `get_services_class()` method."
            )
