import codecs
import json
import traceback
from json import JSONEncoder
from typing import Optional, Union

from .request import Request
from ..__about__ import __version__, __name__
import mimetypes
from muscles.core import BaseModel, Collection
from .http_code import code_status
from .error_handler import ApplicationException
from .error_handler import ErrorsException


class ObjectJSONEncoder(JSONEncoder):
    def default(self, obj):
        return str(obj)


class BaseResponse:

    _headers: list[tuple] = []
    _reason: Union[str, None] = None
    request: Union[Request, None] = None
    _status: Union[str, int, None] = None
    _body: Union[BaseModel, str, int, tuple, dict, list, bytes, bool, None] = None
    _errors: Union[BaseModel, str, int, tuple, dict, list, bytes, bool, None] = None
    _file: Union[str, None] = None

    def __init__(self, *args,
                 status: Union[str, int, None] = None,
                 body: Union[BaseModel, str, int, tuple, dict, list, bytes, bool, None] = None,
                 errors: Union[BaseModel, str, int, tuple, dict, list, bytes, bool, None] = None,
                 file: Union[str, None] = None,
                 headers: list[tuple] = None,
                 reason: Union[str, None] = None,
                 trace: Union[str, list, None] = None,
                 request: Union[Request, None] = None):
        if reason is None:
            reason = None
        if headers is None:
            headers = []
        if request is not None:
            self.request = request
        if trace is None:
            trace = None
        self.trace = trace
        self._headers = headers
        self._reason = reason
        self._file = file
        if len(args) == 0:
            self._body = body
            self._status = status if status is not None else 200
        elif len(args) == 1 and body is not None:
            self._body = body
            self._status = args[0]
        elif len(args) == 1 and status is not None:
            self._body = args[0]
            self._status = status
        elif len(args) >= 2:
            self._body = args[1]
            self._status = args[0]
        else:
            self._body = body
            self._status = status if status is not None else 200
        self._errors = errors

    def make_body(self):
        def _recursive_dict_adapt(dictionary):
            if isinstance(dictionary, dict):
                new_dict = {}
                for key, value in dictionary.items():
                    new_dict[key] = _recursive_dict_adapt(value)
                return new_dict
            elif isinstance(dictionary, list):
                new_list = []
                for value in dictionary:
                    new_list.append(_recursive_dict_adapt(value))
                return new_list
            elif isinstance(dictionary, BaseModel) or isinstance(dictionary, Collection):
                return dictionary.to_json()
            else:
                return dictionary
        body = self.body or self.errors
        if self.type in ['json'] or isinstance(body, dict):
            try:
                body = _recursive_dict_adapt(body)
                body = json.dumps(body, cls=ObjectJSONEncoder)
                if isinstance(body, str):
                    body = codecs.encode(body, encoding='utf-8')
                elif isinstance(body, bool):
                    body = "true" if body else "false"
            except ValueError as e:
                # traceback.format_exc()
                raise ApplicationException(status=500, reason=e, body=traceback.format_exc())
            except Exception as e:
                # traceback.print_exc()
                raise ApplicationException(status=500, reason=e, body=traceback.format_exc())
        else:
            if isinstance(body, str):
                body = codecs.encode(body, encoding='utf-8')
            elif isinstance(body, bool):
                body = "true" if body else "false"
        return body

    @staticmethod
    def schema(child=None):
        if child is None:
            child = {
                "oneOf": [
                    {"type": "object"},
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "integer"},
                    {"type": "array"},
                    {"type": "boolean"},
                    {"type": "binary"},
                    {"type": "byte"},
                    {"type": "null"},
                ]
            }
        return child

    @property
    def reason(self):
        if self._reason is None:
            return ""
        return codecs.encode(str(self._reason), encoding='utf-8')

    @property
    def status(self):
        if self._status is None:
            return str(200)
        return str(self._status)

    @property
    def headers(self):
        def _condition(header):
            res = True
            if res and header[0] == 'Content-Length':
                res = False
            if res and header[0] == 'Content-Type':
                res = False
            return res

        headers = [(str(header[0]), str(header[1])) for header in self._headers if _condition(header)]

        if self.request is not None and self.request.is_json:
            content_type = 'application/json; charset=utf-8'
        elif self.type in ['json']:
            content_type = 'application/json; charset=utf-8'
        elif self.type in ['text']:
            content_type = 'text/html; charset=utf-8'
        else:
            content_type = 'text/html; charset=utf-8'

        if self._file:
            content_type, encoding = mimetypes.guess_type(self._file)

            if content_type is None:
                content_type = "application/octet-stream"
            headers.append(('Content-Type', content_type))
            # Don't send encoding for attachments, it causes browsers to
            # save decompress tar.gz files.
            if encoding is not None:
                headers.append(("Content-Encoding", encoding))
        elif self.body:
            headers.append(('Content-Length', str(len(self.make_body()))))
            headers.append(('Content-Type', content_type))

        headers.append(('Server', str(' '.join([__name__, __version__]))))

        if not any(item[0] == "Content-Type" for item in headers):
            headers.append(('Content-Type', 'text/html; charset=utf-8'))
            # headers.append(('Content-Length', str(len(self.make_body()))))
        return headers

    @headers.setter
    def headers(self, headers):
        self._headers = headers

    def header_append(self, header: tuple[str, str]):
        # Проверяем, есть ли заголовок с таким именем
        for i, _header in enumerate(self._headers):
            if _header[0] == header[0]:  # Сравнение по имени заголовка
                self._headers[i] = header  # Замена существующего заголовка
                break
        else:
            self._headers.append(header)  # Если заголовка нет, добавляем его

    @property
    def body(self):
        body = self._body
        if body is None or body == '':
            body = ''
        return body

    @body.setter
    def body(self, value):
        self._body = value

    @property
    def errors(self):
        errors = self._errors
        if errors is None or errors == '' or errors == {}:
            errors = {}
        return errors

    @property
    def type(self):
        body = self._body
        if isinstance(body, str):
            response_type = "text"
        elif isinstance(body, bytes):
            ''' Ничего не делаем, уже в нужном формате '''
            response_type = "raw"
        elif isinstance(body, Response) or isinstance(body, BaseModel) or isinstance(body, Collection):
            response_type = "json"
        elif isinstance(body, dict):
            response_type = "json"
        elif isinstance(body, list):
            response_type = "json"
        elif body is None or body == '':
            response_type = "text"
        else:
            response_type = "raw"
        return response_type

    @staticmethod
    def file(headers: Optional[list] = None, file: str = None):
        """
        Формируем файл ответа
        :param status: HTTP Код статуса ответа 404=Not Found
        :param reason: Расшифровка статуса ответа
        :param headers: Заголовки ответа
        :param file: Файлы ответа
        :return:
        """
        if headers is None:
            headers = []

        def _condition(header):
            res = True
            if res and header[0] == 'Content-Length':
                res = False
            if res and header[0] == 'Content-Type':
                res = False
            return res

        headers = [(str(header[0]), str(header[1])) for header in headers if _condition(header)]

        if file:
            content_type, encoding = mimetypes.guess_type(file)

            if content_type is None:
                content_type = "application/octet-stream"

            # Don't send encoding for attachments, it causes browsers to
            # save decompress tar.gz files.
            if encoding is not None:
                headers.append(("Content-Encoding", encoding))

            headers.append(('Content-Type', content_type))

        return Response(status=200, headers=headers, file=file)

    @staticmethod
    def abort(http_status,
              errors: list[dict] = None,
              reason: Union[str, BaseException, None] = None) -> BaseException:
        """
        Прерываем запрос с кодом и текстом
        :param http_status: HTTP Код статуса ответа 404=Not Found
        :param reason: Расшифровка статуса ответа
        :param errors: Расшифровка статуса ответа
        :return:
        """
        if reason is None and str(http_status) in code_status:
            reason = code_status[str(http_status)]['message']
        if errors is None:
            raise ApplicationException(http_status, reason=str(reason))
        else:
            raise ErrorsException(http_status, reason=str(reason), body=errors)

    @staticmethod
    def redirect(redirection, status: Optional[int] = None, reason: Optional[str] = None):
        """
        Формируем редирект на другой адрес
        :param redirection:  для редиректа
        :param status: HTTP Код статуса ответа
        :param reason: Текст для расшифровки
        :return:
        """
        if isinstance(redirection, tuple):
            status = redirection[0]
            url = redirection[1]
        elif isinstance(redirection, str):
            status = status if status else 307
            url = redirection
        else:
            status = status if status else 307
            url = redirection
        return Response(status=status, reason=reason, headers=[('Location', url)])

    @staticmethod
    def not_found(reason=None):
        """
        Формирует ответ - Страница не найдена
        :param reason: Текст ответа
        :return:
        """
        return Response(status=404, reason=reason)

    @property
    def http_status(self):
        """
        Формирует HTTP статус
        :return: string
        """
        reason = self.reason
        if reason is None and self.status in code_status:
            reason = code_status[self.status]['message']
        return '%s %s' % (self.status, reason.decode('utf8') if isinstance(reason, bytes) else reason)


