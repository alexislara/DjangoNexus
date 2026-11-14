from rest_framework.viewsets import GenericViewSet

from core.generic_viewset.validates import Validates


class GenericViewsetService(GenericViewSet, Validates):
    services_class = None
    serializer_class_object = {}

    def set_queryset(self, queryset):
        assert queryset is not None, (
            f"'{self.__class__.__name__}' should either include a `queryset` attribute, "
            "or override the `get_queryset()` method."
        )

        return queryset

    def get_service_class(self, *args, **kwargs):
        assert self.services_class is not None, (
            f"'{self.__class__.__name__}' should either include a `services_class` attribute, "
            "or override the `get_service_class()` method."
        )
        return self.services_class(*args, **kwargs)

    def get_serializer_class(self):
        serializer_class = self.serializer_class_object.get(
            self.action, self.serializer_class
        )

        assert serializer_class is not None, (
            f"'{self.__class__.__name__}' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
        )
        return serializer_class

    def dispatch(self, request, *args, **kwargs):
        # validate execute methods
        self.get_attr_validate()
        return super().dispatch(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        return super().initial(request, *args, **kwargs)
