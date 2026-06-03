from functools import wraps
import logging
import re
import os
from abc import ABC
from urllib.parse import unquote
from .response import Response
from muscles.core import Schema
from muscles.core import BaseSecurity
from muscles.core import GuestUser
from muscles.core import Itinerary
from .error_handler import ForbiddenException


class RouteRule(ABC):
    """
    Базовое правило обработки патернов роута
    """
    name = ''

    def is_match(self, match, chunk):
        pass

    def compile(self, val):
        return str(val)

    def param(self, val):
        return str(val)


class RouteRuleDefault(RouteRule):
    """
    Правило обработки роута по умолчанию
    """
    name = 'default'

    def is_match(self, val, chunk):
        return not (val and val[0] == '{' and val[-1] == '}') and val == chunk

    def param(self, val):
        return str(val)

    def compile(self, val):
        return str(val)


class RouteRuleVar(RouteRule):
    """
    Правил обработки роута - разрешенные символы
    """
    name = 'var'

    def is_match(self, val, chunk):
        if not val:
            return False
        for char in val:
            if not (char.isalnum() or char in {'%', '_', '-'}):
                return False
        return True

    def param(self, val):
        return str(val)

    def compile(self, val):
        return str(val)


class RouteRuleInt(RouteRule):
    """
    Правил обработки роута - цифры
    """
    name = 'int'

    def is_match(self, val, chunk):
        return bool(val) and val.isdigit()

    def param(self, val):
        return int(val)

    def compile(self, val):
        return str(val)


class RouteRuleFloat(RouteRule):
    """
    Правил обработки роута - цифра с плавающей точкой
    """
    name = 'float'

    def is_match(self, val, chunk):
        if not val:
            return False
        left, sep, right = val.partition('.')
        return bool(sep) and left.isdigit() and right.isdigit()

    def param(self, val):
        return float(val)

    def compile(self, val):
        return str(val)


