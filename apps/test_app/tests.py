"""Tests de la app `test_app` (implementación con la capa `core`).

Dos cosas se verifican acá:

1. Las **reglas de negocio por HTTP**, tal como las ve el cliente.
2. Los **services** por separado, sin HTTP. Es una de las razones de existir
   de la capa de servicios: la regla de negocio se puede testear sin levantar
   una petición.
"""

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from .models import Author, Library
from .services import AuthorService, LibraryService


class AuthorAPITests(TestCase):
    """Las reglas del autor, vistas desde la API."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def create_author(self, **payload):
        return self.client.post("/v1/authors/", payload, format="json")

    def test_crea_el_autor_normalizando_nombre_y_email(self):
        response = self.create_author(name="  Ana   Pérez ", email="  ANA@Example.COM ")

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["name"], "Ana Pérez")
        self.assertEqual(body["email"], "ana@example.com")
        self.assertEqual(body["slug"], "ana-perez")
        self.assertIn("id", body)

    def test_rechaza_el_email_duplicado(self):
        first = self.create_author(name="Ana", email="ana@example.com")
        self.assertEqual(first.status_code, 201, first.content)

        second = self.create_author(name="Otra", email="ana@example.com")

        self.assertEqual(second.status_code, 400, second.content)
        self.assertEqual(second.json(), {"email": ["Este email ya está registrado."]})

    def test_genera_slugs_unicos_para_nombres_repetidos(self):
        first = self.create_author(name="Ana", email="ana1@example.com")
        second = self.create_author(name="Ana", email="ana2@example.com")

        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(first.json()["slug"], "ana")
        self.assertEqual(second.json()["slug"], "ana-2")

    def test_rechaza_el_nombre_vacio(self):
        response = self.create_author(name="   ", email="vacia@example.com")

        # El mensaje es de DRF, no del dominio: se verifica la clave, no el texto.
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("name", response.json())

    def test_actualizar_el_nombre_regenera_el_slug(self):
        author = self.create_author(name="Ana", email="ana@example.com")
        self.assertEqual(author.status_code, 201, author.content)

        response = self.client.patch(
            f"/v1/authors/{author.json()['id']}/", {"name": "Ana María"}, format="json"
        )

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["name"], "Ana María")
        self.assertEqual(body["slug"], "ana-maria")
        self.assertEqual(body["email"], "ana@example.com")

    def test_actualizar_el_email_lo_deja_en_minusculas(self):
        author = self.create_author(name="Ana", email="ana@example.com")
        self.assertEqual(author.status_code, 201, author.content)

        response = self.client.patch(
            f"/v1/authors/{author.json()['id']}/",
            {"email": "  ANA@EXAMPLE.COM "},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["email"], "ana@example.com")


class LibraryAPITests(TestCase):
    """Las reglas de la biblioteca, vistas desde la API."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def create_author(self, name="Ana", email="ana@example.com"):
        response = self.client.post(
            "/v1/authors/", {"name": name, "email": email}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def create_library(self, **payload):
        return self.client.post("/v1/libraries/", payload, format="json")

    def test_la_biblioteca_necesita_al_menos_un_autor(self):
        response = self.create_library(name="Central", address="Calle 1")

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(
            response.json(),
            {"authors": ["La biblioteca debe tener al menos un autor."]},
        )

    def test_rechaza_una_lista_de_autores_vacia(self):
        response = self.create_library(name="Central", address="Calle 1", authors=[])

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(
            response.json(),
            {"authors": ["La biblioteca debe tener al menos un autor."]},
        )

    def test_crea_la_biblioteca_normalizando_y_con_sus_autores(self):
        author = self.create_author()

        response = self.create_library(
            name="  Biblioteca  Central ",
            address="  Calle 1  ",
            authors=[author["id"]],
        )

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["name"], "Biblioteca Central")
        self.assertEqual(body["address"], "Calle 1")
        self.assertEqual(body["slug"], "biblioteca-central")
        self.assertEqual(body["authors"], [author["id"]])
        self.assertIn("id", body)

    def test_no_se_puede_dejar_la_biblioteca_sin_autores(self):
        author = self.create_author()

        created = self.create_library(
            name="Central", address="Calle 1", authors=[author["id"]]
        )
        self.assertEqual(created.status_code, 201, created.content)

        response = self.client.patch(
            f"/v1/libraries/{created.json()['id']}/",
            {"authors": []},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(
            response.json(),
            {"authors": ["La biblioteca debe tener al menos un autor."]},
        )


class AuthorServiceTests(TestCase):
    """La lógica de negocio del autor, sin pasar por el HTTP."""

    def build_service(self, instance=None):
        return AuthorService(user=None, instance=instance, action="create", model=Author)

    def test_normaliza_el_nombre_y_el_email(self):
        service = self.build_service()

        data = service.create({"name": "  Ana   Pérez ", "email": "  ANA@X.COM "})

        self.assertEqual(data["name"], "Ana Pérez")
        self.assertEqual(data["email"], "ana@x.com")

    def test_genera_el_slug_y_lo_devuelve_en_el_payload(self):
        service = self.build_service()

        data = service.create({"name": "Ana Pérez", "email": "ana@x.com"})

        self.assertEqual(data["slug"], "ana-perez")
        # El service devuelve el payload ya sincronizado con la base: el `id`
        # también viene de ahí.
        self.assertEqual(data["id"], Author.objects.get(email="ana@x.com").pk)

    def test_rechaza_un_email_ya_registrado(self):
        Author.objects.create(name="Ana", email="ana@x.com")
        service = self.build_service()

        with self.assertRaises(ValidationError) as ctx:
            service.create({"name": "Otra", "email": "ana@x.com"})

        self.assertEqual(
            ctx.exception.detail, {"email": ["Este email ya está registrado."]}
        )

    def test_permite_guardar_el_mismo_email_del_autor_que_se_actualiza(self):
        author = Author.objects.create(name="Ana", email="ana@x.com")
        service = AuthorService(user=None, instance=author, action="update", model=Author)

        data = service.update({"email": "ana@x.com"})

        self.assertEqual(data["email"], "ana@x.com")


class LibraryServiceTests(TestCase):
    """La lógica de negocio de la biblioteca, sin pasar por el HTTP."""

    def test_rechaza_crear_una_biblioteca_sin_autores(self):
        service = LibraryService(user=None, instance=None, action="create", model=Library)

        with self.assertRaises(ValidationError) as ctx:
            service.create({"name": "Central", "address": "Calle 1"})

        self.assertEqual(
            ctx.exception.detail,
            {"authors": ["La biblioteca debe tener al menos un autor."]},
        )

    def test_rechaza_dejar_la_biblioteca_sin_autores(self):
        author = Author.objects.create(name="Ana", email="ana@x.com")
        library = Library.objects.create(name="Central", address="Calle 1")
        library.authors.add(author)

        service = LibraryService(user=None, instance=library, action="update", model=Library)

        with self.assertRaises(ValidationError) as ctx:
            service.update({"authors": []})

        self.assertEqual(
            ctx.exception.detail,
            {"authors": ["La biblioteca debe tener al menos un autor."]},
        )
