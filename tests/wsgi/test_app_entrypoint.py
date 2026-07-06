from contextlib import contextmanager

from muscles import DependencyContainer, TelemetryProvider, inspect_application
from muscles.asgi import MuscularAsgiApp, asgi_app
from muscles.asgi import RestApi, TestClient


def test_asgi_app_entrypoint_exports_callable():
    app = MuscularAsgiApp()
    application = asgi_app(app)
    assert callable(application)


def test_asgi_app_passes_request_state_via_execute_kwargs():
    captured = {}

    class DummyContext:
        def execute(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return None

    class DummyApp:
        asgi = DummyContext()

    application = asgi_app(DummyApp())

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        return None

    import asyncio

    scope = {"type": "http", "method": "GET", "path": "/health"}
    asyncio.run(application(scope, receive, send))
    assert captured["args"] == ()
    assert captured["kwargs"]["scope"] is scope
    assert captured["kwargs"]["receive"] is receive
    assert captured["kwargs"]["send"] is send


class RecordingTelemetry(TelemetryProvider):
    def __init__(self):
        self.spans = []

    @contextmanager
    def span(self, name: str, **attributes):
        span = RecordingSpan(attributes)
        yield span
        self.spans.append((name, span.attributes))


class RecordingSpan:
    def __init__(self, attributes):
        self.attributes = dict(attributes)

    def set_attribute(self, key, value):
        self.attributes[key] = value


def test_asgi_app_mounts_rest_api_and_records_server_dispatch_span():
    class App(MuscularAsgiApp):
        def __init__(self):
            self.container = DependencyContainer()
            self.telemetry = RecordingTelemetry()
            self.container.register(TelemetryProvider, self.telemetry)
            self.api = RestApi(name="EntrypointApi", prefix="/api")

            @self.api.init("/entrypoint-otel", method="get")
            def entrypoint_otel(request):
                return {"ok": True}

    app = App()
    application = asgi_app(app)

    response = TestClient(application).get("/api/entrypoint-otel")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert any(route["path"] == "/api/entrypoint-otel" for route in inspect_application(app)["routes"])
    assert (
        "muscles.server.dispatch",
        {
            "muscles.app": "App",
            "muscles.route.name": "api.entrypoint-otel",
            "muscles.route.path": "/api/entrypoint-otel",
            "muscles.transport": "asgi",
            "http.method": "GET",
            "http.route": "/api/entrypoint-otel",
            "http.status_code": 200,
        },
    ) in app.telemetry.spans
