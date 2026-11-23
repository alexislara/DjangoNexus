# `core`

Paquete base del proyecto. Es una **capa de abstracción sobre Django REST Framework**
que elimina el CRUD repetitivo de cada app y concentra el flujo completo en una
cadena de responsabilidades clara:

```
Vista (ViewSet)  →  Mixin  →  Service  →  Save handler  →  Modelo Django
```

`core` no reemplaza a Django ni a DRF: los envuelve y les agrega las piezas que
en la práctica se terminan reescribiendo en **cada** proyecto — validaciones
de configuración, capa de servicios con transacciones, persistencia con soporte
de relaciones *many-to-many* y operaciones masivas.

---

## 1. El problema que resuelve

### 1.1 El CRUD repetitivo

Un viewset "normal" de DRF termina siempre con la misma forma:

```python
class AuthorViewSet(ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
```

Y cada endpoint nuevo agrega el mismo bloque de *wiring*: instanciar el servicio,
pasarle el usuario, envolverlo en una transacción, validarlo y devolver el
serializer. Con `core` ese bloque ya existe y solo se declara.

### 1.2 Lógica de negocio mezclada con la capa HTTP

Cuando la lógica vive en el viewset, no se puede reutilizar (ni testear) fuera de
una petición HTTP. `core` introduce una **capa de servicios** explícita: el
viewset solo orquesta (validar → delegar → responder) y el servicio contiene la
regla de negocio.

### 1.3 Errores de configuración silenciosos

Un viewset sin `queryset`, sin serializer o sin servicio fallaba tarde y con
mensajes confusos (`serializer_class` de DRF es `None` por defecto, y el valor
del framework se mezclaba con el del usuario). `core` valida **antes** de
procesar la petición y falla con un mensaje que dice exactamente qué falta.

### 1.4 Fallos recurrentes al escribir

| Problema | Cómo lo resuelve `core` |
|---|---|
| `serializer_class` de DRF chocaba con el default del framework | Se renombró a `serializer_class_default`; el dict por acción es `serializer_class_object` |
| La validación de serializer tenía la lógica **invertida** (lanzaba error cuando el serializer *sí* estaba) | `validate_serializer_class_default` verifica correctamente que no sea `None` |
| Los validadores no se ejecutaban de forma explícita (se disparaban de forma colateral dentro de una *list comprehension* y el resultado se descartaba) | `validations_execute()` los invoca explícitamente y en orden |
| Las relaciones *many-to-many* en `create()` lanzaban `TypeError` | `Save._create()` las extrae, crea el objeto y recién ahí las asigna |
| El estado *many-to-many* vivía en `self` del `SaveHandled`, que es un **Singleton** compartido por todos los threads | Pasó a variable local por llamada |
| Múltiples escrituras sin atomicidad | `Service.action_controller()` envuelve todo en `@transaction.atomic` |
| Inserciones y actualizaciones masivas escritas a mano | `SaveHandled.bulk_handled()` (`bulk_create` / `bulk_update`) |

---

## 2. Estructura

```
core/
├── generic_viewset/       # Capa HTTP: viewset base, validaciones y mixins
│   ├── base.py            #   GenericViewsetService
│   ├── validates.py       #   ValidatesAtributes (convención validate_*)
│   ├── exceptions.py      #   SerializerIsNone, ServiceIsNone
│   └── mixins/            #   BaseMixin, CreateServicesMixin, UpdateServicesMixin
├── services/              # Capa de negocio (Service, ServiceGenerics)
└── save/                  # Capa de persistencia (Save, BulkSave, SaveHandled)
```

---

## 3. `core/generic_viewset`

### `GenericViewsetService` — `base.py`

Viewset base. Hereda de `GenericViewSet` (DRF) y de `ValidatesAtributes`.

| Atributo que espera el viewset | Para qué sirve |
|---|---|
| `queryset` | Fuente de datos. Requerido. |
| `serializer_class_default` | Serializer por defecto para todas las acciones. Requerido. |
| `serializer_class_object` | Dict `{acción: serializer}` para usar un serializer distinto por endpoint. Opcional. |
| `services_class` | Clase de servicio a instanciar. Requerido. |

Métodos:

