import io
import json
import logging
import sys

from muscles import JsonResponseBody
from muscles import XmlResponseBody
from muscles import MultipartRequestBody
from muscles import PathParameter
from muscles import CookieParameter
from muscles import HeaderParameter
from muscles import QueryParameter
from muscles import JsonRequestBody
from muscles.asgi.asgi import AsgiStrategy
from muscles.asgi.restful import RestApi
from muscles import Context
from muscles import ApplicationMeta
from muscles import Configurator
from muscles import Model, Column, Key, Numeric, List, String, Enum, Date, DateTime


class User(Model):
    id = Column(Key)
    name = Column(String, index=True)
    email = Column(String, index=True)
    status = Column(Enum(enum=['inactive', 'deleted', 'blocked', 'active']), index=True)
    birthday = Column(Date)
    created_at = Column(DateTime)


def start_response(status, headers):
    pass


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

@muscular.api1.controller('/test',
                          description='Контроллер работы со списком пользователей и пользователями',
                          summary='РО'
                          )
class Test:
    """
    Controller
    """

    @muscular.api1.action(method='option')
    def option(self, request):
        return {
            "method": request.method,
            "request": {
                "url": request.url,
            }
        }

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
        return {
            "method": request.method,
            "request": {
                "url": request.url,
            }
        }

    @muscular.api1.action(method='post',
                          request=[
                              JsonRequestBody(description='Json', model=User),
                              MultipartRequestBody(description='Form', model=User),
                          ],
                          response={
                              200: JsonResponseBody(description='OK'),
                              400: JsonResponseBody(description='Error 400'),
                              404: JsonResponseBody(description='Not Found'),
                          })
    def post(self, request):
        return {
            "method": request.method,
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

    @muscular.api1.action(method='delete',
                          request=[
                              JsonRequestBody(description='Json', model=User),
                              MultipartRequestBody(description='Form', model=User),
                          ],
                          response={
                              200: JsonResponseBody(description='OK'),
                              400: JsonResponseBody(description='Error 400'),
                              404: JsonResponseBody(description='Not Found'),
                          })
    def delete(self, request):
        return {
            "method": request.method,
        }

    @muscular.api1.action(method='put',
                          request=[
                              JsonRequestBody(description='Json', model=User),
                              MultipartRequestBody(description='Form', model=User),
                          ],
                          response={
                              200: JsonResponseBody(description='OK'),
                              400: JsonResponseBody(description='Error 400'),
                              404: JsonResponseBody(description='Not Found'),
                          })
    def put(self, request):
        return {
            "method": request.method,
        }

    @muscular.api1.action(route="/{id}",
                          method='get',
                          parameters=[
                              HeaderParameter('Header', Numeric, required=False, description='Header'),
                              CookieParameter('csrftoken', String, required=False, description='Cookie'),
                              PathParameter('id', Numeric, required=True, description='Path ID'),
                              QueryParameter('query1', List(Enum(enum=['one', 'two'])), required=False,
                                             description='Query1'),
                              QueryParameter('query2', Enum(enum=['one', 'two']), required=False, description='Query2'),
                          ],
                          request=[
                              JsonRequestBody(description='Json', model=User),
                              MultipartRequestBody(description='Form', model=User),
                          ],
                          response={
                              200: [
                                  JsonResponseBody(description='OK', model=User),
                                  XmlResponseBody(description='OK'),
                              ],
                              400: JsonResponseBody(description='Error 400'),
                              404: JsonResponseBody(description='Not Found'),
                          })
    def show(self, request, id):
        return {
            "id": id,
            "method": request.method,
            "request": {
                "url": request.url,
            }
        }

    @muscular.api1.action(route="/{id}",
                          method='post',
                          request=[
                              JsonRequestBody(description='Json', model=Column("name", String, index=True))
                          ])
    def change(self, request, id):
        return {
            "id": id,
            "method": request.method,
            "request": {
                "url": request.url,
            }
        }

    @muscular.api1.action(route="/{id}", method='delete')
    def drop(self, request, id):
        return {
            "id": id,
            "method": request.method,
            "request": {
                "url": request.url,
            }
        }


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


def test_check_instance():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v1/test',
        'PATH_INFO': '/api/v1/test',
        'CONTENT_TYPE': 'application/json',
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"method": "GET", "request": {"url": "http://localhost:8080/api/v1/test"}}'

    api1 = RestApi(name='ApiV1')

    @api1.controller('/test2',
                     description='Контроллер работы со списком пользователей и пользователями',
                     summary='РО'
                     )
    class Test2:
        """
        Controller
        """

        @api1.action(method='option')
        def option(self, request):
            return {
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

        @api1.action(method='get',
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
            return {
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v1/test2',
        'PATH_INFO': '/api/v1/test2',
        'CONTENT_TYPE': 'application/json',
    })
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"method": "GET", "request": {"url": "http://localhost:8080/api/v1/test2"}}'

    log_stream = io.StringIO()
    logger = logging.getLogger("muscles.router")
    handler = logging.StreamHandler(log_stream)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    muscular.api1.print_tree()
    api1.print_tree()
    logger.removeHandler(handler)
    output = log_stream.getvalue().strip()
    assert ".  /api    [ key:None]" in output
    assert ". .  /v1    [ key:None]" in output
    assert ". . .  /schema    [* key:api.v1.schema]" in output
    assert ". . .  /test    [OPTION,GET,POST,DELETE,PUT key:api.v1.test]" in output
    assert ". . . .  /{id:var}    [GET,POST,DELETE key:api.v1.test.{id}]" in output
    assert ". . .  /test2    [OPTION,GET key:api.v1.test2]" in output


def test_check_get():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v1/test',
        'PATH_INFO': '/api/v1/test',
        'CONTENT_TYPE': 'application/json',
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"method": "GET", "request": {"url": "http://localhost:8080/api/v1/test"}}'


def test_check_post():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'POST',
        'REQUEST_URI': '/api/v1/test',
        'PATH_INFO': '/api/v1/test',
        'CONTENT_TYPE': 'application/json',
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        pr = json.loads(pr)
        assert pr['method'] == "POST"


def test_check_delete():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'DELETE',
        'REQUEST_URI': '/api/v1/test',
        'PATH_INFO': '/api/v1/test',
        'CONTENT_TYPE': 'application/json',
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"method": "DELETE"}'


def test_check_put():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'PUT',
        'REQUEST_URI': '/api/v1/test',
        'PATH_INFO': '/api/v1/test',
        'CONTENT_TYPE': 'application/json',
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"method": "PUT"}'


def test_check_show():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v1/test/1',
        'PATH_INFO': '/api/v1/test/1',
        'CONTENT_TYPE': 'application/json',
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"id": "1", "method": "GET", "request": {"url": "http://localhost:8080/api/v1/test/1"}}'


def test_check_change():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'POST',
        'REQUEST_URI': '/api/v1/test/1',
        'PATH_INFO': '/api/v1/test/1',
        'CONTENT_TYPE': 'application/json',
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"id": "1", "method": "POST", "request": {"url": "http://localhost:8080/api/v1/test/1"}}'


def test_check_drop():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'DELETE',
        'REQUEST_URI': '/api/v1/test/1',
        'PATH_INFO': '/api/v1/test/1',
        'CONTENT_TYPE': 'application/json',
    })
    muscular = Muscular()
    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"id": "1", "method": "DELETE", "request": {"url": "http://localhost:8080/api/v1/test/1"}}'
