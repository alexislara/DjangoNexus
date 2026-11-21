from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import api_settings

from core.generic_viewset.mixins.base import BaseMixin


class CreateServicesMixin(BaseMixin):
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_instance(data=request.data)
        service = self.get_service_class(
            instance=None, user=request.user, action=self.action, model=self.get_model()
        )
        service.action_controller(serializer.validated_data)
        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def get_success_headers(self, data):
        try:
            return {"Location": str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}
