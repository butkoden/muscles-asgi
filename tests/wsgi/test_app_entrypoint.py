from muscles.asgi import MuscularAsgiApp, asgi_app


def test_asgi_app_entrypoint_exports_callable():
    app = MuscularAsgiApp()
    application = asgi_app(app)
    assert callable(application)
