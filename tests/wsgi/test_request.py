import io
import os
import asyncio

from muscles import JsonResponseBody
from muscles import XmlResponseBody
from muscles import MultipartRequestBody
from muscles import PathParameter
from muscles import JsonRequestBody
from muscles.asgi.asgi import AsgiStrategy
from muscles.asgi.restful import RestApi
from muscles import Context
from muscles import ApplicationMeta
from muscles import Configurator
from muscles import Model, Column, Key, Numeric, List, String, Enum, Date, DateTime
from muscles.asgi.asgi.request import RequestMaker


def start_response(status, headers):
    pass


class User(Model):
    id = Column(Key)
    name = Column(String, index=True)
    email = Column(String, index=True)
    status = Column(Enum(enum=['inactive', 'deleted', 'blocked', 'active']), index=True)
    birthday = Column(Date)
    created_at = Column(DateTime)


class Muscular(metaclass=ApplicationMeta):
    package_paths = []
    shutup = False

    config = Configurator(obj={
        "main": {
            "BASEDIR": ".",
            "BASE_URL": "localhost: 5050",
            "SERVER_NAME": "localhost: 5050",
            "HOST": "localhost",
            "PORT": "5050",
            "ENV": "production",
            "DEBUG": False,
            "TIMEZONE": "UTC",
            "MAIN_ROUTE": "page.index",
            "SQLALCHEMY_DATABASE_URI": "SQLALCHEMY_DATABASE_URI",
            "SQLALCHEMY_TRACK_MODIFICATIONS": True,
            "SQLALCHEMY_ON": True,
            "PROJECT_ROOT": ".",
            "STATICFILES_DIRS": "static",
            "SESSION_KEY_PREFIX": "session",
            "SESSION_TYPE": "filesystem",
            "SECRET_KEY": "dhU73jslvbglsjg&20lfjsl",
        },
        "routes": {
            "prefix": '',
        },
        "api": {
            "prefix": "/api",
            "default_version": "v1",
            "controllers": {
                "Test": "controllers.test",
                "TestRequest": "controllers.request",
            }
        }
    })

    context = Context(AsgiStrategy, {})

    def __init__(self):
        self.api1 = RestApi(
            prefix='/api/v1',
            version='1.0',
            name='ApiV1',
            title='Api v1',
            description='Системный Api',
            termsOfService='http://swagger.io/terms/',
            contact_email='**@**.info',
        )

        self.init_auto_packages(self.config)
        # self.init_imports(self.config.models)
        self.init_imports(self.config.api.controllers)

    @context.before_start()
    def before_start(self_context):
        # print('>>>>>>>>>>>>before_start')
        pass

    @context.after_start()
    def after_start(self_context, result):
        # print('>>>>>>>>>>>>after_start', result)
        pass

    def run(self, *args):
        return self.context.execute(*args, shutup=self.shutup)

    def __call__(self, environ, start_response):
        self.context.set_param('environ', environ)
        self.context.set_param('start_response', start_response)
        return self.context.execute()


muscular = Muscular()


async def _empty_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


def test_request_maker_normalizes_path_and_keeps_query_string():
    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "http",
        "path": "//api//documents//",
        "raw_path": b"//api//documents//",
        "query_string": b"page=1",
        "headers": [(b"host", b"example.test")],
        "server": ("example.test", 80),
        "client": ("127.0.0.1", 1234),
    }

    request = asyncio.run(RequestMaker(scope, _empty_receive).make())

    assert request.path == "/api/documents"
    assert request.query == {"page": "1"}


def test_request_url_helpers_are_runtime_safe():
    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "https",
        "path": "/api/documents",
        "raw_path": b"/api/documents",
        "query_string": b"page=1",
        "headers": [(b"host", b"example.test:8443")],
        "server": ("example.test", 8443),
        "client": ("127.0.0.1", 1234),
    }

    request = asyncio.run(RequestMaker(scope, _empty_receive).make())

    assert request.base_url == "https://example.test:8443/api/documents"
    assert request.host_url == "https://example.test:8443"
    assert request.host == "https://example.test:8443"


@muscular.api1.controller('/test_request',
                          description='Контроллер работы со списком пользователей и пользователями',
                          summary='РО'
                          )
class TestRequest:
    """
    Пользователи
    """

    @muscular.api1.action(method='option')
    def option(self, request):
        pass

    @muscular.api1.action(method='get',
                          description='1 Контроллер работы со списком пользователей и пользователями',
                          summary='1 РО',
                          response={
                              200: [
                                  JsonResponseBody(description='OK', model=User),
                                  XmlResponseBody(description='OK'),
                              ],
                              400: JsonResponseBody(description='Error 400'),
                              404: JsonResponseBody(description='Not Found'),
                          })
    def get(self, request):
        return {"dd": 12}

    @muscular.api1.action(method='post',
                          request=[MultipartRequestBody(description='Form', model=User)],
                          response={
                              200: JsonResponseBody(description='OK', model=User),
                          })
    def post(self, request):
        return {
            "request": {
                "url": request.url,
                "headers": request.headers,
                "query": request.query,
                "content_type": request.content_type,
                "cookies": request.cookies,
                "is_json": request.is_json,
                "forms": request.forms,
                "files": request.files,
                "body": request.body,
            }
        }

    @muscular.api1.action(route="/{id}",
                          method='post',
                          parameters=[
                              PathParameter('id', Numeric, required=True, description='Path ID'),
                          ],
                          request=[MultipartRequestBody(description='Form', model=User)],
                          response={
                              200: JsonResponseBody(description='OK', model=User),
                          })
    def show(self, request, id):
        return {
            "dd": id,
            "json": request.json,
            "forms": request.forms,
            "files": request.files,
            "request": {
                "url": request.url,
            }
        }

    @muscular.api1.action(route="/{id}/raw",
                          method='post',
                          parameters=[
                              PathParameter('id', Numeric, required=True, description='Path ID'),
                          ],
                          request=[MultipartRequestBody(description='Form', model=User)],
                          response={
                              200: JsonResponseBody(description='OK', model=User),
                          })
    def show1(self, request, id):
        return {
            "dd": id,
            "raw": request.raw,
            "forms": request.forms,
            "files": request.files,
            "request": {
                "url": request.url,
            }
        }

    @muscular.api1.action(request=[
        JsonRequestBody(description='Json', model=Column("name", String, index=True))
    ])
    def put(self, request, id):
        pass

    @muscular.api1.action(method='delete')
    def delete(self, request, id):
        pass


