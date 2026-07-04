import importlib.util


def test_asgi_schema_duplicate_package_is_removed():
    assert importlib.util.find_spec("muscles.asgi.schema_") is None
