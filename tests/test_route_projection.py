from __future__ import annotations

from types import SimpleNamespace

from muscles import inspect_application
from muscles.asgi import RestApi, mount_api


def test_mount_api_projects_rest_api_routes_into_application_registry():
    app = SimpleNamespace()
    api = RestApi(name="ProjectionApi", prefix="/api")

    @api.init("/ping", method="get")
    def ping(request):
        return {"ok": True}

    assert inspect_application(app)["routes"] == []

    mounted = mount_api(app, api)

    assert mounted is api
    routes = inspect_application(app)["routes"]
    ping_route = next(route for route in routes if route["path"] == "/api/ping")
    assert ping_route["name"] == "api.ping"
    assert ping_route["method"] == "get"
    assert ping_route["canonical"] == "/api/ping"
    assert ping_route["handler"].endswith(".ping")


def test_mount_api_is_idempotent_for_same_app_and_api():
    app = SimpleNamespace()
    api = RestApi(name="ProjectionIdempotentApi", prefix="/api")

    @api.init("/health", method="get")
    def health(request):
        return {"ok": True}

    mount_api(app, api)
    route_count = len(inspect_application(app)["routes"])

    mount_api(app, api)

    assert len(inspect_application(app)["routes"]) == route_count
