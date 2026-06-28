import asyncio
from dataclasses import dataclass

import pytest

from muscles import ApplicationException, Dependency, cors
from muscles.asgi.asgi.response import BaseResponse
from muscles.asgi.asgi.routers import Itinerary, RouteRuleDefault
from muscles.asgi.asgi.server import AsgiServer


class Request:
    def __init__(self, handler, body=None, path="/api/documents", method="POST"):
        self.route = {"handler": handler}
        self.itinerary = None
        self.path = path
        self.method = method
        self.content_type = "application/json"
        self.headers = {}
        self.cookies = {}
        self.query = {}
        self.json = body if body is not None else {}


@dataclass
class CreateDocument:
    title: str


class StoreInterface:
    pass


@Dependency.init(StoreInterface)
class Store(StoreInterface):
    name = "documents"


def test_call_handler_builds_typed_body_and_injects_dependency():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)

    def handler(body: CreateDocument, store: StoreInterface):
        return {"title": body.title, "store": store.name}

    result = asyncio.run(server._call_handler(Request(handler, {"title": "Spec"}), {}))

    assert result == {"title": "Spec", "store": "documents"}


def test_call_handler_uses_query_header_cookie_fallbacks():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)

    def handler(page, trace_id, session):
        return page, trace_id, session

    request = Request(handler, {})
    request.query = {"page": "2"}
    request.headers = {"Trace-Id": "abc"}
    request.cookies = {"session": "cookie"}

    result = asyncio.run(server._call_handler(request, {}))

    assert result == ("2", "abc", "cookie")


def test_call_handler_missing_required_argument_returns_validation_error():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)

    def handler(required):
        return required

    with pytest.raises(ApplicationException) as exc:
        asyncio.run(server._call_handler(Request(handler, {}), {}))

    assert exc.value.status == 422


def test_application_exception_status_is_preserved_in_protocol_response():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    error = ApplicationException(status=422, reason="bad input")

    response = server._to_protocol_response(error, request=None)

    assert isinstance(response, BaseResponse)
    assert response.status == "422"


def test_cors_preflight_response_for_matching_itinerary():
    itinerary = Itinerary(name="asgi-cors-preflight")
    itinerary.add_rule(RouteRuleDefault())
    itinerary.add("/cors-preflight", handler=lambda request: "ok", method="GET")
    itinerary.use(cors(allow_origins=["https://app.example"], allow_methods=["GET"]))
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    request = Request(lambda request: "ok", path="/cors-preflight", method="OPTIONS")
    request.origin = "https://app.example"

    response = server._cors_preflight_response(request)

    assert response.status == 204
    assert response.headers["Access-Control-Allow-Origin"] == "https://app.example"
