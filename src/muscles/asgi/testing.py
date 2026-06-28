from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass
class TestResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self):
        return json.loads(self.text)


class TestClient:
    __test__ = False

    def __init__(self, app, headers: dict[str, str] | None = None):
        self.app = app
        self.headers = headers or {}

    def with_bearer(self, token: str) -> "TestClient":
        headers = dict(self.headers)
        headers["Authorization"] = f"Bearer {token}"
        return TestClient(self.app, headers=headers)

    def get(self, path: str, **kwargs) -> TestResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> TestResponse:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs) -> TestResponse:
        return self.request("PATCH", path, **kwargs)

    def put(self, path: str, **kwargs) -> TestResponse:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> TestResponse:
        return self.request("DELETE", path, **kwargs)

    def request(
        self,
        method: str,
        path: str,
        json: object | None = None,
        data: bytes | str | None = None,
        headers: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> TestResponse:
        return asyncio.run(self._request(method, path, json=json, data=data, headers=headers, files=files))

    async def _request(self, method, path, json=None, data=None, headers=None, files=None):
        parsed = urlsplit(path)
        request_headers = dict(self.headers)
        request_headers.update(headers or {})
        body = b""

        if files:
            boundary = f"----muscles-{uuid.uuid4().hex}"
            request_headers.setdefault("Content-Type", f"multipart/form-data; boundary={boundary}")
            body = self._encode_multipart(boundary, files, data)
        elif json is not None:
            request_headers.setdefault("Content-Type", "application/json")
            body = __import__("json").dumps(json).encode("utf-8")
        elif data is not None:
            body = data.encode("utf-8") if isinstance(data, str) else data

        request_headers.setdefault("Content-Length", str(len(body)))
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": parsed.path or "/",
            "raw_path": (parsed.path or "/").encode("utf-8"),
            "query_string": parsed.query.encode("utf-8"),
            "headers": [(key.lower().encode("latin-1"), str(value).encode("latin-1")) for key, value in request_headers.items()],
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 1),
        }
        messages = [{"type": "http.request", "body": body, "more_body": False}]
        sent = []

        async def receive():
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        result = self.app(scope, receive, send)
        if asyncio.iscoroutine(result):
            await result

        status = 500
        response_headers = {}
        chunks = []
        for message in sent:
            if message["type"] == "http.response.start":
                status = message["status"]
                response_headers = {
                    key.decode("latin-1").title(): value.decode("latin-1")
                    for key, value in message.get("headers", [])
                }
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))
        return TestResponse(status_code=status, headers=response_headers, content=b"".join(chunks))

    def _encode_multipart(self, boundary, files, data):
        chunks = []
        fields = data if isinstance(data, dict) else {}
        for name, value in fields.items():
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode(),
                b"\r\n",
            ])
        for name, file_data in files.items():
            filename, payload, content_type = file_data
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                payload,
                b"\r\n",
            ])
        chunks.append(f"--{boundary}--\r\n".encode())
        return b"".join(chunks)
