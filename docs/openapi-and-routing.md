# OpenAPI And Routing

ASGI uses the same controller/action model as WSGI. The transport layer receives
ASGI input, turns it into a framework request, resolves the shared route tree and
serializes a framework response back to ASGI messages.

## Controller Shape

```python
from muscles import JsonRequestBody, JsonResponseBody, Model, String, Column
from muscles.asgi import RestApi


class Booking(Model):
    name = Column(String, required=True)


api = RestApi(prefix="/api/v1", version="1.0", name="ApiV1")


@api.controller("/bookings", description="Bookings")
class BookingController:
    @api.action(
        route="",
        method="post",
        request=[JsonRequestBody(model=Booking)],
        response=[JsonResponseBody(model=Booking)],
    )
    def create(self, request):
        return request.json
```

## Generated Paths

OpenAPI paths use the route visible to clients:

- API prefix: `/api/v1`;
- controller/action path: `/bookings`;
- OpenAPI path: `/api/v1/bookings`.

That keeps Swagger UI and generated curl commands correct.

## Compatibility

The ASGI tests use a small WSGI-compatible bridge for shared runtime scenarios.
This is test support only: production applications should run through an ASGI
server and the ASGI strategy.

## Route Groups

`RestApi.group()` registers routes with a shared prefix and inherited OpenAPI
metadata:

```python
from muscles import BearerAuthSecurity, JsonResponseBody

documents = api.group(
    "/documents",
    tags=["Documents"],
    security=[BearerAuthSecurity()],
    response={401: JsonResponseBody(description="Unauthorized")},
)


@documents.init("/{id}", method="GET", summary="Show document")
def show(request, id):
    return {"id": id}
```

The generated operation is emitted as `get`, includes `tags`, `security` and
common responses, and registers the bearer scheme in OpenAPI components.

Endpoint metadata can override inherited auth:

```python
@documents.init("/login", method="POST", auth=False)
def login(request):
    return {"token": "issued-token"}
```

`auth=False` clears inherited security for that operation and tells the ASGI
pipeline to skip matching auth guards.

## Performance Notes

Avoid copying routing logic into ASGI-specific schema modules. Shared indexes and
match caches live in the core itinerary, so ASGI should reuse them directly.

## Swagger/OpenAPI defaults

`RestApi` uses these defaults:
- `docs_url` = `/docs`
- `swagger_url` = `/swagger`
- `openapi_url` = `/openapi.json`
- `schema_url` = `schema`
- `prefix` = `/`

By default the UI is reachable at `/swagger`, and OpenAPI JSON at `/openapi.json`.
Compatibility aliases are also registered, so for the defaults you'll also get:
- `/docs` as docs alias
- `/schema` as openapi alias
- `/healthz`, `/ready`, `/live` service endpoints

When `prefix="/api/v1"` the same defaults become:
- UI: `/api/v1/docs`, `/api/v1/swagger`, `/api/v1/redoc`
- OpenAPI: `/api/v1/openapi.json`, `/api/v1/schema`

You can override route names directly in `RestApi(...)`:
```python
api = RestApi(
    prefix="/api/v1",
    docs_url="/api-docs",
    swagger_url="/api-docs",
    openapi_url="/api-spec.json",
    schema_url="/api-spec",
)
```