class Response(BaseResponse):
    def make_body(self):
        def _recursive_dict_adapt(dictionary):
            if isinstance(dictionary, dict):
                new_dict = {}
                for key, value in dictionary.items():
                    new_dict[key] = _recursive_dict_adapt(value)
                return new_dict
            elif isinstance(dictionary, list):
                new_list = []
                for value in dictionary:
                    new_list.append(_recursive_dict_adapt(value))
                return new_list
            elif isinstance(dictionary, BaseModel) or isinstance(dictionary, Collection):
                return dictionary.to_json()
            else:
                return dictionary

        body = self.body
        errors = self.errors
        if self.type in ['json']:
            try:
                status = self.status
                if status == "200":
                    status = "SUCCESS"
                elif status == "403":
                    status = "ACCESS DENIED"
                elif status == "500":
                    status = "ERROR"
                elif status == "418":
                    status = "I`AM NOT TEAPOT"
                elif status == "422":
                    status = "UNPROCESSABLE ENTITY"
                else:
                    status = "FAIL"
                body = _recursive_dict_adapt(body)
                errors = _recursive_dict_adapt(errors)
                if status == "SUCCESS":
                    body = json.dumps({
                        "status": status,
                        "data": body,
                    }, cls=ObjectJSONEncoder)
                else:
                    body = json.dumps({
                        "status": status,
                        "error": body,
                    }, cls=ObjectJSONEncoder)
                body = codecs.encode(body, encoding='utf-8')
            except ValueError as e:
                traceback.print_stack()
                raise Exception(500, e)
        else:
            body = codecs.encode(body, encoding='utf-8')
        return body

    @staticmethod
    def schema(status=200, child=None):
        if child is None:
            child = {
                "oneOf": [
                    {"type": "object"},
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "integer"},
                    {"type": "array"},
                    {"type": "boolean"},
                    {"type": "binary"},
                    {"type": "byte"},
                    {"type": "null"},
                ]
            }
        schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": [
                        "SUCCESS",
                        "FAIL",
                        "ERROR",
                        "ACCESS DENIED",
                        "I`AM NOT TEAPOT",
                        "UNPROCESSABLE ENTITY",
                    ]
                },
                "data": child,
                "errors": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "string",
                    }
                }
            },
        }
        if status == 200:
            schema["properties"].update({"data": child})
        elif status == 404:
            schema["properties"].update({"errors": {
                "type": "object",
                "additionalProperties": {
                    "type": "string",
                }
            }})
        else:
            schema["properties"].update({"errors": {
                "type": "object",
                "additionalProperties": {
                    "type": "string",
                }
            }})
        return schema


