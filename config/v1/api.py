from rest_framework.routers import DefaultRouter

from apps.test_app.views import AuthorViewSet, LibraryViewSet

router = DefaultRouter()
router.register("authors", AuthorViewSet, basename="author")
router.register("libraries", LibraryViewSet, basename="library")

urlpatterns = router.urls
