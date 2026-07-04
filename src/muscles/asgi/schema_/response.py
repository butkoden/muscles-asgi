from .schema import Schema
from .model import Model
from typing import Any


class ResponseBody(Schema):

    def __init__(self, *args, content_type=None, description=None, http_code=None, model: Any = None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, base_schema=None, **kwargs):
        if callable(model):
            model = model()
        kwargs['content_type'] = content_type
        kwargs['description'] = description
        kwargs['model'] = model
        kwargs['http_code'] = http_code
        kwargs["is_list"] = is_list
        kwargs["min_items"] = min_items
        kwargs["max_items"] = max_items
        kwargs["unique_items"] = unique_items
        kwargs["base_schema"] = base_schema
        super().__init__(*args, **kwargs)
        self.content_type = content_type
        self.description = description
        self.http_code = http_code
        self.model: Any = model
        self.is_list = is_list
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items
        self.base_schema = base_schema

    def dump(self) -> dict:
        results = []
        model: Any = None
        for child in self._children:
            results.append(child.dump())
        if self.model and isinstance(self.model, Model):
            model = {"$ref": "#/components/schemas/%s" % self.model.__class__.__name__}
        elif self.model and isinstance(self.model, list):
            model = {"oneOf": []}
            for _model in self.model:
                model['oneOf'].append({"$ref": "#/components/schemas/%s" % _model.__class__.__name__})
        else:
            model = self.model.dump() if hasattr(self, 'model') and hasattr(self.model, 'dump') else None
        if self.is_list:
            components_schema = {
                "type": "array",
                "items": model
            }
            if self.min_items > 0:
                components_schema['minItems'] = self.min_items
            if self.max_items > 0:
                components_schema['maxItems'] = self.max_items
            if self.unique_items:
                components_schema['uniqueItems'] = True
        else:
            components_schema = model

        if self.base_schema is not None:
            components_schema = self.base_schema.schema(child=components_schema)
        return {
            self.content_type: {
                "http_code": self.http_code,
                "content_type": self.content_type,
                "description": self.description,
                "schema": components_schema,
            }
        }


class HtmlResponseBody(ResponseBody):

    def __init__(self, *args, description=None, http_code=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, base_schema=None, **kwargs):
        kwargs['description'] = description
        kwargs['model'] = model
        kwargs['http_code'] = http_code
        kwargs['is_list'] = is_list
        kwargs['min_items'] = min_items
        kwargs['max_items'] = max_items
        kwargs["unique_items"] = unique_items
        kwargs["base_schema"] = base_schema
        content_type = 'text/html'
        super().__init__(*args, content_type=content_type, **kwargs)


class JsonResponseBody(ResponseBody):

    def __init__(self, *args, description=None, http_code=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, base_schema=None, **kwargs):
        kwargs['description'] = description
        kwargs['model'] = model
        kwargs['http_code'] = http_code
        kwargs['is_list'] = is_list
        kwargs['min_items'] = min_items
        kwargs['max_items'] = max_items
        kwargs["unique_items"] = unique_items
        kwargs["base_schema"] = base_schema
        content_type = 'application/json'
        super().__init__(*args, content_type=content_type, **kwargs)


class XmlResponseBody(ResponseBody):

    def __init__(self, *args, description=None, http_code=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, base_schema=None, **kwargs):
        kwargs['description'] = description
        kwargs['model'] = model
        kwargs['http_code'] = http_code
        kwargs['is_list'] = is_list
        kwargs['min_items'] = min_items
        kwargs['max_items'] = max_items
        kwargs["unique_items"] = unique_items
        kwargs["base_schema"] = base_schema
        content_type = 'application/xml'
        super().__init__(*args, content_type=content_type, **kwargs)


class TextResponseBody(ResponseBody):

    def __init__(self, *args, description=None, http_code=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, base_schema=None, **kwargs):
        kwargs['description'] = description
        kwargs['model'] = model
        kwargs['http_code'] = http_code
        kwargs['is_list'] = is_list
        kwargs['min_items'] = min_items
        kwargs['max_items'] = max_items
        kwargs["unique_items"] = unique_items
        kwargs["base_schema"] = base_schema
        content_type = 'text/plain'
        super().__init__(*args, content_type=content_type, **kwargs)
