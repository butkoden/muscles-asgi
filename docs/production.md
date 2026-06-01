# Muscles ASGI Production Notes

## Run With Uvicorn

```bash
uvicorn app.application:app --host 0.0.0.0 --port 8080 --workers 2
```

## Run With Hypercorn

```bash
hypercorn app.application:app --bind 0.0.0.0:8080
```

## Reverse Proxy

Use nginx or equivalent to terminate TLS and proxy to the ASGI runtime port.
