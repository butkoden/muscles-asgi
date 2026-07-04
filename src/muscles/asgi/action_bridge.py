from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable
from urllib.parse import parse_qs, unquote

from muscles.core import (
    ActionDispatcher,
    ActionError,
    ActionExecutionError,
    ActionNotFound,
    ActionPermissionDenied,
    ActionValidationError,
    inspect_application,
)

Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class ActionAsgiAdapter:
    app: Any
    allowed_actions: set[str] = field(default_factory=set)
    path_prefix: str = "/actions"
    get_actions: set[str] = field(default_factory=set)

    @classmethod
    def from_application(
        cls,
        app: Any,
        *,
        allowed_actions: Iterable[str] | None = None,
        path_prefix: str = "/actions",
        get_actions: Iterable[str] | None = None,
    ) -> "ActionAsgiAdapter":
        return cls(
            app=app,
            allowed_actions=set(allowed_actions or ()),
            path_prefix=path_prefix,
            get_actions=set(get_actions or ()),
        )

    def list_actions(self) -> list[dict[str, Any]]:
        contract = inspect_application(self.app)
        return [
            action
            for action in contract.get("actions", [])
            if isinstance(action, dict) and action.get("name") in self.allowed_actions
        ]

    async def __call__(self, scope: dict[str, Any], receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self._send_problem(send, status=404, code="not_found", detail="Only HTTP scopes are supported.")
            return

        action_name = self._action_name(scope.get("path") or "/")
        if action_name is None:
            await self._send_problem(send, status=404, code="not_found", detail="Action endpoint not found.")
            return
        if action_name not in self.allowed_actions:
            await self._send_problem(
                send,
                status=404,
                code="action_not_exposed",
                detail=f"Action is not exposed over HTTP: {action_name}",
                action=action_name,
            )
            return

        method = str(scope.get("method") or "GET").upper()
        if method == "GET":
            if action_name not in self.get_actions:
                await self._send_problem(
                    send,
                    status=405,
                    code="method_not_allowed",
                    detail=f"GET is not enabled for action: {action_name}",
                    action=action_name,
                )
                return
            payload = self._query_payload(scope.get("query_string", b""))
        elif method == "POST":
            try:
                payload = self._json_payload(await self._read_body(receive))
            except ValueError as exc:
                await self._send_problem(send, status=400, code="invalid_json", detail=str(exc), action=action_name)
                return
        else:
            await self._send_problem(
                send,
                status=405,
                code="method_not_allowed",
                detail=f"Method is not supported for action bridge: {method}",
                action=action_name,
            )
            return

        try:
            result = ActionDispatcher(self.app).execute(
                action_name,
                payload,
                transport="http",
                metadata={"projection": "asgi"},
            )
            if result.is_stream:
                await self._send_problem(
                    send,
                    status=501,
                    code="stream_not_supported",
                    detail="HTTP action bridge does not stream action results; use muscles-sse for stream actions.",
                    action=action_name,
                )
                return
            await self._send_json(
                send,
                {
                    "action": result.action_name,
                    "result": result.value,
                    "metadata": dict(result.metadata),
                },
            )
        except Exception as exc:
            status, problem = self._problem_from_exception(exc)
            await self._send_json(send, problem, status=status, content_type="application/problem+json")

    def _action_name(self, path: str) -> str | None:
        prefix = self.path_prefix.rstrip("/") or "/"
        marker = prefix if prefix == "/" else f"{prefix}/"
        if prefix == "/":
            raw = path.lstrip("/")
        elif path.startswith(marker):
            raw = path[len(marker):]
        else:
            return None
        if not raw or "/" in raw:
            return None
        return unquote(raw)

    @staticmethod
    async def _read_body(receive: Receive) -> bytes:
        chunks: list[bytes] = []
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                continue
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        return b"".join(chunks)

    @staticmethod
    def _json_payload(body: bytes) -> dict[str, Any]:
        if not body:
            return {}
        payload = json.loads(body.decode("utf-8"))
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ValueError("Action payload must be a JSON object.")
        return payload

    @staticmethod
    def _query_payload(query_string: bytes) -> dict[str, Any]:
        query = parse_qs(query_string.decode("utf-8"), keep_blank_values=True)
        payload: dict[str, Any] = {}
        for key, values in query.items():
            payload[key] = values[0] if len(values) == 1 else values
        return payload

    @staticmethod
    def _problem_from_exception(exc: Exception) -> tuple[int, dict[str, Any]]:
        if isinstance(exc, ActionNotFound):
            return 404, ActionAsgiAdapter._problem_payload(exc, 404, "Action not found")
        if isinstance(exc, ActionValidationError):
            return 400, ActionAsgiAdapter._problem_payload(exc, 400, "Action validation failed")
        if isinstance(exc, ActionPermissionDenied):
            return 403, ActionAsgiAdapter._problem_payload(exc, 403, "Action permission denied")
        if isinstance(exc, ActionExecutionError):
            return 500, ActionAsgiAdapter._problem_payload(exc, 500, "Action execution failed")
        if isinstance(exc, ActionError):
            return exc.status, ActionAsgiAdapter._problem_payload(exc, exc.status, "Action error")
        return 500, {
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": str(exc),
            "code": "internal_error",
            "action": None,
            "data": None,
        }

    @staticmethod
    def _problem_payload(exc: ActionError, status: int, title: str) -> dict[str, Any]:
        return {
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": exc.message,
            "code": exc.code,
            "action": exc.action_name,
            "data": exc.data,
        }

    async def _send_problem(
        self,
        send: Send,
        *,
        status: int,
        code: str,
        detail: str,
        action: str | None = None,
    ) -> None:
        await self._send_json(
            send,
            {
                "type": "about:blank",
                "title": code.replace("_", " ").title(),
                "status": status,
                "detail": detail,
                "code": code,
                "action": action,
                "data": None,
            },
            status=status,
            content_type="application/problem+json",
        )

    @staticmethod
    async def _send_json(
        send: Send,
        payload: dict[str, Any],
        *,
        status: int = 200,
        content_type: str = "application/json",
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", content_type.encode("latin-1")),
                    (b"content-length", str(len(body)).encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})
