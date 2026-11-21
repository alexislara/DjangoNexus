from rest_framework.response import Response

from core.generic_viewset.mixins.base import BaseMixin


class UpdateServicesMixin(BaseMixin):
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop("partial", False)
        serializer = self.serializer_instance(request.data, instance, partial)
        service = self.get_service_class(
            user=request.user,
            action="update",
            instance=instance,
            model=self.get_model(),
        )

        service.action_controller(serializer.validated_data)

        if getattr(instance, "_prefetched_objects_cache", {}):
            cache = getattr(instance, "_prefetched_objects_cache", None)
            if cache:
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)
