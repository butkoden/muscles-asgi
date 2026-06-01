from muscles.asgi import MuscularAsgiApp, asgi_app


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
        context = DummyContext()

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
