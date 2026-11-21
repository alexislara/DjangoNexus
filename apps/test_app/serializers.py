from rest_framework import serializers

from .models import Author


class AuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()


class LibrarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=150)
    address = serializers.CharField(max_length=255)
    authors = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Author.objects.all(),
        required=False,
    )
