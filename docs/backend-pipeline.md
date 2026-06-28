# Backend Pipeline

ASGI uses the shared `muscles` core contracts for route groups, middleware,
guards, exception mapping, auth metadata, response helpers and CORS.

## Route Groups And OpenAPI

```python
from dataclasses import dataclass

from muscles import BearerJwtAuth, JsonResponseBody, cors
from muscles.asgi import RestApi

api = RestApi(prefix="/api")
jwt_auth = BearerJwtAuth(secret=settings.jwt_secret)

documents = api.group(
    "/documents",
    tags=["Documents"],
    security=[jwt_auth],
    response={401: JsonResponseBody(description="Unauthorized")},
)

api.use(cors(allow_origins=settings.allowed_origins, allow_credentials=True))
```

Handlers registered through `documents` inherit the group tags, security and
common responses. The OpenAPI builder emits lower-case methods and includes
route-level security schemes in `components.securitySchemes`.

## Handler Arguments

The ASGI runtime builds handler arguments from path parameters, JSON body,
query parameters, headers, cookies and core dependencies:

```python
@dataclass
class CreateDocument:
    title: str


class DocumentStore:
    ...


@documents.init("", method="post")
def create_document(body: CreateDocument, store: DocumentStore, trace_id: str):
    return store.create(title=body.title, trace_id=trace_id)
```

`body` is built from JSON. Dataclasses, Pydantic-style models and simple Python
classes with keyword constructors are supported. Missing required arguments and
body validation failures return `422`.

## Guards, Auth And Errors

```python
def require_workspace(request):
    if not request.user:
        return {"error": "unauthorized"}, 401


api.guard("/api/**", require_workspace, except_=["/api/public/**"])
api.map_error(PermissionError, status=403)
api.map_error(ValueError, status=422)
```

If a handler raises a mapped exception, ASGI preserves the mapped status before
creating the problem response.

## File Upload Helpers

Multipart files are exposed as `FileStorage`:

```python
def upload(request):
    file = request.files["image"]
    file.validate(max_size=5_000_000, allowed_content_types={"image/png"})
    saved_path = file.save("/srv/uploads", safe=True)
    return {"path": saved_path}
```

`safe=True` stores the file under a sanitized basename.

## Test Client

`muscles.asgi.testing.TestClient` calls an ASGI app in-process:

```python
from muscles.asgi.testing import TestClient

client = TestClient(app).with_bearer(token)
response = client.post("/api/documents", json={"title": "Spec"})

assert response.status_code == 201
assert response.json()["title"] == "Spec"
```
