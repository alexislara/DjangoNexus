from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from .models import Comment, Subscription
from .serializers import (
    CommentCreateSerializer,
    CommentListSerializer,
    SubscriptionCreateSerializer,
    SubscriptionListSerializer,
    SubscriptionUpdateSerializer,
    UserInfoSerializer,
)

User = get_user_model()


class SubscriptionViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Subscription.objects.all()
    search_fields = ["user__first_name", "user__last_name"]
    filterset_fields = ["status", "is_anonymous"]

    def get_serializer_class(self):
        if self.action in ["create"]:
            return SubscriptionCreateSerializer

        elif self.action in ["update", "partial_update"]:
            return SubscriptionUpdateSerializer

        return SubscriptionListSerializer

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-is_renewal", "created")
        try:
            if self.request.user.is_librarian():
                return queryset.all()

            elif self.request.user.is_reader():
                return queryset.filter(user=self.request.user)

            return queryset.exclude().all()
        except AttributeError:
            return queryset.exclude().all()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        data.update({"user": request.user.id})

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        serializer_data = serializer.data.copy()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer_data, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop("partial", False)
        data = request.data

        try:
            if data["comment"] is not None:
                comment = {
                    "user": request.user.id,
                    "subscription": instance.id,
                    "text": data["comment"],
                }
                comment_serializer = CommentCreateSerializer(data=comment)
                comment_serializer.is_valid(raise_exception=True)
                comment_serializer.save()
        except KeyError:
            pass

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(data)

    @action(methods=["GET"], detail=True)
    def get_comments(self, request, *args, **kwargs):
        comments = Comment.objects.filter(subscription=kwargs["pk"]).order_by("created")
        serializer = CommentListSerializer(comments, many=True)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UserInfoViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = UserInfoSerializer

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)
