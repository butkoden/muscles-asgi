from muscles.asgi.testing import TestClient


async def app(scope, receive, send):
    first = await receive()
    await send({
        "type": "http.response.start",
        "status": 201,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({
        "type": "http.response.body",
        "body": b'{"path":"%b","auth":"%b","body":%b}' % (
            scope["path"].encode(),
            dict(scope["headers"]).get(b"authorization", b""),
            first.get("body", b"null"),
        ),
    })


def test_asgi_test_client_sends_json_and_bearer_auth():
    client = TestClient(app).with_bearer("token")

    response = client.post("/api/documents?x=1", json={"title": "Spec"})

    assert response.status_code == 201
    assert response.json()["path"] == "/api/documents"
    assert response.json()["auth"] == "Bearer token"
    assert response.json()["body"] == {"title": "Spec"}
