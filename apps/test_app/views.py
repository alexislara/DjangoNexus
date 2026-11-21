from rest_framework.mixins import (
    ListModelMixin,
    RetrieveModelMixin,
)

from core.generic_viewset.base import GenericViewsetService
from core.generic_viewset.mixins.create import CreateServicesMixin
from core.generic_viewset.mixins.update import UpdateServicesMixin

from .models import Author, Library
from .serializers import AuthorSerializer, LibrarySerializer
from .services import AuthorService, LibraryService


class AuthorViewSet(
    GenericViewsetService,
    ListModelMixin,
    RetrieveModelMixin,
    CreateServicesMixin,
    UpdateServicesMixin,
):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    services_class = AuthorService


class LibraryViewSet(
    GenericViewsetService,
    ListModelMixin,
    RetrieveModelMixin,
    CreateServicesMixin,
    UpdateServicesMixin,
):
    queryset = Library.objects.prefetch_related("authors")
    serializer_class = LibrarySerializer
    services_class = LibraryService
