from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    # El slug lo deriva el dominio: lo calcula y escribe el `AuthorService`.
    # El modelo no lo hace por su cuenta -- esa es la diferencia con la app
    # convencional, donde el slug sale de `Model.save()`.
    slug = models.SlugField(max_length=160, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Library(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    slug = models.SlugField(max_length=160, unique=True, null=True, blank=True)
    # `blank=True` porque la base de datos admite una biblioteca sin autores...
    # pero la API no: el `LibraryService` lo impide. Regla de negocio y
    # constraint de base de datos no son lo mismo.
    authors = models.ManyToManyField(Author, related_name="libraries", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
