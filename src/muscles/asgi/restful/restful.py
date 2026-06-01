import os.path
import re

from muscles.core import EventsStorageInterface, inject
from muscles.core import Itinerary
from ..asgi import Routes
from ..template import Template
from muscles.core import Schema
from .swagger import Swagger


class RestApi(Itinerary):

    def __before_init__(self, *args, **kwargs):
        tpl_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
        template = Template(templates=tpl_path)

        routers = Routes()

        prefix = kwargs.get('prefix', '/')
        schema_url = kwargs.get('schema_url', 'schema')

        self.swagger = Swagger(
            name=kwargs.get('name', 'default'),
            title=kwargs.get('title', 'Simple Api'),
            prefix=prefix,
            version=kwargs.get('version', '1.0'),
            openapi_version=kwargs.get('openapi_version', '3.0.3'),
            schema_url=re.sub("//+", "/", '/'.join([prefix, schema_url])),
            description=kwargs.get('description', None),
            termsOfService=kwargs.get('termsOfService', None),
            contact_email=kwargs.get('contact_email', None),
            servers=kwargs.get('servers', None),
            security=kwargs.get('security', []),
        )

        def _swagger(request):
            return template('templates/swagger.jinja2', swagger=self.swagger)

        def _schema(request):
            swagger = Swagger.load(request.path) or self.swagger
            return swagger.dump()

        super().add(schema_url, handler=_schema)
        routers.add(kwargs.get('swagger_url', '/swagger'), method="GET", handler=_swagger)
        routers.add(kwargs.get('docs_url', '/docs'), method="GET", handler=_swagger)
        routers.add(kwargs.get('openapi_url', '/openapi.json'), method="GET", handler=_schema)
        self.install = True

    def _trigger_set_handler(self, handler, *args, tags: list = None, description: str = None, summary: str = None,
                             request: list = [], security: list = [], response: dict = {}, parameters: list = [],
                             **kwargs):
        if not hasattr(handler, 'description') or not handler.description:
            handler.description = description
        if not hasattr(handler, 'summary') or not handler.summary:
            handler.summary = summary
        if not hasattr(handler, 'request') or not handler.request:
            handler.request = request
        if not hasattr(handler, 'security') or not handler.security:
            handler.security = security
        if not hasattr(handler, 'response') or not handler.response:
            handler.response = response
        if not hasattr(handler, 'parameters') or not handler.parameters:
            handler.parameters = parameters
        else:
            handler.parameters = handler.parameters + parameters

        return handler

    def _trigger_set_controller(self, handler, *args, tags: list = None, description: str = None, summary: str = None,
                                request: list = [], security: list = [], response: dict = {}, parameters: list = [],
                                **kwargs):
        self.swagger.tags.append({
            "name": handler.__name__,
            "description": handler.__doc__,
            # "externalDocs": {
            #     "description": "Find out more",
            #     "url": "http://swagger.io"
            # }
        })
        return handler

    def add(self, route, key=None, handler=None, method: str = '*', content_type: str = '*/*',
            redirect: str = None, module=None):
        """

        :param route:
        :param key:
        :param handler:
        :param method:
        :param content_type:
        :param redirect:
        :param module:
        :param tags:
        :param description:
        :param summary:
        :param request:
        :param security:
        :param response:
        :param parameters:
        :param kwargs:
        :return:
        """
        handler = super().add(route, key=key, handler=handler, method=method, content_type=content_type,
                              redirect=redirect, module=module)
        self.swagger(handler=handler, node=handler.node, module=module)

    def init(self, route, key=None, module=None, method: str = '*', content_type: str = '*/*', redirect: str = None,
             tags: list = None, description: str = None, summary: str = None, request: list = [], security: list = [],
             response: dict = {}, parameters: list = [], **kwargs):
        """
        Декоратор функции обработки маршрута

        :param parameters:
        :param response:
        :param security:
        :param request:
        :param summary:
        :param tags:
        :param description:
        :param route: Маршрут
        :param key: Ключ маршрута
        :param module: Настройки модуля обработки
        :param method: Метод маршрута
        :param content_type: Тип контента маршрута
        :param redirect: Редирект, для маршрута
        :return:
        """
        decorator = super().init(route, key=key, module=module, method=method, content_type=content_type,
                                 redirect=redirect, tags=tags, description=description, summary=summary,
                                 request=request, security=security, response=response, parameters=parameters, **kwargs)
        return decorator

    def controller(self, route, model: Schema = None, tags: list = None, description: str = None, summary: str = None,
                   request: list = [], security: list = [], response: dict = {}, parameters: list = [], **kwargs):
        """
        Регистрация контроллера для обработки запросов классом

        :param request:
        :param security:
        :param tags:
        :param description:
        :param summary:
        :param parameters:
        :param response:
        :param model: Модель данных
        :param route: Маршрут
        :return:
        """
        decorator = super().controller(route, model=model, tags=tags, description=description, summary=summary,
                                       request=request, security=security, response=response, parameters=parameters,
                                       **kwargs)
        return decorator

    def action(self, route=None, key=None, module=None, method: str = '*', content_type: str = '*/*',
               redirect: str = None, model: Schema = None, tags: list = None, description: str = None,
               summary: str = None, request: list = [], security: list = [], response: dict = {},
               parameters: list = [], **kwargs):
        """
        Регистрация "действия" для контроллера.
        Внимание: Работает только совместно с регистрацией контроллера с помощью метода controller

        :param parameters:
        :param response:
        :param security:
        :param request:
        :param summary:
        :param description:
        :param tags:
        :param model: Модель данных
        :param route: Маршрут
        :param key: Ключ маршрута
        :param module: Настройки модуля обработки
        :param method: Метод маршрута
        :param content_type: Тип контента маршрута
        :param redirect: Редирект, для маршрута
        :return:
        """
        decorator = super().action(route=route, key=key, module=module, method=method, content_type=content_type,
                                   redirect=redirect, model=model, tags=tags, description=description, summary=summary,
                                   request=request, security=security, response=response, parameters=parameters,
                                   **kwargs)
        return decorator

    @inject(EventsStorageInterface)
    def before_request(self, evnetStorage: EventsStorageInterface):
        """
        Декоратор обработчика запросов

        :return:
        """
        def decorator(func):
            self.add_event('before_request', func)
        return decorator
