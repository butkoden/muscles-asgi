from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from muscles.core import get_application_registry, normalize_path


class _ProjectedRouteHandler:
    def __init__(self, route_record: dict[str, Any]):
        original_handler = route_record.get("handler")
        route_path = _route_path(route_record)
        canonical_route = _route_path({"route": route_record.get("canonical_route") or route_path})

        setattr(self, "__name__", getattr(original_handler, "__name__", route_record.get("key") or "unknown"))
        setattr(self, "__module__", getattr(original_handler, "__module__", ""))
        self.node = SimpleNamespace(
            key=route_record.get("key"),
            route=route_path,
            full_route=route_path,
        )
        self.method = getattr(original_handler, "method", None) or route_record.get("method")
        self.canonical_route = canonical_route
        self.aliases = [_normalize_path(alias) for alias in route_record.get("aliases", []) or []]
        self.actions = list(getattr(original_handler, "actions", []) or [])
        self.permission = route_record.get("permission", getattr(original_handler, "permission", None))
        self.permission_check = getattr(original_handler, "permission_check", "route")


def mount_api(app: Any, api: Any):
    setattr(api, "_owner", app)
    registry = get_application_registry(app)
    existing_signatures = {_route_signature(handler) for handler in getattr(registry, "routes", []) or []}

    for route_record in getattr(api, "nodes_map", []) or []:
        projected_handler = _ProjectedRouteHandler(route_record)
        permission = projected_handler.permission
        if permission is not None:
            permission_id = permission if isinstance(permission, str) else getattr(permission, "id", None)
            if not isinstance(permission_id, str) or permission_id not in registry.permissions:
                raise ValueError(f"Unknown route permission: {permission_id!r}")
            mode = getattr(route_record.get("handler"), "permission_check", "route")
            if mode not in ("route", "business"):
                raise ValueError(f"Invalid route permission check mode: {mode!r}")
            projected_handler.permission = permission_id
        signature = _route_signature(projected_handler)
        if signature in existing_signatures:
            continue
        registry.add_route(projected_handler)
        existing_signatures.add(signature)

    return api


def finalize_api(app: Any, api: Any):
    return mount_api(app, api)


def mount_application_apis(app: Any):
    get_application_registry(app).validate_permission_extensions()
    seen: set[int] = set()
    for api in _iter_application_apis(app):
        marker = id(api)
        if marker in seen:
            continue
        mount_api(app, api)
        seen.add(marker)
    return app


def _iter_application_apis(app: Any):
    for owner in (type(app), app):
        for value in vars(owner).values():
            if _looks_like_rest_api(value):
                yield value


def _looks_like_rest_api(value: Any) -> bool:
    return hasattr(value, "nodes_map") and hasattr(value, "swagger")


def _route_path(route_record: dict[str, Any]) -> str:
    return _normalize_path(route_record.get("route"))


def _normalize_path(value: Any) -> str:
    return normalize_path(str(value or "/"))


def _route_signature(handler: Any) -> tuple[Any, Any, Any]:
    node = getattr(handler, "node", None)
    route_path = getattr(node, "full_route", None) or getattr(node, "route", None)
    method = getattr(handler, "method", None)
    canonical = getattr(handler, "canonical_route", None) or route_path
    return (route_path, method or "*", canonical)
