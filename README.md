# Muscles ASGI

`muscles-asgi` is the ASGI runtime for Muscles. It mirrors the WSGI API model
while using ASGI scopes/events for async-capable servers.

## Installation

Canonical ecosystem install matrix is documented in core:
[Muscles installation matrix](https://github.com/butkoden/muscles/blob/master/docs/installation.md).

## Related Repositories

- [`muscles`](https://github.com/butkoden/muscles) - core contracts, routing, actions and canonical documentation.
- [`muscles-wsgi`](https://github.com/butkoden/muscles-wsgi) - WSGI runtime with the same application model.
- [`muscles-cli`](https://github.com/butkoden/muscles-cli) - CLI projection and developer commands.
- [`muscles-sse`](https://github.com/butkoden/muscles-sse) - streaming projection for action results.
- [`muscles-mcp`](https://github.com/butkoden/muscles-mcp) - MCP projection that can bind to ASGI entrypoints.
- [`muscles-benchmarks`](https://github.com/butkoden/muscles-benchmarks) - ASGI regression and architecture checks.

## Runtime

An app binds `Context` to `AsgiStrategy`:

```python
from muscles import ApplicationMeta, Configurator, Context
from muscles.asgi import AsgiStrategy


class App(metaclass=ApplicationMeta):
    config = Configurator(obj={"main": {"HOST": "0.0.0.0", "PORT": "8080"}})
    context = Context(AsgiStrategy, params={})

    def run(self, *args):
        return self.context.execute(*args, shutup=True)
```

The ASGI package shares core schemas, route matching and OpenAPI generation with
the other runtimes. It should not duplicate core itinerary code.

## Schema Ownership

ASGI does not ship its own `muscles.asgi.schema_` package. Framework schemas,
columns, fields, request/response bodies, security objects and value objects
belong to `muscles.core.schema` and should be imported from `muscles`:

```python
from muscles import Column, JsonRequestBody, Model, String
```

## REST API And Swagger

`RestApi` controllers/actions are projected into OpenAPI automatically. Generated
paths include the external API prefix, so a mounted route such as
`/api/v1/bookings` appears in Swagger exactly as clients must call it.

More detail: [docs/openapi-and-routing.md](docs/openapi-and-routing.md).
Backend pipeline features are documented in
[docs/backend-pipeline.md](docs/backend-pipeline.md).

## Application Inspection

Use `mount_api(app, api)` after declaring a `RestApi` to project ASGI routes into
the core `ApplicationRegistry`. This makes routes visible to
`inspect_application(app)` and CLI/doctor tooling without making the registry
the HTTP dispatch source.

Call it after all controllers/actions are registered and before running
inspection, doctor checks or generators. It is safe to call more than once:
already projected routes are skipped. `finalize_api(app, api)` is an alias for
projects that prefer a "declare, then finalize" bootstrap style.
`asgi_app(app)` also calls `mount_application_apis(app)` once when the ASGI
entrypoint is created, so APIs stored as attributes on the application are
visible to runtime inspection without additional app-side adapters.

```python
from muscles import inspect_application
from muscles.asgi import RestApi, finalize_api

app = App()
api = RestApi(name="Api", prefix="/api")

@api.init("/ping", method="get")
def ping(request):
    return {"ok": True}

finalize_api(app, api)
assert any(route["path"] == "/api/ping" for route in inspect_application(app)["routes"])
```

Request dispatch still uses the ASGI `RestApi` route tree. The projected routes
are lightweight descriptors for tools that need to understand the application
without knowing ASGI internals.

When the application has a neutral `TelemetryProvider`, ASGI records a
`muscles.server.dispatch` span for matched routes with app, route, method and
HTTP status attributes.

## Action Bridge

`ActionAsgiAdapter` is an optional HTTP projection for Muscles actions. It keeps
package-specific features out of ASGI routes: packages register normal core
actions, and ASGI exposes only the actions explicitly allowed by the project.

```python
from muscles.asgi import ActionAsgiAdapter

application = ActionAsgiAdapter.from_application(
    app,
    allowed_actions={"bookings.echo"},
)
```

The bridge accepts JSON `POST /actions/<action-name>` requests, executes through
core `ActionDispatcher(..., transport="http")`, returns JSON for non-stream
results, and returns `application/problem+json` for core action errors. Stream
actions should be projected through `muscles-sse`.

## Request Handling

Request parsing does not require `cgi`, `multipart` or `python-magic` at import
time. Multipart form data uses the standard library path, and missing MIME
detection falls back safely.

ASGI request execution is stateless on `Context`: request-specific data
(`scope`, `receive`, `send`) is passed directly into `context.execute(...)`
per request. The strategy keeps a persistent server lifecycle while request
state stays isolated.

## Development

Run tests with sibling packages on `PYTHONPATH`:

```bash
PYTHONPATH=../muscles/src:src python -m pytest -q
```

Production notes: [docs/production.md](docs/production.md).
