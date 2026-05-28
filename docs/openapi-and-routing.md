# OpenAPI And Routing

ASGI uses the same controller/action model as WSGI. The transport layer receives
ASGI input, turns it into a framework request, resolves the shared route tree and
serializes a framework response back to ASGI messages.

## Controller Shape

```python
from muscles import JsonRequestBody, JsonResponseBody, Model, String, Column
from muscles.asgi import RestApi


class Booking(Model):
    name = Column(String, required=True)


api = RestApi(prefix="/api/v1", version="1.0", name="ApiV1")


@api.controller("/bookings", description="Bookings")
class BookingController:
    @api.action(
        route="",
        method="post",
        request=[JsonRequestBody(model=Booking)],
        response=[JsonResponseBody(model=Booking)],
    )
    def create(self, request):
        return request.json
```

## Generated Paths

OpenAPI paths use the route visible to clients:

- API prefix: `/api/v1`;
- controller/action path: `/bookings`;
- OpenAPI path: `/api/v1/bookings`.

That keeps Swagger UI and generated curl commands correct.

## Compatibility

The ASGI tests use a small WSGI-compatible bridge for shared runtime scenarios.
This is test support only: production applications should run through an ASGI
server and the ASGI strategy.

## Performance Notes

Avoid copying routing logic into ASGI-specific schema modules. Shared indexes and
match caches live in the core itinerary, so ASGI should reuse them directly.