- `get_service_class(*args, **kwargs)` — instancia `services_class`.
- `get_serializer_class()` — resuelve `serializer_class_object.get(self.action, self.serializer_class_default)`.
- `dispatch()` — ejecuta `validations_execute()` **antes** de delegar en DRF.

### `ValidatesAtributes` — `validates.py`

Implementa el patrón *convention over configuration*: **todo método que empiece
por `validate_` se ejecuta automáticamente** en cada petición, antes del handler.

Validadores incluidos de fábrica:

| Validador | Comprueba |
|---|---|
| `validate_queryset` | Que `queryset` no sea `None` |
| `validate_serializer_class_default` | Que `serializer_class_default` no sea `None` |
| `validate_service_class` | Que `services_class` esté definido (lanza `ServiceIsNone`) |

Los validadores propios del viewset se suman solos:

```python
class AuthorViewSet(GenericViewsetService, ...):
    def validate_serializer_class_object(self):
        for action in self.serializer_class_object:
            assert hasattr(self, action), (
                f"'{action}' está en serializer_class_object pero no existe en el viewset."
            )
```

> **Importante:** las validaciones corren en `dispatch()`, antes de que DRF
> resuelva la acción ni envuelva la petición. Durante el `validate_*`:
>
> - `self.action` **todavía no existe**.
> - `self.request` es el `WSGIRequest` crudo de Django, no el `Request` de DRF:
>   no tiene `.data` ni `.query_params`.
>
> Si necesitás validar el payload, hacelo en el serializer. Si necesitás la
> acción, hacelo en el servicio.

### Mixins — `mixins/`

`BaseMixin` aporta las utilidades compartidas:

- `get_model()` — devuelve el modelo a partir del `queryset`.
- `serializer_instance(data, instance=None, partial=True)` — construye el
  serializer, lo valida (`is_valid(raise_exception=True)`) y lo devuelve.

`CreateServicesMixin.create()`:

1. Valida el payload con el serializer.
2. Instancia el servicio con `instance=None`, `action=self.action` (`"create"`).
3. Ejecuta `service.action_controller(serializer.validated_data)`.
4. Responde `201 Created` con el header `Location` cuando el serializer expone el `id`.

`UpdateServicesMixin.update()` / `partial_update()`:

1. Resuelve la instancia con `get_object()`.
2. Valida el payload (respeta `partial`).
3. Instancia el servicio con `action="update"`.
4. Invalida `_prefetched_objects_cache` si el queryset traía `prefetch_related`.
5. Responde `200 OK`.

---

## 4. `core/services`

Capa de negocio. Cada servicio recibe el contexto de la petición y expone un
método por acción.

```python
class Service(ServiceBase):
    def __init__(self, user, instance, action, model): ...

    @transaction.atomic
    def action_controller(self, validated_data):
        method = getattr(self, self.action)
        return method(validated_data)
```

- `user` — el usuario autenticado de la petición.
- `instance` — la instancia afectada (`None` en `create`).
- `action` — el nombre de la acción; `action_controller` hace el despacho.
- `model` — la clase del modelo.

`ServiceGenerics` trae las implementaciones por defecto de `create` y `update`,
que delegan la escritura en el save handler.

Ejemplo con regla de negocio:

```python
class AuthorService(ServiceGenerics):
    def create(self, validated_data):
        validated_data["created_by"] = self.user
        return super().create(validated_data)
```

---

## 5. `core/save`

Capa de persistencia.

- **`Save`** — `_create()` y `_update()`. Extrae las relaciones *many-to-many*
  antes de escribir (no son argumentos válidos de `Model.objects.create()`),
  escribe el objeto y recién después asigna las relaciones.
- **`BulkSave`** — `_bulk_create()` y `_bulk_update()` sobre los `bulk_create` /
  `bulk_update` nativos de Django, con `batch_size` e `ignore_conflicts`.
- **`SaveHandled`** — une ambas cosas y es un **Singleton** (`SingletonMeta`),
  de modo que hay una única instancia compartida por toda la aplicación.

API pública:

```python
from core.save import SaveHandled

handler = SaveHandled()  # siempre la misma instancia

handler.save(Model, validated_data)  # create
handler.save(Model, validated_data, instance=obj)  # update
handler.bulk_handled(Model, [], validated_data=[{...}, {...}])  # bulk_create
handler.bulk_handled(obj, ["name"])  # bulk_update
```

