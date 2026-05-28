import io
from muscles import JsonResponseBody
from muscles.asgi.asgi import AsgiStrategy, Request
from muscles.asgi.restful import RestApi
from muscles import Context
from muscles import ApplicationMeta
from muscles import Configurator


def start_response(status, headers):
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


def test_check_get_1():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v11/test',
        'PATH_INFO': '/api/v11/test',
        'CONTENT_TYPE': 'application/json',
    })

    class Muscular1(metaclass=ApplicationMeta):
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
                    "Test2": "controllers.test2",
                }
            }
        })

        context = Context(AsgiStrategy, {})

        def __init__(self):
            self.api1 = RestApi(
                prefix='/api/v11',
                version='11.0',
                name='ApiV11',
                title='Api v11',
                description='Системный Api',
                termsOfService='http://swagger.io/terms/',
                contact_email='**@**.info',
            )
            self.api2 = RestApi(
                prefix='/api/v12',
                version='12.0',
                name='ApiV12',
                title='Api v12',
                description='Системный Api',
                termsOfService='http://swagger.io/terms/',
                contact_email='**@**.info',
            )

            self.init_auto_packages(self.config)
            self.init_imports(self.config.api.controllers)

        def __call__(self, environ, start_response):
            self.context.set_param('environ', environ)
            self.context.set_param('start_response', start_response)
            return self.context.execute()

    muscular = Muscular1()

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
                                  200: JsonResponseBody(description='OK'),
                                  400: JsonResponseBody(description='Error 400'),
                                  404: JsonResponseBody(description='Not Found'),
                              })
        def get(self, request):
            return {
                "actor": request.actor,
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

    @muscular.api2.controller('/test',
                              description='Контроллер работы со списком пользователей и пользователями',
                              summary='РО'
                              )
    class Test2:
        """
        Controller
        """

        @muscular.api2.action(method='option')
        def option(self, request):
            return {
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

        @muscular.api2.action(method='get',
                              description='1 Контроллер работы со списком пользователей и пользователями',
                              summary='1 РО',
                              response={
                                  200: JsonResponseBody(description='OK'),
                                  400: JsonResponseBody(description='Error 400'),
                                  404: JsonResponseBody(description='Not Found'),
                              })
        def get(self, request):
            return {
                "actor": request.actor,
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

    @muscular.api1.before_request()
    def before_request_1(request):
        def call_test(request):
            return "CALL TEST 1"
        request.route['handler'] = call_test

    @muscular.api2.before_request()
    def before_request_2(request):
        def call_test(request):
            return "CALL TEST 2"
        request.route['handler'] = call_test

    muscular.context.strategy = AsgiStrategy
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'CALL TEST 1'

    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v12/test',
        'PATH_INFO': '/api/v12/test',
        'CONTENT_TYPE': 'application/json',
    })
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'CALL TEST 2'


def test_check_get_2():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v21/test',
        'PATH_INFO': '/api/v21/test',
        'CONTENT_TYPE': 'application/json',
    })

    class Muscular2(metaclass=ApplicationMeta):
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
                "default_version": "v21",
                "controllers": {
                    "Test": "controllers.test",
                    "Test2": "controllers.test2",
                }
            }
        })

        context = Context(AsgiStrategy, {})

        def __init__(self):
            self.api1 = RestApi(
                prefix='/api/v21',
                version='21.0',
                name='ApiV21',
                title='Api v1',
                description='Системный Api',
                termsOfService='http://swagger.io/terms/',
                contact_email='**@**.info',
            )
            self.api2 = RestApi(
                prefix='/api/v22',
                version='22.0',
                name='ApiV22',
                title='Api v22',
                description='Системный Api',
                termsOfService='http://swagger.io/terms/',
                contact_email='**@**.info',
            )

            self.init_auto_packages(self.config)
            self.init_imports(self.config.api.controllers)

        def __call__(self, environ, start_response):
            self.context.set_param('environ', environ)
            self.context.set_param('start_response', start_response)
            return self.context.execute()

    muscular = Muscular2()

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
                                  200: JsonResponseBody(description='OK'),
                                  400: JsonResponseBody(description='Error 400'),
                                  404: JsonResponseBody(description='Not Found'),
                              })
        def get(self, request):
            return {
                "actor": request.actor,
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

    @muscular.api2.controller('/test',
                              description='Контроллер работы со списком пользователей и пользователями',
                              summary='РО'
                              )
    class Test2:
        """
        Controller
        """

        @muscular.api2.action(method='option')
        def option(self, request):
            return {
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

        @muscular.api2.action(method='get',
                              description='1 Контроллер работы со списком пользователей и пользователями',
                              summary='1 РО',
                              response={
                                  200: JsonResponseBody(description='OK'),
                                  400: JsonResponseBody(description='Error 400'),
                                  404: JsonResponseBody(description='Not Found'),
                              })
        def get(self, request):
            return {
                "actor": request.actor,
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }


    ApiV1 = RestApi(name='ApiV21')
    ApiV2 = RestApi(name='ApiV22')

    @ApiV1.before_request()
    def before_request_1(request):
        def call_test(request):
            return "CALL TEST 3"
        request.route['handler'] = call_test

    @ApiV2.before_request()
    def before_request_2(request):
        def call_test(request):
            return "CALL TEST 4"
        request.route['handler'] = call_test

    muscular.context.strategy = AsgiStrategy

    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'CALL TEST 3'

    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v22/test',
        'PATH_INFO': '/api/v22/test',
        'CONTENT_TYPE': 'application/json',
    })
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'CALL TEST 4'


