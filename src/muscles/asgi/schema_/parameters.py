from .schema import Schema
from typing import Any


class BaseParameter(Schema):

    def __init__(self, name, param_type: Any, *args, required=False, description=None, explode=False, model=None, **kwargs):
        kwargs["required"] = required
        kwargs["explode"] = explode
        kwargs["description"] = description
        if callable(param_type):
            param_type = param_type()
        super().__init__(name, param_type, *args, **kwargs)
        self.name = name
        self.param_type = param_type
        self.required = required
        self.explode = explode
        self.description = description
        self.destination = None

    def dump(self) -> dict:
        results = []
        for child in self._children:
            results.append(child.dump())
        return {
            "required": self.required,
            "explode": self.explode,
            "description": self.description,
            "name": self.name,
            "schema": self.param_type.dump(),
            "in": self.destination,
        }


class FormParameter(BaseParameter):

    def __init__(self, name, param_type, *args, required=False, description=None, explode=False, **kwargs):
        kwargs["required"] = required
        kwargs["description"] = description
        kwargs["explode"] = explode
        super().__init__(name, param_type, *args, **kwargs)
        self.destination = 'formData'


class HeaderParameter(BaseParameter):

    def __init__(self, name, param_type, *args, required=False, description=None, explode=False, **kwargs):
        kwargs["required"] = required
        kwargs["description"] = description
        kwargs["explode"] = explode
        super().__init__(name, param_type, *args, **kwargs)
        self.destination = 'header'


class QueryParameter(BaseParameter):

    def __init__(self, name, param_type, *args, required=False, description=None, explode=False, **kwargs):
        kwargs["required"] = required
        kwargs["description"] = description
        kwargs["explode"] = explode
        super().__init__(name, param_type, *args, **kwargs)
        self.destination = 'query'


class CookieParameter(BaseParameter):

    def __init__(self, name, param_type, *args, required=False, description=None, explode=False, **kwargs):
        kwargs["required"] = required
        kwargs["description"] = description
        kwargs["explode"] = explode
        super().__init__(name, param_type, *args, **kwargs)
        self.destination = 'cookie'


class PathParameter(BaseParameter):

    def __init__(self, name, param_type, *args, required=False, description=None, explode=False, **kwargs):
        kwargs["required"] = required
        kwargs["description"] = description
        kwargs["explode"] = explode
        super().__init__(name, param_type, *args, **kwargs)
        self.destination = 'path'
