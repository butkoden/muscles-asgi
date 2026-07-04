from .schema import Schema
from .model import BaseModel
from .collection import Collection
from typing import Any


class RequestBody(Schema):

    def __init__(self, *args, content_type=None, description=None, model: Any = None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, **kwargs):
        if callable(model):
            model = model()
        kwargs["content_type"] = content_type
        kwargs["description"] = description
        kwargs["model"] = model
        kwargs["is_list"] = is_list
        kwargs["min_items"] = min_items
        kwargs["max_items"] = max_items
        kwargs["unique_items"] = unique_items
        super().__init__(*args, **kwargs)
        self.is_list = is_list
        self.content_type = content_type
        self.description = description
        self.model: Any = model
        self.is_list = is_list
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items

    def dump(self) -> dict:
        results = []
        for child in self._children:
            results.append(child.dump())
        if self.is_list:
            if self.model and (isinstance(self.model, BaseModel) or isinstance(self.model, Collection)):
                schema = {"$ref": "#/components/schemas/%s" % self.model.__class__.__name__}
            elif self.model and isinstance(self.model, list):
                schema = {"oneOf": []}
                for _model in self.model:
                    schema['oneOf'].append({"$ref": "#/components/schemas/%s" % _model.__class__.__name__})
            else:
                schema = self.model.dump() if hasattr(self, 'model') and hasattr(self.model, 'dump') else None
            model: Any = {
                "type": "array",
                "items": schema
            }
            if self.min_items > 0:
                model['minItems'] = self.min_items
            if self.max_items > 0:
                model['maxItems'] = self.max_items
            if self.unique_items:
                model['uniqueItems'] = True
        else:
            if self.model and (isinstance(self.model, BaseModel) or isinstance(self.model, Collection)):
                model = {"$ref": "#/components/schemas/%s" % self.model.__class__.__name__}
            elif self.model and isinstance(self.model, list):
                model = {"oneOf": []}
                for _model in self.model:
                    model['oneOf'].append({"$ref": "#/components/schemas/%s" % _model.__class__.__name__})
            else:
                model = self.model.dump() if hasattr(self, 'model') and hasattr(self.model, 'dump') else None

        return {
            self.content_type: {
                "description": self.description,
                "schema": model,
            }
        }


class JsonRequestBody(RequestBody):

    def __init__(self, *args, description=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, **kwargs):
        kwargs["description"] = description
        kwargs["model"] = model
        kwargs["content_type"] = 'application/json'
        kwargs["is_list"] = is_list
        kwargs["min_items"] = min_items
        kwargs["max_items"] = max_items
        kwargs["unique_items"] = unique_items
        super().__init__(*args, **kwargs)


class XmlRequestBody(RequestBody):

    def __init__(self, *args, description=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, **kwargs):
        kwargs["description"] = description
        kwargs["model"] = model
        kwargs["content_type"] = 'application/xml'
        kwargs["is_list"] = is_list
        kwargs["min_items"] = min_items
        kwargs["max_items"] = max_items
        kwargs["unique_items"] = unique_items
        super().__init__(*args, **kwargs)


class FormRequestBody(RequestBody):

    def __init__(self, *args, description=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, **kwargs):
        kwargs["description"] = description
        kwargs["model"] = model
        kwargs["content_type"] = 'application/x-www-form-urlencoded'
        kwargs["is_list"] = is_list
        kwargs["min_items"] = min_items
        kwargs["max_items"] = max_items
        kwargs["unique_items"] = unique_items
        super().__init__(*args, **kwargs)


class MultipartRequestBody(RequestBody):

    def __init__(self, *args, description=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, **kwargs):
        kwargs["description"] = description
        kwargs["model"] = model
        kwargs["content_type"] = 'multipart/form-data'
        kwargs["is_list"] = is_list
        kwargs["min_items"] = min_items
        kwargs["max_items"] = max_items
        kwargs["unique_items"] = unique_items
        super().__init__(*args, **kwargs)


class FileRequestBody(RequestBody):

    def __init__(self, *args, content_type=None, description=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, **kwargs):
        kwargs["description"] = description
        kwargs["model"] = model
        kwargs["content_type"] = content_type
        kwargs["is_list"] = is_list
        kwargs["min_items"] = min_items
        kwargs["max_items"] = max_items
        kwargs["unique_items"] = unique_items
        super().__init__(*args, **kwargs)


class PayloadRequestBody(RequestBody):

    def __init__(self, *args, description=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, **kwargs):
        kwargs["description"] = description
        kwargs["model"] = model
        kwargs["content_type"] = 'text/plain'
        kwargs["is_list"] = is_list
        kwargs["min_items"] = min_items
        kwargs["max_items"] = max_items
        kwargs["unique_items"] = unique_items
        super().__init__(*args, **kwargs)


class TextRequestBody(RequestBody):

    def __init__(self, *args, description=None, model=None,
                 is_list=False, min_items=0, max_items=0, unique_items=False, **kwargs):
        kwargs["description"] = description
        kwargs["model"] = model
        kwargs["content_type"] = 'text/plain'
        kwargs["is_list"] = is_list
        kwargs["min_items"] = min_items
        kwargs["max_items"] = max_items
        kwargs["unique_items"] = unique_items
        super().__init__(*args, **kwargs)
