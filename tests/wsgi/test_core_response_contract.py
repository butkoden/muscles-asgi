from muscles import HtmlResponse as CoreHtmlResponse
from muscles import BaseResponse as CoreBaseResponse
from muscles import JsonResponse as CoreJsonResponse
from muscles import NoContentResponse as CoreNoContentResponse
from muscles.asgi.asgi.response import BaseResponse as AsgiBaseResponse
from muscles.asgi.asgi.server import AsgiTransport
from muscles.asgi.asgi.server import AsgiServer


def test_asgi_server_accepts_core_json_response():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response(CoreJsonResponse({"ok": True}))
    assert isinstance(response, AsgiBaseResponse)
    assert response.status == "200"
    assert response.make_body() == b'{"ok": true}'


def test_asgi_server_accepts_core_html_response():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response(CoreHtmlResponse("<h1>ok</h1>"))
    assert isinstance(response, AsgiBaseResponse)
    assert response.status == "200"
    assert response.make_body() == b"<h1>ok</h1>"


def test_asgi_server_accepts_core_no_content_response_without_body():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response(CoreNoContentResponse())

    assert isinstance(response, AsgiBaseResponse)
    assert response.status == "204"
    assert response.make_body() == b""


def test_asgi_transport_encodes_string_headers_for_protocol_messages():
    transport = AsgiTransport()

    assert transport._asgi_headers([("Content-Type", "text/plain")]) == [(b"Content-Type", b"text/plain")]


def test_asgi_server_keeps_legacy_protocol_response():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    legacy = AsgiBaseResponse(status=201, body={"created": True})
    response = server._to_protocol_response(legacy)
    assert response is legacy


def test_asgi_server_keeps_legacy_serialization_for_non_json_serializable_objects():
    class DummyFileStorage:
        def __str__(self):
            return "FileStorage('image/jpeg', 'photo.jpg')"

    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response({"file": DummyFileStorage()})
    payload = response.make_body()
    assert b"FileStorage('image/jpeg', 'photo.jpg')" in payload


def test_asgi_server_preserves_core_custom_content_type():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    core = CoreBaseResponse(
        body=b'{"type":"problem"}',
        status=422,
        headers={"X-Trace-Id": "abc"},
        content_type="application/problem+json",
    )
    response = server._to_protocol_response(core)
    headers = dict(response.headers)
    assert headers["Content-Type"] == "application/problem+json"
    assert headers["X-Trace-Id"] == "abc"


def test_asgi_server_accepts_plain_dict_as_json():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response({"ok": True, "nested": {"value": 1}})
    assert isinstance(response, AsgiBaseResponse)
    assert response.status == "200"
    assert response.make_body() == b'{"ok": true, "nested": {"value": 1}}'
    assert dict(response.headers)["Content-Type"] == "application/json; charset=utf-8"


def test_asgi_server_accepts_plain_list_as_json():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response([1, "a", {"b": True}])
    assert response.make_body() == b'[1, "a", {"b": true}]'
    assert response.status == "200"


def test_asgi_server_accepts_tuple_with_json_body():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response(({"ok": True}, 201, [("X", "Y")]))
    assert response.status == "201"
    assert response.make_body() == b'{"ok": true}'
    assert dict(response.headers)["X"] == "Y"
    assert dict(response.headers)["Content-Type"] == "application/json; charset=utf-8"


def test_asgi_server_accepts_bytes_without_transform():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response(b"abc")
    assert response.make_body() == b"abc"
    assert response.status == "200"
