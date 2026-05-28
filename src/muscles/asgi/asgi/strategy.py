import asyncio
import io
import logging
from typing import Optional

from muscles.core import BaseStrategy
from watchdog.events import LoggingEventHandler
from .server import AsgiTransport, AsgiServer
from .error_handler import ResponseErrorHandler

event_handler = LoggingEventHandler()


class AsgiStrategy(BaseStrategy):
    """
    Стратегия ASGI сервера
    """

    def execute(self, *args, error_handler: Optional[ResponseErrorHandler] = None, **kwargs):
        """
        Запускаем обработку запросов
        :param args:
        :param error_handler:
        :param kwargs:
        :return:
        """
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 8080)
        logger = kwargs.get('logger')
        container = kwargs.get('container')
        if logger is None and container is not None:
            logger = getattr(container, "logger", None)
        if isinstance(logger, str):
            logger = logging.getLogger(logger)
        if logger is None:
            logger = logging.getLogger("muscles.asgi")
        debug = bool(kwargs.get('debug', False))

        server = AsgiServer(host, port, error_handler=error_handler, logger=logger, debug=debug)
        transport = kwargs.get('transport', AsgiTransport)
        server.init_transport(transport)
        if 'environ' in kwargs and 'scope' not in kwargs:
            return self._execute_wsgi_compatible(server, **kwargs)
        return server.execute(*args, **kwargs)

    def _execute_wsgi_compatible(self, server, **kwargs):
        environ = kwargs['environ']
        start_response = kwargs.get('start_response')
        body = self._read_wsgi_body(environ)
        sent = []

        async def receive():
            return {
                'type': 'http.request',
                'body': body,
                'more_body': False,
            }

        async def send(message):
            sent.append(message)

        scope = self._scope_from_environ(environ)
        asyncio.run(server.execute(scope=scope, receive=receive, send=send))

        status = 200
        headers = []
        chunks = []
        for message in sent:
            if message['type'] == 'http.response.start':
                status = message.get('status', status)
                headers = message.get('headers', headers)
            elif message['type'] == 'http.response.body':
                chunks.append(message.get('body', b''))

        if start_response is not None:
            start_response(str(status), headers)
        return chunks

    def _read_wsgi_body(self, environ):
        stream = environ.get('wsgi.input', io.BytesIO())
        try:
            length = int(environ.get('CONTENT_LENGTH', 0) or 0)
        except (TypeError, ValueError):
            length = 0
        return stream.read(length) if length else b''

    def _scope_from_environ(self, environ):
        path = environ.get('PATH_INFO') or environ.get('REQUEST_URI') or '/'
        if '?' in path:
            path, query_string = path.split('?', 1)
        else:
            query_string = environ.get('QUERY_STRING', '')
        scheme = environ.get('UWSGI_ROUTER') or environ.get('wsgi.url_scheme') or 'http'
        host = environ.get('HTTP_HOST') or environ.get('SERVER_NAME') or 'localhost'
        headers = []
        if 'CONTENT_TYPE' in environ:
            headers.append((b'content-type', str(environ['CONTENT_TYPE']).encode()))
        if 'CONTENT_LENGTH' in environ:
            headers.append((b'content-length', str(environ['CONTENT_LENGTH']).encode()))
        headers.append((b'host', str(host).encode()))
        for key, value in environ.items():
            if key.startswith('HTTP_') and key != 'HTTP_HOST':
                name = key[5:].lower().replace('_', '-').encode()
                headers.append((name, str(value).encode()))
        return {
            'type': 'http',
            'method': environ.get('REQUEST_METHOD', 'GET'),
            'scheme': scheme,
            'path': path,
            'raw_path': path.encode(),
            'query_string': query_string.encode(),
            'headers': headers,
            'server': (
                environ.get('SERVER_NAME', 'localhost'),
                int(environ.get('SERVER_PORT', 80)),
            ),
            'client': (
                environ.get('REMOTE_ADDR', ''),
                int(environ.get('REMOTE_PORT', 0)),
            ),
        }
