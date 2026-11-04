import asyncio
from muscles.asgi.asgi.strategy import AsgiStrategy


def test_asgi_strategy_reuses_server_instance_between_requests():
    class DummyTransport:
        init_calls = 0

        def __init__(self):
            pass

        def init_server(self, server):
            DummyTransport.init_calls += 1
            self.server = server

        async def execute(self, *args, **kwargs):
            return "ok"

    strategy = AsgiStrategy()
    first = asyncio.run(strategy.execute(scope={}, receive=None, send=None, transport=DummyTransport))
    server_id_first = id(strategy._server)
    second = asyncio.run(strategy.execute(scope={}, receive=None, send=None, transport=DummyTransport))
    server_id_second = id(strategy._server)

    assert first == "ok"
    assert second == "ok"
    assert server_id_first == server_id_second
    assert DummyTransport.init_calls == 1
