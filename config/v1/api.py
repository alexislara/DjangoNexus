from rest_framework.routers import DefaultRouter

from apps.subscription.viewsets import SubscriptionViewSet, UserInfoViewSet
from apps.test_app.views import AuthorViewSet, LibraryViewSet

router = DefaultRouter()

# Implementación con la capa de abstracción `core`.
router.register("authors", AuthorViewSet, basename="author")
router.register("libraries", LibraryViewSet, basename="library")

# Apps reales.
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("users", UserInfoViewSet, basename="user")

urlpatterns = router.urls
