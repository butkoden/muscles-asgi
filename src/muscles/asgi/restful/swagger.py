from typing import Any, cast

from muscles.core import Schema
from muscles.core import Model
from muscles.core import Collection
from muscles.core import BaseSecurity
from muscles.core import to_openapi_schema
import inspect
import re


class Swagger(Schema):

    _urls = []
    _instances = {}
    legal_http_method = ['get', 'post', 'put', 'delete', 'head', 'patch', 'options', 'trace', 'connect']

    def __new__(cls, *args, name: str | None = None, **kwargs):
        if name not in cls._instances:
            cls._instances[name] = object.__new__(cls)
        return cls._instances[name]

    def __init__(self, *args, name: str | None = None, schema_url: str | None = None,
                 prefix: str | None = None, version: str | None = None,
                 openapi_version: str | None = None,
                 title: str | None = None, description: str | None = None,
                 termsOfService: str | None = None, contact_email: str | None = None,
                 servers: list | None = None, security: list[BaseSecurity] | None = None, **kwargs):
        """
        Конструктор схемы Swagger

        :param args:
        :param name: Имя
        :param schema_url: Ссылка на схему
        :param prefix: Префикс к апи
        :param version: Версия апи
        :param title: Название API
        :param description: Описание API
        :param termsOfService: Ссылка на лицензионное соглашение
        :param contact_email: Контактный email
        :param list servers: Сервера [{"url": 'http://localhost:8080/'}]
        :param kwargs:

        """
        if not hasattr(self, 'install'):
            super().__init__(*args, **kwargs)
            self.prefix = prefix or '/'
            server = '/'.join(list(filter(None, self.prefix.split('/'))))
            if not server.startswith('http://') and not server.startswith('https://'):
                server = "/{server}".format(server=server)
            self.version = version or '1.0'
            self.openapi_version = openapi_version or '3.0.3'
            self.title = title
            self.schema_url = schema_url
            self.name = name
            self.components = {}
            self.paths = {}
            self.handlers = []
            self.tags = []
            self.security = security or []
            self.description = description or None
            self.termsOfService = termsOfService or None
            self.contact_email = contact_email or None
            self.models = []
            self.servers = servers or [{"url": server}]
            self._urls.append({"url": self.schema_url, "name": self.title or self.name})
            self.schema = {}

            self.install = True

    def add_handler(self, handler):
        self.handlers.append(handler)

    @property
    def urls(self):
        return self._urls

    @staticmethod
    def load(url):
        matched = []
        for key in Swagger._instances:
            instance = Swagger._instances[key]
            if isinstance(instance, Swagger):
                if instance.prefix in url:
                    matched.append(instance)
        if matched:
            matched.sort(key=lambda item: len(item.prefix or ""), reverse=True)
            return Swagger(name=matched[0].name)
        return None

    def dump(self) -> dict:
        self.schema = {
            'info': {},
            'openapi': self.openapi_version,
            'contact': {},
            'components': {}
        }
        self.schema.update(super().dump())
        self.schema.pop('class', None)
        self.schema.pop('children', None)

        self.schema['info']['title'] = self.title
        self.schema['info']['version'] = self.version
        if self.description is not None:
            self.schema['info']['description'] = self.description
        if self.termsOfService is not None:
            self.schema['info']['termsOfService'] = self.termsOfService
        self.schema['servers'] = self.servers
        if self.contact_email is not None:
            self.schema['info']['contact'] = {'email': self.contact_email}
        self.schema.pop('contact', None)
        self.schema['paths'] = self._dump_paths()
        models = self._dump_models()
        self.schema['components']['schemas'] = {
            name: to_openapi_schema(model_schema)
            for name, model_schema in models.items()
        }
        self.schema['components']['securitySchemes'] = self._dump_securitySchemes()

        # self.schema['components']['securitySchemes'] = {
        #     "petstore_auth": {
        #         "type": "oauth2",
        #         "flows": {
        #             "implicit": {
        #                 "authorizationUrl": "https://petstore3.swagger.io/oauth/authorize",
        #                 "scopes": {
        #                     "write:pets": "modify pets in your account",
        #                     "read:pets": "read your pets"
        #                 }
        #             }
        #         }
        #     },
        #     "api_key": {
        #         "type": "apiKey",
        #         "name": "api_key",
        #         "in": "header"
        #     }
        # }

        return self.schema

    def _dump_models(self):
        _models = {}
        if len(self.models) > 0:
            for model in self.models:
                if isinstance(model, Model):
                    _models.update(model.dump())
                if isinstance(model, Collection):
                    _models.update(model.dump())
        return _models

    def _dump_securitySchemes(self):
        _security = {}
        security_items = list(self.security)
        for handler in self.handlers:
            security_items.extend(getattr(handler, "security", []) or [])
        for item in security_items:
            if isinstance(item, BaseSecurity):
                _security.update(item.dump())
            if isinstance(item, type) and issubclass(item, BaseSecurity):
                _security.update(item().dump())
        return _security

    def _dump_security(self, securities):
        _security = []
        if len(securities) > 0:
            for item in securities:
                if isinstance(item, BaseSecurity):
                    _security.append({item.key: item.scope})
                elif isinstance(item, type) and issubclass(item, BaseSecurity):
                    security = item()
                    _security.append({security.key: security.scope})
                elif isinstance(item, str):
                    _security.append({item: []})
        return _security

    def _dump_paths(self):
        _handlers = {}
        for handler in self.handlers:
            handler_name = handler.__name__
            if not hasattr(handler, 'node'):
                continue
            full_route = self._external_path(handler.node.full_route)
            if full_route not in _handlers:
                _handlers[full_route] = {}
            method = handler.method
            if not method and handler_name in self.legal_http_method:
                method = handler_name
            elif method is None:
                method = 'get'
            method = method.lower()
            if method == 'option':
                method = 'options'

            if hasattr(handler, 'tags') and len(handler.tags) > 0:
                tags = handler.tags
            elif hasattr(handler, 'controller_class'):
                tags = [handler.controller_class]
            else:
                tags = []

            operation = {'tags': tags}
            if handler.description is not None:
                operation['description'] = handler.description
            if handler.summary is not None:
                operation['summary'] = handler.summary
            _handlers[full_route][method] = operation
            parameters = self._dump_paths_parameters(handler)
            known = {item.get('name') for item in parameters}
            for name in re.findall(r'{([^}/]+)}', full_route):
                if name not in known:
                    parameters.append({
                        'name': name,
                        'in': 'path',
                        'required': True,
                        'schema': {'type': 'string'},
                    })
            if parameters:
                operation['parameters'] = parameters
            operation['responses'] = self._dump_paths_response(handler)
            if hasattr(handler, 'request') and len(handler.request) > 0:
                _handlers[full_route][method].update({
                    'requestBody': self._dump_paths_request(handler)
                })
            if hasattr(handler, 'security') and len(handler.security) > 0:
                _handlers[full_route][method].update({
                    'security': self._dump_security(handler.security)
                })
        return _handlers

    def _external_path(self, path):
        prefix = '/' + '/'.join(list(filter(None, self.prefix.split('/'))))
        route = '/' + '/'.join(list(filter(None, path.split('/'))))
        if prefix != '/' and not route.startswith(prefix + '/') and route != prefix:
            route = prefix + route
        return route

    def _dump_paths_parameters(self, handler):
        parameters = []
        if len(handler.parameters) > 0:
            for parameter in handler.parameters:
                item = parameter.dump()
                item['schema'] = to_openapi_schema(item.get('schema', {}))
                item = {key: value for key, value in item.items() if value is not None}
                if item.get('in') == 'path':
                    item['required'] = True
                parameters.append(item)
        return parameters

    def _dump_paths_request(self, handler):
        requests = {}
        if hasattr(handler, 'request') and len(handler.request) > 0:
            for request in handler.request:
                requests.update(request.dump())
                if request.model and request.model not in self.models:
                    self.models.append(request.model)
        description = next(
            (item.get('description') for item in requests.values() if item.get('description')),
            None,
        )
        content = {}
        for content_type, item in requests.items():
            media = {}
            schema = item.get('schema')
            if schema is not None:
                media['schema'] = to_openapi_schema(schema)
            content[content_type] = media
        result = {'content': content}
        if description is not None:
            result['description'] = description
        return result

    def _dump_paths_response(self, handler):
        responses = {}
        if hasattr(handler, 'response') and len(handler.response) > 0:
            for code in handler.response:
                content = {}
                description = None
                if isinstance(handler.response[code], list):
                    for item in handler.response[code]:
                        dumped = item.dump()
                        for content_type, media in dumped.items():
                            description = description or media.get('description')
                            content[content_type] = {
                                'schema': to_openapi_schema(media['schema'])
                            } if media.get('schema') is not None else {}
                        if item.model and item.model not in self.models:
                            self.models.append(item.model)
                else:
                    dumped = handler.response[code].dump()
                    for content_type, media in dumped.items():
                        description = description or media.get('description')
                        content[content_type] = {
                            'schema': to_openapi_schema(media['schema'])
                        } if media.get('schema') is not None else {}
                    if handler.response[code].model and handler.response[code].model not in self.models:
                        self.models.append(handler.response[code].model)
                responses[str(code)] = {
                    'description': description or f'Response {code}',
                    'content': content,
                }
        if not responses:
            return {'default': {'description': 'Default response'}}
        return responses

    def __call__(self, *args, handler=None, node=None, model: Model | None = None, tags: list | None = None,
                 description: str | None = None, summary: str | None = None, request: list | None = None,
                 security: list | None = None, response: list | None = None,
                 parameters: list | None = None, **kwargs):
        """
        Устанавливает схему для метода. Позволяет указать базовые правила работы апи.

        :param model: Модель данных
        :return:
        """
        request = request or []
        security = security or []
        response = response or []
        parameters = parameters or []

        if inspect.isclass(handler):
            handler_obj = cast(Any, handler)
            handler_obj.actions = []
            for name in list(handler_obj.__dict__):
                method = handler_obj.__dict__[name]
                if hasattr(method, "is_action"):
                    handler_obj.actions.append(name)
                    if not hasattr(method, 'model') and hasattr(handler_obj.__dict__[name], 'is_swagger') and \
                            handler_obj.__dict__[name].is_swagger:
                        handler_obj.__dict__[name].model = model
                        if handler_obj.__dict__[name].model is not None and handler_obj.__dict__[name].model not in self.models:
                            self.models.append(handler_obj.__dict__[name].model)
        elif inspect.isfunction(handler):
            handler_obj = cast(Any, handler)
            handler_obj.is_swagger = True
            if model:
                handler_obj.model = model
                if handler_obj.model is not None and handler_obj.model not in self.models:
                    self.models.append(handler_obj.model)
        if model:
            cast(Any, handler).model = model

        if handler not in self.handlers:
            self.handlers.append(handler)
