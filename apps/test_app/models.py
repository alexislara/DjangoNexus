from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Library(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    authors = models.ManyToManyField(Author, related_name="libraries", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
