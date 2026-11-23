from rest_framework.viewsets import GenericViewSet

from core.generic_viewset.validates import ValidatesAtributes


class GenericViewsetService(GenericViewSet, ValidatesAtributes):

    def get_service_class(self, *args, **kwargs):
        assert self.services_class is not None, (
            f"'{self.__class__.__name__}' should either include a `services_class` attribute, "
            "or override the `get_service_class()` method."
        )
        return self.services_class(*args, **kwargs)

    def get_serializer_class(self):
        serializer_class = self.serializer_class_object.get(
            self.action, self.serializer_class_default
        )
        assert serializer_class is not None, (
            f"'{self.__class__.__name__}' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
        )

        return serializer_class

    def dispatch(self, request, *args, **kwargs):
        # validate execute methods
        self.validations_execute()
        return super().dispatch(request, *args, **kwargs)
