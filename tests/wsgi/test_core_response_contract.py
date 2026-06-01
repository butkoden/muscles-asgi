from muscles import HtmlResponse as CoreHtmlResponse
from muscles import JsonResponse as CoreJsonResponse
from muscles.asgi.asgi.response import BaseResponse as AsgiBaseResponse
from muscles.asgi.asgi.response import HtmlResponse as AsgiHtmlResponse
from muscles.asgi.asgi.response import JsonResponse as AsgiJsonResponse
from muscles.asgi.asgi.server import AsgiServer


def test_asgi_server_accepts_core_json_response():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response(CoreJsonResponse({"ok": True}))
    assert isinstance(response, AsgiJsonResponse)
    assert response.status == "200"
    assert response.make_body() == b'{"ok": true}'


def test_asgi_server_accepts_core_html_response():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    response = server._to_protocol_response(CoreHtmlResponse("<h1>ok</h1>"))
    assert isinstance(response, AsgiHtmlResponse)
    assert response.status == "200"
    assert response.make_body() == b"<h1>ok</h1>"


def test_asgi_server_keeps_legacy_protocol_response():
    server = AsgiServer(host="localhost", port=0, error_handler=Exception)
    legacy = AsgiBaseResponse(status=201, body={"created": True})
    response = server._to_protocol_response(legacy)
    assert response is legacy
