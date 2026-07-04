# Muscles ASGI

`muscles-asgi` is the ASGI runtime for Muscles. It mirrors the WSGI API model
while using ASGI scopes/events for async-capable servers.

## Installation

Canonical ecosystem install matrix is documented in core:
[Muscles installation matrix](https://github.com/butkoden/muscles/blob/master/docs/installation.md).

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

## REST API And Swagger

`RestApi` controllers/actions are projected into OpenAPI automatically. Generated
paths include the external API prefix, so a mounted route such as
`/api/v1/bookings` appears in Swagger exactly as clients must call it.

More detail: [docs/openapi-and-routing.md](docs/openapi-and-routing.md).
Backend pipeline features are documented in
[docs/backend-pipeline.md](docs/backend-pipeline.md).

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
