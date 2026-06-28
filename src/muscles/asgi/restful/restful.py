import os.path
import re

from muscles.core import EventsStorageInterface, inject
from muscles.core import Itinerary
from muscles.core import build_route_aliases
from ..template import Template
from muscles.core import Schema
from .swagger import Swagger


class RestApi(Itinerary):

    def __before_init__(self, *args, **kwargs):
        tpl_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
        template = Template(templates=tpl_path)

        prefix = kwargs.get('prefix', '/')
        schema_url = kwargs.get('schema_url', 'schema')
        docs_url = kwargs.get('docs_url', '/docs')
        swagger_url = kwargs.get('swagger_url', '/swagger')
        openapi_url = kwargs.get('openapi_url', '/openapi.json')
        canonical_alias_map = build_route_aliases(prefix=prefix, schema_url=schema_url, swagger_url=swagger_url,
                                                 openapi_url=openapi_url, docs_url=docs_url)

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

        def _aliases_for(canonical_route):
            return sorted(
                [alias for alias, target in canonical_alias_map["aliases"].items() if target == canonical_route]
            )

        def _health(request):
            return {"status": "ok", "service": kwargs.get('name', 'default')}

        canonical_openapi = canonical_alias_map["canonical"]["openapi"]
        canonical_docs = canonical_alias_map["canonical"]["docs"]
        canonical_redoc = canonical_alias_map["canonical"]["redoc"]
        canonical_healthz = canonical_alias_map["canonical"]["healthz"]
        canonical_ready = canonical_alias_map["canonical"]["ready"]
        canonical_live = canonical_alias_map["canonical"]["live"]

        normalized_prefix = re.sub("//+", "/", f"/{prefix.strip('/')}" if prefix else "/")

        def _expand_with_root_aliases(route: str, aliases: list[str]) -> list[str]:
            paths = [route]
            paths.extend(aliases)
            if normalized_prefix != "/" and route:
                for source_path in [route, *aliases]:
                    source_path = re.sub("//+", "/", source_path)
                    if source_path == normalized_prefix:
                        paths.append("/")
                    elif source_path.startswith(f"{normalized_prefix}/"):
                        paths.append(source_path[len(normalized_prefix):])
            uniq_paths = []
            for item in paths:
                if item not in uniq_paths:
                    uniq_paths.append(item)
            return uniq_paths

        openapi_aliases = [alias for alias in _aliases_for(canonical_openapi) if alias != canonical_openapi]
        docs_aliases = [alias for alias in _aliases_for(canonical_docs) if alias != canonical_docs]
        healthz_aliases = [alias for alias in _aliases_for(canonical_healthz) if alias != canonical_healthz]

        original_prefix = self.prefix
        self.prefix = None
        for path in _expand_with_root_aliases(canonical_openapi, openapi_aliases):
            super().add(path, handler=_schema, canonical_route=canonical_openapi, aliases=openapi_aliases)
        for path in _expand_with_root_aliases(canonical_docs, [*docs_aliases, canonical_redoc]):
            super().add(path, handler=_swagger, canonical_route=canonical_docs, aliases=docs_aliases)
        for path in _expand_with_root_aliases(canonical_healthz, healthz_aliases):
            super().add(path, handler=_health, canonical_route=canonical_healthz, aliases=healthz_aliases)
        for path in _expand_with_root_aliases(canonical_ready, [canonical_live]):
            super().add(path, handler=_health, canonical_route=path, aliases=[])
        self.prefix = original_prefix
        self.install = True

    def _trigger_set_handler(self, handler, *args, tags: list = None, description: str = None, summary: str = None,
                             request: list = [], security: list = [], response: dict = {}, parameters: list = [],
                             **kwargs):
        if not hasattr(handler, 'tags') or not handler.tags:
            handler.tags = tags or []
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
        for key, value in kwargs.items():
            if key.startswith("_"):
                continue
            if value in (None, [], {}, "") and hasattr(handler, key):
                continue
            setattr(handler, key, value)

        return handler

    def _trigger_set_controller(self, handler, *args, tags: list = None, description: str = None, summary: str = None,
                                request: list = [], security: list = [], response: dict = {}, parameters: list = [],
                                stateful: bool = False,
                                **kwargs):
        self.swagger.tags.append({
            "name": handler.__name__,
            "description": handler.__doc__,
            # "externalDocs": {
            #     "description": "Find out more",
            #     "url": "http://swagger.io"
            # }
        })
        if not hasattr(handler, 'stateful_controller'):
            handler.stateful_controller = stateful
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
                   request: list = [], security: list = [], response: dict = {}, parameters: list = [],
                   stateful: bool = False, **kwargs):
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
        :param stateful: Не кэшировать инстанс контроллера между запросами
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