class Itinerary1:
    """
    Базовый класс для работы с роутами
    """

    legal_http_method = ['get', 'post', 'put', 'delete', 'head', 'patch', 'options', 'trace', 'connect']

    # nodes_map = []
    # static_map = []
    error_handler_map = []
    rules = []
    node = None
    _instances = {}

    set_response = {}

    def __new__(cls, *args, prefix=None, version=None, name=None, **kwargs):
        """
        Создает синглтон объект роутера, формирует первую ноду роутера
        :param args:
        :param prefix: префикс роутера
        :param version: Версия роутера
        :param name: Название роутера
        :param kwargs:
        """
        instance_name = (cls, name)
        if instance_name not in cls._instances:
            cls._instances[instance_name] = super(Itinerary, cls).__new__(cls)
            cls._instances[instance_name].node = Node('')
            cls._instances[instance_name].prefix = prefix
            cls._instances[instance_name].nodes_map = []
            cls._instances[instance_name].static_map = []
        return cls._instances[instance_name]

    def __init__(self, *args, **kwargs):
        if not hasattr(self, 'install'):
            self.__before_init__(*args, **kwargs)
            self.install = True

    def __before_init__(self, *args, **kwargs):
        pass

    def modify_response(self, response: Response) -> Response:
        """
        @TODO Добавить возможность модификации к функциям роута
        Модифицирует объект ответ

        :param response: Объект ответа
        :return:
        """
        return response

    def instance_keys(self):
        """
        Получает ключи созданых роутеров

        :return: List(dict)
        """
        return self._instances.keys()

    def instance_list(self):
        """
        Получает список объектов роутеоров

        :return: List
        """
        return self._instances.items()

    def add_rule(self, rule):
        """
        Добавляет новое правило в доступный список правил

        :param rule: Объект правила
        :return:
        """
        self.rules.append(rule)

    def to_url(self, route_key, params):
        """
        Формирует из ключа маршрута и параметров ссылку

        :param route_key: Ключ маршрута
        :param params: Параметры
        :return:
        """
        l = []

        def repl(m):
            name = m.group(3) if m.group(3) else 'var'
            for rule in self.rules:
                if rule.name == name:
                    return rule.compile(params.get(m.group(2), ''))

        for r in self.nodes_map:
            if r['key'] == route_key:
                rs = r['route'].split('/')
                for s in rs:
                    l.append(re.sub(r"(\{([\w\d\%\_\-]+)\:?([\w\d\%\_\-]+)?\})", repl, s))
        return '/'.join(l)

    def match(self, url):
        """
        Находит подходящий маршрут по УРЛ

        :param url: Ссылка
        :return:
        """
        if url == '/':
            url = '/main'
        chunks = url.split('/')
        if len(chunks) > 0 and chunks[0] == '':
            chunks = chunks[1:]
        route = self.node
        routes = []
        _find_routes = self._match(route, chunks)
        for _route in _find_routes:
            for item in self.nodes_map:
                if item['key'] == _route.key:
                    routes.append(_route)
        return routes[0] if len(routes) > 0 else None

    def _match(self, route, chunks, paths=[], n=0):
        """
        Поиск подходящих узлов

        :param route:
        :param chunks:
        :param paths:
        :param n:
        :return:
        """
        for node in route.childrens:
            if node.is_match(chunks[:1][0]):
                if len(chunks[1:]) == 0:
                    yield node
                else:
                    yield from self._match(node, chunks[1:], [node] + paths, n + 1)

    def match_with_params(self, url):
        """
        Возврщает подходящий маршрут с параметрами

        :param url: УРЛ
        :return:
        """
        chunks = url.split('/')
        node = self.match(url)
        if node is None:
            return None, {}
        _node = node
        dictionary = {}
        for chunk in chunks[::-1]:
            if _node.dictionary_key:
                dictionary.update(_node.dictionary(chunk))
            _node = _node.parent
        return node, dictionary

    def add_static(self, directory: str, prefix: str = None, handler=None, full_path: bool = False):
        """
        Функции обработки статических файлов

        :param directory: Директория фалов
        :param prefix: Префикc для маршрута
        :param handler: Обработчик маршрута
        :param bool full_path: Польный путь маршрута
        :return:
        """
        for c in self.static_map:
            if directory == c['directory'] and prefix == c['prefix']:
                raise Exception('Route must have unique `prefix` [%s] and `route` [%s] values' % (prefix, directory))
        self.static_map.append({
            "directory": directory if full_path else os.path.join(os.getcwd(), directory),
            "prefix": prefix,
            'handler': handler,
        })

    def static(self, directory: str, prefix: str = None, full_path: bool = False):
        """
        Декторатор функции обработки статических файлов

        :param directory: Директория фалов
        :param prefix: Префикc для маршрута
        :param bool full_path: Польный путь маршрута
        :return:
        """

        def decorator(func):
            self.add_static(directory, prefix=prefix, handler=func, full_path=full_path)

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def get_current_static(self, request):
        """
        Возвращает обработчик статических файлов

        :param request: Объект запроса
        :return:
        """

        def condition(route):
            """condition here"""
            res = True
            if res and route['prefix'] and not request.path.lower().startswith(route['prefix'] + '/'.lower()):
                res = False
            return res

        filtered = [static for static in self.static_map if condition(static)]
        return filtered[0] if len(filtered) > 0 else None

    def _trigger_set_handler(self, handler, *args, **kwargs):
        return handler

    def _trigger_set_controller(self, handler, *args, stateful: bool = False, **kwargs):
        if not hasattr(handler, 'stateful_controller'):
            handler.stateful_controller = stateful
        return handler

    def add(self, route, key=None, handler=None, method=None, content_type=None,
            redirect: str = None, module=None):
        """
        Добавляет функцию обработки маршрута

        :param route: Маршрут
        :param key: Ключ маршрута
        :param handler: Обработчик маршрута
        :param method: Метод маршрута
        :param content_type: Тип контента маршрута
        :param redirect: Редирект для маршрута
        :param module: Настройки модуля обработки
        :return:
        """
        if route == '/':
            route = '/main'
        if module is not None and 'url_prefix' in module:
            route = '/'.join(module['url_prefix'].split('/') + route.split('/'))
        full_route = route
        full_route = '/'.join([i for i in full_route.split('/') if i != ''])
        if not full_route.startswith('/'):
            full_route = "/%s" % full_route

        if self.prefix:
            route = '/'.join(self.prefix.split('/') + route.split('/'))

        route = '/'.join([i for i in route.split('/') if i != ''])

        chunks = route.split('/')
        for c in self.nodes_map:
            if route == c['route'] and content_type == c['content_type'] and key == c['key'] and method == c['method']:
                raise Exception(
                    'The router must have a unique sequence of `key` [%s], `content_type` [%s], `method` ['
                    '%s], `route` [%s]' % (key, content_type, method, route))

        if handler is None:
            raise Exception('The `handler` parameter is mandatory')

        node = self.node
        if key is None or not key:
            key = '.'.join(
                tuple(chunks[1:] if chunks[0] == '' else chunks)
            )
        _key, key = key, None
        _handler, handler = handler, None
        _chunks = []
        for chunk in chunks:
            _chunks.append(chunk)
            if chunk == '':
                continue
            m = re.search(r"\{([^\}]+)\}", chunk)
            if m:
                m = m.group(1).split(':')
                dictionary_key = m[0]
                rule = m[1] if len(m) > 1 else 'var'
            else:
                dictionary_key = False
                rule = 'default'
            for _rule in self.rules:
                if _rule.name == rule:
                    rule = _rule
                    break
            if '/'.join(_chunks) == '/'.join(chunks):
                key = _key
                handler = _handler

                def condition(nm, key=None, route=None, method=None, content_type=None):
                    res = True
                    if res and nm['key'] != key:
                        res = False
                    if res and nm['route'] != route:
                        res = False
                    if res and nm['method'] != method:
                        res = False
                    if res and nm['content_type'] != content_type:
                        res = False
                    return res

                nm_find = [nm for nm in self.nodes_map if condition(nm, key=key, route=route, method=method,
                                                                    content_type=content_type)]
                if len(nm_find) == 0:
                    self.nodes_map.append({
                        "key": key,
                        "route": route,
                        'method': method,
                        'content_type': content_type,
                        'redirect': redirect,
                        'handler': handler,
                    })
            node = node.instance(chunk, full_route=full_route, key=key, dictionary_key=dictionary_key, rule=rule)
        handler.node = node
        handler.full_route = full_route
        if not hasattr(handler, 'method') or not handler.method:
            handler.method = method
        if not hasattr(handler, 'content_type') or not handler.content_type:
            handler.content_type = content_type
        if not hasattr(handler, 'redirect') or not handler.redirect:
            handler.redirect = redirect
        return handler

    def init(self, route, *args, key=None, module=None, method=None, content_type=None,
             redirect: str = None, **kwargs):
        """
        Декоратор функции обработки маршрута

        :param route: Маршрут
        :param key: Ключ маршрута
        :param module: Настройки модуля обработки
        :param method: Метод маршрута
        :param content_type: Тип контента маршрута
        :param redirect: Редирект, для маршрута
        :return:
        """
        def decorator(func):
            func = self._trigger_set_handler(func, *args, **kwargs)
            self.add(route, key=key, module=module, handler=func, method=method, content_type=content_type,
                     redirect=redirect)
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def controller(self, route, *args, model: Schema = None, security: list[BaseSecurity, str] = None,
                   stateful: bool = False, **kwargs):
        """
        Регистрация контроллера для обработки запросов классом

        :param model: Модель данных
        :param route: Маршрут
        :param stateful: Не кэшировать инстанс контроллера между запросами
        :return:
        """
        def decorator(func):
            func.actions = []
            func.security = []
            func = self._trigger_set_controller(func, *args, stateful=stateful, **kwargs)
            for name in func.__dict__:
                method = func.__dict__[name]

                _security = []
                if security is not None:
                    for item in security:
                        if isinstance(item, BaseSecurity):
                            _security.append({item.securitySchema: []})
                        else:
                            _security.append({item: []})
                    func.security = _security

                if hasattr(method, "is_action"):
                    method.controller_class = func.__name__
                    method.controller = func
                    if len(func.security) > 0:
                        for item in func.security:
                            if item not in method.security:
                                method.security.append(item)
                    func.actions.append(name)
                    if not hasattr(method, 'model'):
                        method.model = model
                    _route = '/'.join(list(filter(None, route.split('/'))) + [method.route])
                    method = self._trigger_set_handler(method, *args, **kwargs)
                    self.add(_route, key=method.key, module=method.module, handler=method, method=method.method,
                             content_type=method.content_type, redirect=method.redirect)

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def action(self, *args, route=None, key=None, module=None, method=None, content_type=None,
               redirect: str = None, model: Schema = None, security: list[BaseSecurity, str] = None, **kwargs):
        """
        Регистрация "действия" для контроллера.
        Внимание: Работает только совместно с регистрацией контроллера с помощью метода controller

        :param model: Модель данных
        :param route: Маршрут
        :param key: Ключ маршрута
        :param module: Настройки модуля обработки
        :param method: Метод маршрута
        :param content_type: Тип контента маршрута
        :param redirect: Редирект, для маршрута
        :param security: Необходимость и способ авторизации
        :return:
        """
        def decorator(func):
            func = self._trigger_set_handler(func, *args, **kwargs)
            func.security = []
            func.is_action = True

            _security = []
            if security is not None:
                for item in security:
                    if isinstance(item, BaseSecurity):
                        _security.append(item.securitySchema)
                    else:
                        _security.append(item)
                func.security = _security

            func.key = key
            func.module = module
            func.method = method
            if func.method == '*' and func.__name__ in self.legal_http_method:
                func.method = func.__name__
            func.content_type = content_type
            func.redirect = redirect
            func.route = route or '/'
            if model:
                func.model = model

            @wraps(func)
            def wrapper(*args, **kwargs):
                # validate(instance={"name": "Eggs", "price": 34.99}, schema=schema)
                if "request" in kwargs and len(func.security) > 0 and isinstance(kwargs["request"].user, GuestUser):
                    raise ForbiddenException()
                else:
                    return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def add_error_handler(self, code=None, handler=None):
        """
        Добавляет функцию обработки ошибки

        :param code: Код ошибки
        :param handler: функция обработки ошибки
        :return:
        """
        for c in self.error_handler_map:
            if code == c['code']:
                raise Exception('Error Handler must have unique `code` [%s]' % (code))
        if handler is None:
            raise Exception('Error Handler must have `handler`')
        self.error_handler_map.append({
            "code": code,
            "point": self.__class__,
            "handler": handler,
        })

    def error_handler(self, code=None):
        """
        Декоратор функции ошибки

        :param code: Код ошибки, который эта функция будет обрабатывать
        :return:
        """

        def decorator(func):
            self.add_error_handler(code=code, handler=func)

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def get_current_route(self, request):
        """
        Получает узел роутера из объекта запроса

        :param request: Объект запроса
        :return:
        """
        node, dictionary = self.match_with_params(request.path)
        if node is None:
            return None, ()

        def condition(route):
            """condition here"""
            res = True
            if res and route['key'] and route['key'] != node.key:
                res = False
            if res and route['method'] and route['method'] != '*' and route['method'].upper() != request.method.upper():
                res = False
            if res and route['content_type'] and route['content_type'] != '*/*' and \
                    route['content_type'].lower() != request.content_type.lower():
                res = False
            return res

        filtered = [route for route in self.nodes_map if condition(route)]
        return filtered[0] if len(filtered) > 0 else None, dictionary

    def get_current_error_handler(self, error):
        """
        Возвращает функцию обработки ошибки

        :param error: код ошибки
        :return:
        """

        def condition(handler, cls):
            """condition here"""
            res = True
            if handler['code'] is None or str(handler['code']) != str(error.status):
                res = False
            return res

        filtered_default = [handler for handler in self.error_handler_map if handler['code'] is None]
        filtered = [handler for handler in self.error_handler_map if condition(handler, self)]
        return filtered[0] if len(filtered) > 0 else filtered_default[0] if len(filtered_default) > 0 else None

    def print_tree(self):
        """
        Печатает дерево маршрутов

        :return:
        """
        logger = getattr(self, "logger", None) or logging.getLogger("muscles.asgi.router")
        route_map = self.nodes_map
        def tree(node, i):
            for r in node.childrens:
                i = i + 1
                meth = [_m['method'] or '*' for _m in route_map if r.key == _m['key']]
                logger.debug(
                    "%s /%s    [%s key:%s]",
                    '. ' * i,
                    r.route,
                    ','.join(meth).upper(),
                    r.key,
                )
                tree(r, i)
                i = i - 1

        tree(self.node, 0)


