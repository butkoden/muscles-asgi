from __future__ import annotations

import inspect

from muscles import ApplicationMeta, Configurator, Context
from .asgi import AsgiStrategy


class MuscularAsgiApp(metaclass=ApplicationMeta):
    """
    Minimal ASGI-oriented Muscles application skeleton.
    Projects can subclass this class and register routes/controllers in app code.
    """

    package_paths = []
    shutup = False

    config = Configurator(
        obj={
            "main": {
                "BASEDIR": ".",
                "BASE_URL": "http://localhost:8080",
                "SERVER_NAME": "localhost:8080",
                "HOST": "0.0.0.0",
                "PORT": "8080",
                "ENV": "development",
                "DEBUG": True,
                "TIMEZONE": "UTC",
                "MAIN_ROUTE": "page.index",
            },
            "routes": {"prefix": ""},
            "api": {"prefix": "/api", "default_version": "v1", "controllers": {}},
        }
    )

    asgi = Context(AsgiStrategy, params={})

    def run(self, *args, **kwargs):
        return self.asgi.execute(*args, **kwargs, shutup=self.shutup)


def asgi_app(app: MuscularAsgiApp, context: str | Context | None = None):
    def _resolve_context():
        if isinstance(context, Context):
            return context
        if context is not None and hasattr(app, context):
            selected = getattr(app, context)
            if not isinstance(selected, Context):
                raise TypeError(f"Application has no context '{context}'")
            return selected
        if hasattr(app, 'asgi'):
            return getattr(app, 'asgi')
        raise TypeError("Application has no context 'asgi'")

    async def application(scope, receive, send):
        ctx = _resolve_context()
        result = ctx.execute(scope=scope, receive=receive, send=send)
        if inspect.isawaitable(result):
            await result

    return application
