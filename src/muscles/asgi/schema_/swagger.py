from .schema import Schema
from .request import RequestBody
from .response import ResponseBody
from .parameters import BaseParameter


class Swagger(Schema):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = {'info': {}, 'openapi': kwargs.get('openapi_version', '3.0.3')}
        if kwargs.get('title'):
            self.schema['info']['title'] = kwargs['title']
        elif kwargs.get('name'):
            self.schema['info']['title'] = kwargs.get('name')
        if kwargs.get('version'):
            self.schema['info']['version'] = kwargs.get('version')
        if kwargs.get('description'):
            self.schema['description'] = kwargs.get('description')
        if kwargs.get('termsOfService'):
            self.schema['termsOfService'] = kwargs.get('termsOfService')
        if kwargs.get('servers') and isinstance(kwargs.get('servers'), list):
            self.schema['servers'] = kwargs.get('servers')
        if kwargs.get('contact_email'):
            self.schema['contact'] = {}
            self.schema['contact']['email'] = kwargs.get('contact_email')

        if kwargs.get('request'):
            self.request = kwargs.get('request')
        if kwargs.get('response'):
            self.response = kwargs.get('response')
        if kwargs.get('parameters'):
            self.parameters = kwargs.get('parameters')
        if kwargs.get('security'):
            self.security = kwargs.get('security')

    def dump(self) -> dict:
        results = []
        for child in self._children:
            results.append(child.dump())

        if hasattr(self, "request") and self.request is not None:
            if isinstance(self.request, list):
                self.schema['request'] = []
                for request in self.request:
                    if isinstance(request, RequestBody):
                        self.schema['request'].append(request.dump())
                    else:
                        raise Exception('The `response` parameter is not inherited from the `ResponseBody` object')
            elif isinstance(self.request, RequestBody):
                self.schema['request'] = self.request.dump()
            else:
                raise Exception('The `response` parameter is not inherited from the `ResponseBody` object')

        if hasattr(self, "response") and self.response is not None:
            if isinstance(self.response, dict):
                self.schema['response'] = {}
                for key, response in self.response.items():
                    self.schema['response'].update({key: []})
                    if isinstance(response, list):
                        for item in response:
                            if isinstance(item, ResponseBody):
                                self.schema['response'][key].append(item.dump())
                            else:
                                raise Exception(
                                    'The response parameter is not inherited from the `ResponseBody` object')
                    elif isinstance(response, ResponseBody):
                        self.schema['response'].update({key: response.dump()})
                    else:
                        raise Exception('The response parameter is not inherited from the `ResponseBody` object')
            elif isinstance(self.response, ResponseBody):
                self.schema['response'] = self.response.dump()
            else:
                raise Exception('The `response` parameter is not inherited from the `ResponseBody` object')

        if hasattr(self, "parameters") and self.parameters is not None:
            if isinstance(self.parameters, list):
                self.schema['parameters'] = []
                for parameter in self.parameters:
                    if isinstance(parameter, BaseParameter):
                        self.schema['parameters'].append(parameter.dump())
                    else:
                        raise Exception('The `parameters` parameter is not inherited from the `BaseParameter` object')
            elif isinstance(self.parameters, BaseParameter):
                self.schema['parameters'] = self.parameters.dump()
            else:
                raise Exception('The `parameters` parameter is not inherited from the `BaseParameter` object')

        if hasattr(self, "security") and self.security is not None:
            if "components" not in self.schema:
                self.schema["components"] = {}
            self.schema["components"]["securitySchemes"] = {}
            for item in self.security:
                self.schema["components"]["securitySchemes"].update(item.dump())

        return self.schema
