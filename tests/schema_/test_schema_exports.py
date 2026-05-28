import importlib.util

import muscles.asgi.schema_ as schema_


def test_adapter_schema_does_not_export_duplicate_itinerary():
    assert not hasattr(schema_, 'Itinerary')
    assert not hasattr(schema_, 'Node')
    assert importlib.util.find_spec('muscles.asgi.schema_.itinerary') is None
