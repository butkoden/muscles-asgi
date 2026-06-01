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

    context = Context(AsgiStrategy, {})

    def run(self, *args, **kwargs):
        return self.context.execute(*args, **kwargs, shutup=self.shutup)


def asgi_app(app: MuscularAsgiApp):
    async def application(scope, receive, send):
        result = app.context.execute(scope=scope, receive=receive, send=send)
        if inspect.isawaitable(result):
            await result

    return application