---

## 6. Guía de uso

### 6.1 Definir el serializer

```python
# apps/test_app/serializers.py
class AuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
```

### 6.2 Definir el servicio

```python
# apps/test_app/services.py
from core.services import ServiceGenerics


class AuthorService(ServiceGenerics):
    pass
```

### 6.3 Definir el viewset

```python
# apps/test_app/views.py
class AuthorViewSet(
    GenericViewsetService,
    ListModelMixin,
    RetrieveModelMixin,
    CreateServicesMixin,
    UpdateServicesMixin,
):
    queryset = Author.objects.all()
    serializer_class_default = AuthorSerializer
    services_class = AuthorService
```

Con eso queda operativo `GET list`, `GET detail`, `POST create`, `PUT update` y
`PATCH partial_update`.

### 6.4 Serializers distintos por acción

```python
class AuthorViewSet(...):
    serializer_class_default = AuthorSerializer
    serializer_class_object = {"publish": AuthorPublishSerializer}
```

`get_serializer_class()` elige el del `dict` para la acción en curso y cae en
`serializer_class_default` para el resto.

### 6.5 Acción personalizada

El nombre de la acción es el que se le pasa al servicio, así que el servicio
tiene que implementar ese método:

```python
class AuthorService(ServiceGenerics):
    def publish(self, validated_data):
        self.instance.published_at = timezone.now()
        self.instance.save(update_fields=["published_at"])
        return validated_data
```

```python
class AuthorViewSet(...):
    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        instance = self.get_object()
        service = self.get_service_class(
            user=request.user,
            action="publish",
            instance=instance,
            model=self.get_model(),
        )
        service.action_controller({})
        return Response(status=status.HTTP_204_NO_CONTENT)
```

### 6.6 Escrituras masivas

```python
from core.save import SaveHandled

handler = SaveHandled()
handler.bulk_handled(
    Author,
    [],  # fields_update: no se usa en la ruta de bulk_create
    validated_data=[{"name": "Ana", "email": "ana@x.com"}, ...],
    batch_size=1000,
    ignore_conflicts=False,
)
```

---

## 7. Detalles a tener en cuenta

- **`serializer_class_default`, no `serializer_class`.** DRF ya define
  `serializer_class = None` en `GenericAPIView`; el framework usa un nombre
  distinto a propósito para no pisar el atributo estándar de DRF.
- **`serializer_class_object` es un atributo de clase.** Definilo en el viewset,
  no lo mutes en runtime (el dict sería compartido por todas las instancias).
- **`self.action` no existe durante las validaciones.** Las validaciones corren
  antes de que DRF resuelva la acción.
- **El servicio recibe la acción como string.** `create` → `"create"`,
  `update`/`partial_update` → `"update"`. Cualquier otra acción necesita su
  propio método en el servicio.
- **`_update()` recibe la instancia, no la clase.** El parámetro se llama
  `model` por historia del código, pero en la práctica es el objeto ya
  instanciado (por eso puede hacer `setattr()` y `.save()`).
- **`SaveHandled` es un Singleton.** No guardes estado por petición en sus
  atributos; usá variables locales (como hace `_create` con las relaciones
  *many-to-many*).
- **`bulk_handled()` tiene sus propias reglas.** `fields_update` es obligatorio
  siempre (en la ruta de `bulk_create` se pasa `[]`), la ruta de `bulk_update`
  acepta **una sola instancia** (el `assert` rechaza listas, aunque `_bulk_update`
  internamente las soporta) y un `validated_data` vacío cae en la rama de
  update y termina en `AssertionError`.

---

## 8. Referencias

- `apps/test_app/` — ejemplo completo y funcional de la integración.
- `core/generic_viewset/base.py` — `GenericViewsetService`.
- `core/generic_viewset/validates.py` — `ValidatesAtributes`.
- `core/generic_viewset/mixins/` — `BaseMixin`, `CreateServicesMixin`, `UpdateServicesMixin`.
- `core/services/base.py` — `Service`, `ServiceGenerics`.
- `core/save/base.py` — `Save`.
- `core/save/bulk_save.py` — `BulkSave`.
- `core/save/handled.py` — `SaveHandled`.
