from muscles.asgi.asgi.actor import Actor
from muscles.asgi.restful.request_body import (
    JsonRequestBody as RestJsonRequestBody,
    XmlRequestBody as RestXmlRequestBody,
    MultipartRequestBody as RestMultipartRequestBody,
)
from muscles.asgi.restful.response_body import (
    JsonResponseBody as RestJsonResponseBody,
    TextResponseBody as RestTextResponseBody,
)
from muscles.asgi.schema_ import (
    JsonRequestBody,
    JsonResponseBody,
    HeaderParameter,
    Swagger,
)
from muscles import String


class DumpableModel:
    def dump(self):
        return {"type": "string"}


class SecurityMock:
    def dump(self):
        return {"apiKeyAuth": {"type": "apiKey", "name": "X-API-Key", "in": "header"}}


def test_actor_singleton_and_loader_registration():
    Actor._instances.clear()
    Actor._loaders.clear()
    actor = Actor(token="abc")
    loaded = []

    @actor.loader()
    def _loader(token, **kwargs):
        loaded.append((token, kwargs))
        return {"token": token}

    second = Actor(token="abc")
    assert second is actor
    assert second.token == "abc"
    assert loaded == []


def test_rest_request_response_body_content_types():
    assert RestJsonRequestBody().content_type == "application/json"
    assert RestXmlRequestBody().content_type == "application/xml"
    assert RestMultipartRequestBody().content_type == "multipart/form-data"
    assert RestJsonResponseBody().content_type == "application/json"
    assert RestTextResponseBody().content_type == "text/plain"


def test_schema_request_body_dump_array_constraints():
    body = JsonRequestBody(
        description="payload",
        model=DumpableModel(),
        is_list=True,
        min_items=1,
        max_items=2,
        unique_items=True,
    )
    dumped = body.dump()
    schema = dumped["application/json"]["schema"]
    assert schema["type"] == "array"
    assert schema["minItems"] == 1
    assert schema["maxItems"] == 2
    assert schema["uniqueItems"] is True


def test_schema_response_body_dump_with_base_schema_wrapper():
    class Wrapper:
        def schema(self, child):
            return {"allOf": [child]}

    response = JsonResponseBody(
        description="ok",
        model=DumpableModel(),
        base_schema=Wrapper(),
    )
    dumped = response.dump()
    assert "application/json" in dumped
    assert "allOf" in dumped["application/json"]["schema"]


def test_schema_swagger_dump_with_request_response_and_security():
    swagger = Swagger(
        title="ASGI API",
        version="1.0.0",
        request=JsonRequestBody(description="in", model=DumpableModel()),
        response={"200": JsonResponseBody(description="out", model=DumpableModel())},
        parameters=[HeaderParameter("X-Test", String, required=True, description="header")],
        security=[SecurityMock()],
    )
    dumped = swagger.dump()
    assert dumped["info"]["title"] == "ASGI API"
    assert dumped["request"]["application/json"]["description"] == "in"
    assert dumped["response"]["200"]["application/json"]["description"] == "out"
    assert dumped["parameters"][0]["name"] == "X-Test"
    assert "apiKeyAuth" in dumped["components"]["securitySchemes"]
