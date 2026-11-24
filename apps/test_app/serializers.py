from rest_framework import serializers

from .models import Author


class AuthorSerializer(serializers.Serializer):
    """Serializer plano: describe el contrato de la API y nada más.

    `core` trabaja sobre el dict de `validated_data`, así que el serializer no
    necesita saber nada del modelo. Las reglas de negocio (normalizar, email
    único, slug) viven en `AuthorService`.
    """

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    # El cliente nunca manda el slug: lo deriva el dominio.
    slug = serializers.SlugField(max_length=160, read_only=True)


class LibrarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=150)
    address = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=160, read_only=True)
    authors = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Author.objects.all(),
        required=False,
    )