def test_check_get_3():
    """
    Проверяем работоспособность схемы
    :return:
    """
    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v31/test',
        'PATH_INFO': '/api/v31/test',
        'CONTENT_TYPE': 'application/json',
    })

    class Muscular3(metaclass=ApplicationMeta):
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
                prefix='/api/v31',
                version='31.0',
                name='ApiV31',
                title='Api v31',
                description='Системный Api',
                termsOfService='http://swagger.io/terms/',
                contact_email='**@**.info',
            )
            self.api2 = RestApi(
                prefix='/api/v32',
                version='32.0',
                name='ApiV32',
                title='Api v32',
                description='Системный Api',
                termsOfService='http://swagger.io/terms/',
                contact_email='**@**.info',
            )

            self.init_auto_packages(self.config)
            self.init_imports(self.config.api.controllers)

        def __call__(self, environ, start_response):
            self.context.set_param('environ', environ)
            self.context.set_param('start_response', start_response)
            return self.context.execute()

    muscular = Muscular3()

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
                                  200: JsonResponseBody(description='OK'),
                                  400: JsonResponseBody(description='Error 400'),
                                  404: JsonResponseBody(description='Not Found'),
                              })
        def get(self, request):
            return {
                "actor": request.actor,
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

    @muscular.api2.controller('/test',
                              description='Контроллер работы со списком пользователей и пользователями',
                              summary='РО'
                              )
    class Test2:
        """
        Controller
        """

        @muscular.api2.action(method='option')
        def option(self, request):
            return {
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

        @muscular.api2.action(method='get',
                              description='1 Контроллер работы со списком пользователей и пользователями',
                              summary='1 РО',
                              response={
                                  200: JsonResponseBody(description='OK'),
                                  400: JsonResponseBody(description='Error 400'),
                                  404: JsonResponseBody(description='Not Found'),
                              })
        def get(self, request):
            return {
                "actor": request.actor,
                "method": request.method,
                "request": {
                    "url": request.url,
                }
            }

    @Request.init_request()
    def init_request(request):
        request.actor = 1

    muscular.context.strategy = AsgiStrategy

    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"actor": 1, "method": "GET", "request": {"url": "http://localhost:8080/api/v31/test"}}'

    environ.update({
        'REQUEST_METHOD': 'GET',
        'REQUEST_URI': '/api/v32/test',
        'PATH_INFO': '/api/v32/test',
        'CONTENT_TYPE': 'application/json',
    })
    app = muscular(environ, start_response)
    for pr in app:
        assert pr == b'{"actor": 1, "method": "GET", "request": {"url": "http://localhost:8080/api/v32/test"}}'

