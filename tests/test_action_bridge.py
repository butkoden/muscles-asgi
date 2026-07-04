from muscles import ApplicationMeta, BaseStrategy, Context
from muscles.asgi import ActionAsgiAdapter, TestClient


class _EchoStrategy(BaseStrategy):
    def execute(self, *args, **kwargs):
        return kwargs


def _make_app():
    class _App(metaclass=ApplicationMeta):
        context = Context(_EchoStrategy)

    app = _App()

    @app.action(
        name="bookings.echo",
        input_schema={"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]},
        transports=["http"],
    )
    def echo(payload, context):
        return {"payload": payload, "transport": context.transport, "metadata": context.metadata}

    @app.action(name="bookings.query", input_schema={"type": "object", "properties": {}}, transports=["http"])
    def query(payload, context):
        return {"payload": payload, "transport": context.transport}

    @app.action(name="bookings.secret", input_schema={"type": "object", "properties": {}}, transports=["http"])
    def secret(_payload, _context):
        raise PermissionError("admin required")

    @app.action(name="bookings.cli_only", input_schema={"type": "object", "properties": {}}, transports=["cli"])
    def cli_only(_payload, _context):
        return {"ok": True}

    @app.action(name="bookings.stream", input_schema={"type": "object", "properties": {}}, transports=["http"])
    def stream(_payload, _context):
        yield {"event": "progress", "data": {"step": 1}}

    return app


def test_action_bridge_dispatches_allowed_post_action():
    adapter = ActionAsgiAdapter.from_application(_make_app(), allowed_actions={"bookings.echo"})
    response = TestClient(adapter).post("/actions/bookings.echo", json={"title": "Call"})

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    payload = response.json()
    assert payload["action"] == "bookings.echo"
    assert payload["result"]["payload"] == {"title": "Call"}
    assert payload["result"]["transport"] == "http"
    assert payload["result"]["metadata"] == {"projection": "asgi"}


def test_action_bridge_requires_explicit_allowed_action():
    adapter = ActionAsgiAdapter.from_application(_make_app(), allowed_actions={"bookings.echo"})
    response = TestClient(adapter).post("/actions/bookings.secret", json={})

    assert response.status_code == 404
    assert response.headers["Content-Type"] == "application/problem+json"
    assert response.json()["code"] == "action_not_exposed"


def test_action_bridge_maps_validation_error_to_problem_json():
    adapter = ActionAsgiAdapter.from_application(_make_app(), allowed_actions={"bookings.echo"})
    response = TestClient(adapter).post("/actions/bookings.echo", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "action_validation_error"
    assert payload["action"] == "bookings.echo"
    assert payload["data"]["path"] == []


def test_action_bridge_maps_permission_error_to_problem_json():
    adapter = ActionAsgiAdapter.from_application(_make_app(), allowed_actions={"bookings.secret"})
    response = TestClient(adapter).post("/actions/bookings.secret", json={})

    assert response.status_code == 403
    payload = response.json()
    assert payload["code"] == "action_permission_denied"
    assert payload["action"] == "bookings.secret"


def test_action_bridge_maps_unknown_allowed_action_to_not_found():
    adapter = ActionAsgiAdapter.from_application(_make_app(), allowed_actions={"bookings.missing"})
    response = TestClient(adapter).post("/actions/bookings.missing", json={})

    assert response.status_code == 404
    assert response.json()["code"] == "action_not_found"


def test_action_bridge_respects_core_transport_filtering():
    adapter = ActionAsgiAdapter.from_application(_make_app(), allowed_actions={"bookings.cli_only"})
    response = TestClient(adapter).post("/actions/bookings.cli_only", json={})

    assert response.status_code == 403
    assert response.json()["code"] == "action_permission_denied"


def test_action_bridge_rejects_stream_actions_with_sse_hint():
    adapter = ActionAsgiAdapter.from_application(_make_app(), allowed_actions={"bookings.stream"})
    response = TestClient(adapter).post("/actions/bookings.stream", json={})

    assert response.status_code == 501
    payload = response.json()
    assert payload["code"] == "stream_not_supported"
    assert "muscles-sse" in payload["detail"]


def test_action_bridge_allows_get_query_payload_when_configured():
    adapter = ActionAsgiAdapter.from_application(
        _make_app(),
        allowed_actions={"bookings.query"},
        get_actions={"bookings.query"},
    )
    response = TestClient(adapter).get("/actions/bookings.query?status=open&tag=a&tag=b")

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["payload"] == {"status": "open", "tag": ["a", "b"]}
    assert payload["result"]["transport"] == "http"
