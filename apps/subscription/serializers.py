from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Comment, Subscription

User = get_user_model()


class UserInfoSerializer(serializers.ModelSerializer):
    is_librarian = serializers.SerializerMethodField(default=False)
    is_reader = serializers.SerializerMethodField(default=False)
    email = serializers.CharField(default=None)

    def get_is_librarian(self, obj):
        try:
            return User.objects.get(id=obj.id).is_librarian()
        except AttributeError:
            return User.objects.get(id=obj["id"]).is_librarian()

    def get_is_reader(self, obj):
        try:
            return User.objects.get(id=obj.id).is_reader()
        except AttributeError:
            return User.objects.get(id=obj["id"]).is_reader()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "is_librarian",
            "is_reader",
        ]


class CommentListSerializer(serializers.ModelSerializer):
    user = UserInfoSerializer(read_only=True, default=None)

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "text",
            "created",
        ]


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["subscription", "user", "text"]


class SubscriptionListSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    status = serializers.CharField(source="get_status_display", read_only=True)

    def get_user(self, obj):
        try:
            user = User.objects.get(id=obj.user.id)
            if obj.is_anonymous:
                serializer = UserInfoSerializer(
                    instance={
                        "id": user.id,
                        "first_name": "[ Suscripción ]",
                        "last_name": "Anónimo",
                    },
                    many=False,
                )
            else:
                serializer = UserInfoSerializer(instance=user, many=False)

            return serializer.data
        except (User.DoesNotExist, AttributeError):
            return None

    class Meta:
        model = Subscription
        fields = [
            "id",
            "user",
            "book",
            "author",
            "status",
            "is_renewal",
            "created",
            "is_anonymous",
        ]


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "id",
            "user",
            "book",
            "author",
            "status",
            "is_renewal",
            "is_anonymous",
        ]


class SubscriptionUpdateSerializer(serializers.ModelSerializer):
    comment = serializers.CharField(default=None)

    class Meta:
        model = Subscription
        fields = [
            "is_renewal",
            "status",
            "comment",
        ]