class BadResponse(Response):
    def make_body(self):
        def _recursive_dict_adapt(dictionary):
            if isinstance(dictionary, dict):
                new_dict = {}
                for key, value in dictionary.items():
                    new_dict[key] = _recursive_dict_adapt(value)
                return new_dict
            elif isinstance(dictionary, list):
                new_list = []
                for value in dictionary:
                    new_list.append(_recursive_dict_adapt(value))
                return new_list
            elif isinstance(dictionary, BaseModel) or isinstance(dictionary, Collection):
                return dictionary.to_json()
            else:
                return dictionary

        body = self.body
        trace = self.trace
        errors = self.errors
        if self.type in ['json']:
            try:
                status = self.status
                if status == "403":
                    status = "ACCESS DENIED"
                elif status == "500":
                    status = "ERROR"
                elif status == "418":
                    status = "I`AM NOT TEAPOT"
                elif status == "422":
                    status = "UNPROCESSABLE ENTITY"
                elif status == "200":
                    status = "SUCCESS"
                else:
                    status = "FAIL"
                body = _recursive_dict_adapt(body)
                errors = _recursive_dict_adapt(errors)
                body = json.dumps({
                    "status": status,
                    "body": body,
                    "trace": trace,
                    "errors": errors,
                }, cls=ObjectJSONEncoder)
                body = codecs.encode(body, encoding='utf-8')
            except ValueError as e:
                traceback.print_stack()
                raise Exception(500, e)
        else:
            if (body is None or body == '') and trace is None:
                body = codecs.encode("{}", encoding='utf-8')
            else:
                body = codecs.encode("%s\n%s" % (body, "\n".join(trace) if isinstance(trace, list) else trace), encoding='utf-8')
        return body

    @staticmethod
    def schema(child=None):
        if child is None:
            child = {
                "oneOf": [
                    {"type": "object"},
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "integer"},
                    {"type": "array"},
                    {"type": "boolean"},
                    {"type": "binary"},
                    {"type": "byte"},
                    {"type": "null"},
                ]
            }
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": [
                        "ERROR",
                        "SUCCESS",
                        "FAIL",
                        "ACCESS DENIED",
                        "I`AM NOT TEAPOT",
                        "UNPROCESSABLE ENTITY",
                    ]
                },
                "errors": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "string",
                    }
                }
            },
        }


class MakeResponse:

    def __init__(self, response: BaseResponse):
        self.response = response

    @property
    def body(self):
        return self.response.make_body()

    @property
    def http_status(self):
        return self.response.http_status

    @property
    def status(self):
        return self.response.status

    @property
    def headers(self):
        return self.response.headers


class JsonResponse(BaseResponse):
    def __init__(self, body=None, status: int = 200, headers: Optional[list] = None, **kwargs):
        super().__init__(status=status, body=body, headers=headers or [], **kwargs)
        self.header_append(("Content-Type", "application/json; charset=utf-8"))


class HtmlResponse(BaseResponse):
    def __init__(self, body: str = "", status: int = 200, headers: Optional[list] = None, **kwargs):
        super().__init__(status=status, body=body, headers=headers or [], **kwargs)
        self.header_append(("Content-Type", "text/html; charset=utf-8"))
