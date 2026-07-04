from functools import wraps
import logging
import re
import os
from abc import ABC
from typing import Any
from urllib.parse import unquote
from .response import Response
from muscles.core import Schema
from muscles.core import BaseSecurity
from muscles.core import GuestUser
from muscles.core import Itinerary as CoreItinerary
from muscles.core.schema.itinerary import Node as CoreNode
from .error_handler import ForbiddenException


class RouteRule(ABC):
    """
    Базовое правило обработки патернов роута
    """
    name = ''

    def is_match(self, val, chunk) -> bool:
        return False

    def compile(self, val):
        return str(val)

    def param(self, val) -> Any:
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


class Itinerary(CoreItinerary):
    """
    Адаптер маршрутизатора на базе core-модуля Itinerary.
    """

    pass


class Itinerary1(Itinerary):
    """
    Совместимый адаптер для легаси-импорта Itinerary1.
    """

    pass


class Node(CoreNode):
    """
    Совместимый адаптер для легаси-импорта Node.
    """

    pass


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
