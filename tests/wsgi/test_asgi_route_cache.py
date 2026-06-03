from muscles.asgi.asgi import server as asgi_server
from muscles.asgi.asgi.routers import Itinerary, RouteRuleDefault
from muscles.asgi.asgi.server import AsgiServer


class Request:
    def __init__(self, path, method="GET", content_type="application/json"):
        self.path = path
        self.method = method
        self.content_type = content_type
        self.route = None
        self.itinerary = None


def test_route_resolution_cache_stores_full_result(monkeypatch):
    itinerary = Itinerary("asgi-fast-route-cache")
    itinerary.add_rule(RouteRuleDefault())

    handler = itinerary.add("/cache-path", key="cache.path", method="GET", handler=lambda: {}, content_type="application/json")

    call_counter = {"count": 0}
    original = itinerary.get_current_route

    def counted_get_current_route(request):
        call_counter["count"] += 1
        return original(request)

    monkeypatch.setattr(asgi_server, "itinerary", itinerary)
    monkeypatch.setattr(itinerary, "instance_list", lambda: [("cache-test", itinerary)])
    monkeypatch.setattr(itinerary, "get_current_route", counted_get_current_route)

    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    first = Request("/cache-path")
    second = Request("/cache-path")

    server._resolve_route(first)
    server._resolve_route(second)

    assert call_counter["count"] == 1
    assert first.route is not None
    assert first.route["handler"] is handler
    assert first.route is second.route
