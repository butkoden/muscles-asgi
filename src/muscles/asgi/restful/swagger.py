from muscles.core import Schema
from muscles.core import Model
from muscles.core import Collection
from muscles.core import BaseSecurity
from muscles.core.schema.itinerary import BaseSecurity
import inspect


class Swagger(Schema):

    _urls = []
    _instances = {}
    legal_http_method = ['get', 'post', 'put', 'delete', 'head', 'patch', 'options', 'trace', 'connect']

    def __new__(cls, *args, name: str = None, **kwargs):
        if name not in cls._instances:
            cls._instances[name] = object.__new__(cls)
        return cls._instances[name]

    def __init__(self, *args, name: str = None, schema_url: str = None, prefix: str = None, version: str = None,
                 title: str = None, description: str = None, termsOfService: str = None, contact_email: str = None,
                 servers: list = None, security: list[BaseSecurity] = None, **kwargs):
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
        for key in Swagger._instances:
            instance = Swagger._instances[key]
            if isinstance(instance, Swagger):
                if instance.prefix in url:
                    return Swagger(name=instance.name)
        return None

    def dump(self) -> dict:
        self.schema = {
            'info': {},
            'openapi': '3.0.3',
            'contact': {},
            'components': {}
        }
        self.schema.update(super().dump())

        self.schema['info']['title'] = self.title
        self.schema['info']['version'] = self.version
        self.schema['description'] = self.description
        self.schema['termsOfService'] = self.termsOfService
        self.schema['servers'] = self.servers
        self.schema['contact']['email'] = self.contact_email
        self.schema['paths'] = self._dump_paths()
        self.schema['components']['schemas'] = self._dump_models()
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
        if len(self.security) > 0:
            for item in self.security:
                if isinstance(item, BaseSecurity):
                    _security.update(item.dump())
                if isinstance(item, type):
                    _security.update(item().dump())
        return _security

    def _dump_security(self, securities):
        _security = []
        if len(securities) > 0:
            for item in securities:
                if isinstance(item, BaseSecurity):
                    _security.append({item.key: item.scope})
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

            if hasattr(handler, 'tags') and len(handler.tags) > 0:
                tags = handler.tags
            elif hasattr(handler, 'controller_class'):
                tags = [handler.controller_class]
            else:
                tags = []

            _handlers[full_route][method] = {
                'tags': tags,
                'description': handler.description,
                'summary': handler.summary,
            }
            if len(handler.parameters) > 0:
                _handlers[full_route][method].update({
                    'parameters': self._dump_paths_parameters(handler)
                })
            if hasattr(handler, 'response') and len(handler.response) > 0:
                _handlers[full_route][method].update({
                    'responses': self._dump_paths_response(handler)
                })
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
                parameters.append(parameter.dump())
        return parameters

    def _dump_paths_request(self, handler):
        requests = {}
        if hasattr(handler, 'request') and len(handler.request) > 0:
            for request in handler.request:
                requests.update(request.dump())
                if request.model and request.model not in self.models:
                    self.models.append(request.model)
        return {
            "content": requests
        }

    def _dump_paths_response(self, handler):
        responses = {}
        if hasattr(handler, 'response') and len(handler.response) > 0:
            for code in handler.response:
                responses[code] = {"content": {}}
                if isinstance(handler.response[code], list):
                    for item in handler.response[code]:
                        responses[code]["content"].update(item.dump())
                        if item.model and item.model not in self.models:
                            self.models.append(item.model)
                else:
                    responses[code]["content"].update(handler.response[code].dump())
                    if handler.response[code].model and handler.response[code].model not in self.models:
                        self.models.append(handler.response[code].model)
        return responses

    def __call__(self, *args, handler=None, node=None, model: Model = None, tags: list = None, description: str = None,
                 summary: str = None, request: list = [], security: list = [], response: list = [],
                 parameters: list = [], **kwargs):
        """
        Устанавливает схему для метода. Позволяет указать базовые правила работы апи.

        :param model: Модель данных
        :return:
        """
        if inspect.isclass(handler):
            handler.actions = []
            for name in list(handler.__dict__):
                method = handler.__dict__[name]
                if hasattr(method, "is_action"):
                    handler.actions.append(name)
                    if not hasattr(method, 'model') and hasattr(handler.__dict__[name], 'is_swagger') and \
                            handler.__dict__[name].is_swagger:
                        handler.__dict__[name].model = model
                        if handler.__dict__[name].model is not None and handler.__dict__[name].model not in self.models:
                            self.models.append(handler.__dict__[name].model)
        elif inspect.isfunction(handler):
            handler.is_swagger = True
            if model:
                handler.model = model
                if handler.model is not None and handler.model not in self.models:
                    self.models.append(handler.model)
        if model:
            handler.model = model

        if handler not in self.handlers:
            self.handlers.append(handler)