class Node(ABC):
    """
    Класс узла роутера
    """
    route = None
    rule = None
    name = None
    dictionary = None
    key = None
    method = None
    content_type = None

    def __init__(self, chunk_route, key=None, full_route=None, dictionary_key=None, rule=None, parent=None):
        """
        Конструктор класса роутера

        :param chunk_route: Адрес узла
        :param key: ключ узла
        :param dictionary_key: Словарь узла
        :param rule: Правило узла
        :param parent: Родитель узла
        """
        self.full_route = full_route
        m = re.search(r"\{([^\}]+)\}", chunk_route)
        if m:
            m = m.group(1).split(':')
            chunk_route = '{%s:%s}' % (m[0], m[1] if len(m) > 1 else 'var')
        self.key = key.lower() if key and key is not None else None
        self.route = chunk_route.lower() if chunk_route and chunk_route is not None else None
        self.rule = rule
        self.full_route = full_route.lower() if full_route and full_route is not None else None
        self.parent = parent
        self.weight = 0 if not m else 100
        self.dictionary_key = dictionary_key.lower() if dictionary_key and dictionary_key is not None else None
        self._childrens = []
        if self.parent is not None:
            self.parent._childrens.append(self)

    def get_children_node(self, chunk_route):
        """
        Находит потомков узла
        :param chunk_route: Узел для поиска
        :return:
        """
        for node in self._childrens:
            if node.route == chunk_route.lower():
                return node
        return None

    def instance(self, chunk_route, key=None, full_route=None, dictionary_key=None, rule=None):
        """
        Формирует узел

        :param full_route:
        :param chunk_route: Адрес узла
        :param key: ключ узла
        :param dictionary_key: Словарь узла
        :param rule: Правило узла
        :return: Node
        """
        m = re.search(r"\{([^\}]+)\}", chunk_route)
        if m:
            m = m.group(1).split(':')
            chunk_route = '{%s:%s}' % (m[0], m[1] if len(m) > 1 else 'var')
        if self.get_children_node(chunk_route):
            if self.get_children_node(chunk_route).key is None:
                self.get_children_node(chunk_route).key = key
            return self.get_children_node(chunk_route)
        else:
            return Node(chunk_route, key=key, full_route=full_route, dictionary_key=dictionary_key,
                        rule=rule, parent=self)

    def is_match(self, path):
        """
        Проверяет совпадает ли путь с правилом узла
        :param path: путь роутера
        :return:
        """
        return True if self.rule.is_match(path, self.route) else False

    def dictionary(self, chunk):
        """
        Словарь запроса

        :param chunk: часть пути узла
        :return:
        """
        return {self.dictionary_key: unquote(chunk)}

    @property
    def childrens(self):
        """
        Потомки узла
        :return:
        """
        return self._childrens

    def set_parent(self, parent, rule=None):
        """
        Устанавливает родителя узла
        :param parent: Родитель узла
        :param rule:
        :return:
        """
        self.parent = parent


class Routes(Itinerary):
    """
    Класс роутера
    """
    pass


class Api(Itinerary):
    """
    Класс Апи
    """

    def modify_response(self, response):
        headers = []
        for header in response.headers:
            if header[0] == 'Content-Type':
                continue
            headers.append(header)
        headers.append(('Content-Type', 'application/json; charset=utf-8'))
        response.headers = headers
        return response


itinerary = Itinerary()
routes = Routes()
api = Api()

routes.add_rule(RouteRuleDefault())
routes.add_rule(RouteRuleVar())
routes.add_rule(RouteRuleInt())
routes.add_rule(RouteRuleFloat())