environ = {
    'REQUEST_METHOD': 'GET',
    'REQUEST_URI': '/api/v1/test',
    'PATH_INFO': '/api/v1/test',
    'QUERY_STRING': '',
    'SERVER_PROTOCOL': 'HTTP/1.1',
    'SCRIPT_NAME': '',
    'SERVER_NAME': 'a0c8b2e9a5a7',
    'SERVER_PORT': '8080',
    'UWSGI_ROUTER': 'http',
    'REMOTE_ADDR': '172.22.0.1',
    'REMOTE_PORT': '34030',
    'HTTP_X_API_TOKEN': 'hfHfdjfr746Hfkdbd3uhHdl',
    'HTTP_USER_AGENT': 'PostmanRuntime/7.29.2',
    'HTTP_ACCEPT': '*/*',
    'HTTP_CACHE_CONTROL': 'no-cache',
    'HTTP_POSTMAN_TOKEN': '2241d11b-aeb6-4ed1-a0d3-c120168d96b6',
    'HTTP_HOST': 'localhost:8080',
    'HTTP_ACCEPT_ENCODING': 'gzip, deflate, br', 'HTTP_CONNECTION': 'keep-alive',
    'wsgi.input': io.BytesIO(),
    'wsgi.version': (1, 0),
    'wsgi.errors': io.BytesIO(),
    'wsgi.run_once': False,
    'wsgi.multithread': False,
    'wsgi.multiprocess': False,
    'wsgi.url_scheme': 'http',
    'uwsgi.version': b'2.0.20',
    'uwsgi.node': b'a0c8b2e9a5a7'
}


def test_send_json():
    """
    Проверяем работоспособность схемы
    :return:
    """
    string = b'{"j": 1}'
    environ.update({
        'REQUEST_METHOD': 'POST',
        'REQUEST_URI': '/api/v1/test_request/1',
        'PATH_INFO': '/api/v1/test_request/1',
        'CONTENT_TYPE': 'application/json',
        'wsgi.input': io.BytesIO(string),
        'CONTENT_LENGTH': len(string),
    })

    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    muscular.api1.print_tree()
    for pr in app:
        assert pr == b'{"dd": "1", "json": {"j": 1}, ' \
                     b'"forms": null, "files": null, ' \
                     b'"request": {"url": "http://localhost:8080/api/v1/test_request/1"}}'


def test_send_multipart():
    """
    Проверяем работоспособность схемы
    :return:
    """
    from requests_toolbelt.multipart.encoder import MultipartEncoder
    mp_encoder = MultipartEncoder(
        fields={
            'foo': 'bar',
            'image': (
                '6152749397.jpg', open(os.path.join(os.path.dirname(__file__), '6152749397.jpg'), 'rb'), 'image/jpg'),
        }
    )
    environ.update({
        'REQUEST_METHOD': 'POST',
        'REQUEST_URI': '/api/v1/test_request/1',
        'PATH_INFO': '/api/v1/test_request/1',
        'CONTENT_TYPE': mp_encoder.content_type,
        'wsgi.input': io.BytesIO(mp_encoder.to_string()),
        'CONTENT_LENGTH': int(1421),
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"dd": "1", "json": {}, "forms": {"foo": "bar"}, ' \
                     b'"files": {"image": "FileStorage(\'image/jpeg\', \'6152749397.jpg\')"}, ' \
                     b'"request": {"url": "http://localhost:8080/api/v1/test_request/1"}}'


def test_send_form():
    """
    Проверяем работоспособность схемы
    :return:
    """
    string = b'dd=1&d2=2&d2=3'
    environ.update({
        'REQUEST_METHOD': 'POST',
        'REQUEST_URI': '/api/v1/test_request/1',
        'PATH_INFO': '/api/v1/test_request/1',
        'CONTENT_TYPE': 'application/x-www-form-urlencoded',
        'wsgi.input': io.BytesIO(string),
        'CONTENT_LENGTH': int(14),
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"dd": "1", "json": {}, "forms": {"dd": "1", "d2": ["2", "3"]}, "files": {}, ' \
                     b'"request": {"url": "http://localhost:8080/api/v1/test_request/1"}}'


def test_send_file():
    """
    Проверяем работоспособность схемы
    :return:
    """
    file = os.path.join(os.path.dirname(__file__), '6152749397.jpg')
    fp = open(file, 'rb')
    environ.update({
        'REQUEST_METHOD': 'POST',
        'REQUEST_URI': '/api/v1/test_request/1/raw',
        'PATH_INFO': '/api/v1/test_request/1/raw',
        'CONTENT_TYPE': 'image/jpeg',
        'wsgi.input': fp,
        'CONTENT_LENGTH': os.stat(file).st_size,
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"dd": "1", "raw": "FileStorage(\'image/jpeg\', None)", "forms": null, ' \
                     b'"files": null, "request": {"url": "http://localhost:8080/api/v1/test_request/1/raw"}}'
