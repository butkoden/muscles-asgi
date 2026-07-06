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

## Mounting For Inspection And Tools

`RestApi` owns ASGI route declaration, dispatch and OpenAPI generation. Core
tooling, however, reads routes from `ApplicationRegistry` through
`inspect_application(app)`. Use `mount_api(app, api)` or its alias
`finalize_api(app, api)` to copy lightweight route descriptors from `RestApi`
into the registry:

```python
from muscles import inspect_application
from muscles.asgi import RestApi, mount_api

app = App()
api = RestApi(prefix="/api/v1", version="1.0", name="ApiV1")


@api.init("/health", method="GET", key="health.show")
def health(request):
    return {"ok": True}


mount_api(app, api)

routes = inspect_application(app)["routes"]
assert any(route["path"] == "/api/v1/health" for route in routes)
```

Call `mount_api(...)` after all controllers/actions are registered and before
inspection, doctor checks or generators run. The operation is idempotent: calling
it more than once will not duplicate the same route signature.

`asgi_app(app)` calls `mount_application_apis(app)` once while creating the ASGI
entrypoint. It scans `RestApi` objects stored on the application class or
instance and projects them into the registry. Use explicit `mount_api(...)` when
you build APIs outside the application object or need inspection before the ASGI
entrypoint exists.

This projection does not move HTTP dispatch into `ApplicationRegistry`. ASGI
requests still resolve through the `RestApi` route tree; the registry receives
only descriptors that tools can read without knowing ASGI internals.

## Server Dispatch Telemetry

When the application resolves a neutral `TelemetryProvider`, ASGI adds a
`muscles.server.dispatch` span around matched route execution:

```python
from muscles import TelemetryProvider

telemetry = app.container.resolve(TelemetryProvider)
```

The span includes safe framework and HTTP metadata:

- `muscles.app`
- `muscles.route.name`
- `muscles.route.path`
- `muscles.transport`
- `http.method`
- `http.route`
- `http.status_code`

ASGI does not import `muscles_otel`. It only uses the neutral `span(...)`
surface from core, so applications can use `muscles-otel` or another compatible
provider.

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

## Route Key Rule (Important)

`@routes.init(...)` / `api.init(...)` binds handlers by route `path + key + method`.

Endpoints that share the same `path` may keep one shared `key`, or use distinct
keys per HTTP method when operation names must differ.

```python
@api.init("/api/documents", key="documents.collection", method="GET", summary="List")
def list_documents(request):
    ...


@api.init("/api/documents", key="documents.collection", method="POST", summary="Create")
def create_document(request):
    ...


@api.init("/api/documents", key="documents.list", method="GET", summary="List V2")
def list_documents_v2(request):
    ...


@api.init("/api/documents", key="documents.create", method="POST", summary="Create V2")
def create_document_v2(request):
    ...
```

Core route lookup keeps all route records on the matched terminal node and then
filters by method and content type.

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
