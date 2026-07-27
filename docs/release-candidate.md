# ASGI RC checklist

`muscles-asgi` is released only after the core version range resolves from the
package index and the wheel imports without a sibling checkout.

```bash
PYTHONPATH=../muscles/src:src python -m pytest --import-mode=importlib -q
python -m build --wheel --sdist
```

The production entrypoint, lifecycle, request isolation, OpenAPI and action
bridge are covered by the package tests. Stream actions use `muscles-sse`.
Deployment guidance is in [production.md](production.md).
