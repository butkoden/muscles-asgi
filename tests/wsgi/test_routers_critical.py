import pytest

from muscles.asgi.asgi.routers import Itinerary, RouteRuleDefault, RouteRuleVar, RouteRuleInt


class Request:
    def __init__(self, path, method="GET", content_type="text/plain"):
        self.path = path
        self.method = method
        self.content_type = content_type


def _handler(**kwargs):
    return kwargs


def _make_itinerary(name):
    itinerary = Itinerary(name=name)
    itinerary.add_rule(RouteRuleDefault())
    itinerary.add_rule(RouteRuleVar())
    itinerary.add_rule(RouteRuleInt())
    return itinerary


def test_route_registration_and_lookup_by_method_and_type():
    itinerary = _make_itinerary("asgi-router-critical-1")
    get_handler = itinerary.add("/items/{id:int}", key="items.show", handler=_handler, method="GET", content_type="application/json")
    itinerary.add("/items/{id:int}", key="items.show", handler=_handler, method="POST", content_type="application/json")

    route, params = itinerary.get_current_route(Request("/items/7", method="GET", content_type="application/json"))
    assert route["handler"] is get_handler
    assert params == {"id": "7"}


def test_same_path_can_use_distinct_keys_per_method():
    itinerary = _make_itinerary("asgi-router-distinct-method-keys")
    get_handler = itinerary.add("/items", key="items.list", handler=_handler, method="GET")
    post_handler = itinerary.add("/items", key="items.create", handler=_handler, method="POST")

    get_route, _ = itinerary.get_current_route(Request("/items", method="GET"))
    post_route, _ = itinerary.get_current_route(Request("/items", method="POST"))

    assert get_route["handler"] is get_handler
    assert get_route["key"] == "items.list"
    assert post_route["handler"] is post_handler
    assert post_route["key"] == "items.create"


def test_static_registration_and_lookup():
    itinerary = _make_itinerary("asgi-router-critical-2")
    itinerary.add_static("static", prefix="/assets", handler=_handler)
    current = itinerary.get_current_static(Request("/assets/app.css"))
    assert current is not None
    assert current["handler"] is _handler


def test_error_handler_lookup_priority_and_duplicates():
    name = "asgi-router-critical-3"
    itinerary = _make_itinerary(name)

    def h_default(err, request):
        return "default"

    def h_404(err, request):
        return "404"

    itinerary.add_error_handler(None, h_default)
    itinerary.add_error_handler(404, h_404)

    class Err:
        def __init__(self, status):
            self.status = status

    assert itinerary.get_current_error_handler(Err(404))["handler"] is h_404
    assert itinerary.get_current_error_handler(Err(500))["handler"] is h_default

    with pytest.raises(Exception):
        itinerary.add_error_handler(404, h_404)

    Itinerary._instances.pop((Itinerary, name), None)


def test_to_url_with_int_rule():
    itinerary = _make_itinerary("asgi-router-critical-4")
    itinerary.add("/users/{id:int}", key="users.show", handler=_handler, method="GET")
    assert itinerary.to_url("users.show", {"id": 42}) == "users/42"
