import asyncio
import traceback
import urllib
from urllib.parse import urlparse, urlunparse, parse_qs
from operator import itemgetter
import re

from muscles.core import Dependency
from muscles.core import EventsStorageInterface
from muscles.core import inject
import json
import sys
import email.parser
import email.policy
import tempfile
import os
from http.cookies import SimpleCookie
from muscles.core import normalize_path
from .error_handler import ApplicationException, AttributeException

try:
    import magic
except ImportError:
    magic = None


def detect_mime_from_buffer(value):
    if magic is None:
        return 'application/octet-stream'
    try:
        return magic.Magic(mime=True).from_buffer(value)
    except ImportError:
        return 'application/octet-stream'


def normalize_mime_type(value):
    return 'image/jpeg' if value == 'image/jpg' else value


def _split_on_find(content, bound):
    point = content.find(bound)
    return content[:point], content[point + len(bound):]


class ImproperBodyPartContentException(Exception):
    pass


class NonMultipartContentTypeException(Exception):
    pass


def _header_parser(string, encoding):
    major = sys.version_info[0]
    if major == 3:
        string = string.decode(encoding)
    headers = email.parser.HeaderParser().parsestr(string).items()
    return (
        (k, v) for k, v in headers
    )


class BodyPart(object):
    """
    Часть объекта ``Response`` для хранения частей тела запроса

    """

    def __init__(self, content, encoding):
        self.encoding = encoding
        headers = {}
        # Split into header section (if any) and the content
        if b'\r\n\r\n' in content:
            first, self.content = _split_on_find(content, b'\r\n\r\n')
            if first != b'':
                headers = _header_parser(first.lstrip(), encoding)
        else:
            raise ImproperBodyPartContentException(
                'content does not contain CR-LF-CR-LF'
            )
        self.headers = headers or {}
        self._name = None
        self._filename = None
        for k, v in self.headers:
            if k == 'Content-Disposition':
                v = v.split("; ")
                for vi in v:
                    u = vi.split("=")
                    if len(u) > 1:
                        if u[0] == 'name':
                            self._name = u[1].strip('"')
                        if u[0] == 'filename':
                            self._filename = u[1].strip('"')

    @property
    def text(self):
        """
        Контент части запроса
        :return: unicode
        """
        return self.content.decode(self.encoding)

    @property
    def name(self):
        """
        Имя раздела в unicode.
        :return: unicode
        """
        try:
            return self._name.decode(self.encoding)
        except:
            return self._name

    @property
    def filename(self):
        """
        Имя файла
        :return: unicode
        """
        try:
            return self._filename.decode(self.encoding)
        except:
            return self._filename


class FileStorage:
    """
    Хранилище файлов
    """

    def __init__(self, name, value, filename=None, mime_type=None, file_type=None, bytes_read=0):
        self._name = name
        self._value = value
        # TODO Если оставить сохранение в файл то открывается уязвимость переполнения файловой системы,
        #  лучше переделать на поток
        self.fp = tempfile.NamedTemporaryFile(prefix="tempfile_", suffix="_muscular")
        self.fp.write(self._value)
        self.fp.seek(0)
        self._filepath = self.fp.name
        self._filename = filename
        self._file_type = file_type
        if mime_type is None:
            mime_type = detect_mime_from_buffer(self._value)
        self._mime_type = mime_type
        self._bytes_read = bytes_read or len(self._value)

    def __del__(self):
        try:
            self.fp.close()
        except AttributeError:
            pass

    def load(self):
        return self.fp.read()

    @property
    def name(self):
        """
        Имя файла
        :return: string
        """
        return self._name

    @property
    def filepath(self):
        """
        Путь к файлу
        :return: string
        """
        return self._filepath

    @property
    def filename(self):
        """
        Имя файла
        :return: string
        """
        return self._filename

    @property
    def file_type(self):
        """
        Тип файла
        :return: string
        """
        return self._file_type

    @property
    def bytes_read(self):
        """
        Байт файла
        :return: string
        """
        return self._bytes_read

    @property
    def value(self):
        return self._value

    @property
    def content_type(self):
        return self._mime_type

    @property
    def safe_filename(self):
        name = os.path.basename(self._filename or self._name or "upload.bin")
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
        return name or "upload.bin"

    def validate(self, max_size=None, allowed_content_types=None):
        if max_size is not None and self._bytes_read > max_size:
            raise ValueError("Uploaded file is too large")
        if allowed_content_types is not None and self._mime_type not in set(allowed_content_types):
            raise ValueError("Uploaded file content type is not allowed")
        return self

    def __str__(self):
        return "FileStorage(%r, %r)" % (self._mime_type, self.filename)

    def __repr__(self):
        """Возвращает строку для отображения"""
        return "FileStorage(%r, %r)" % (self._mime_type, self.filename)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.fp.close()

    def save(self, filepath=None, safe=False):
        """
        Сохраняет файл по указаному пути
        :param filepath: путь сохранения файла
        :return: None
        """
        if safe and filepath is not None and os.path.isdir(filepath):
            filepath = os.path.join(filepath, self.safe_filename)
        self._filepath = os.path.abspath(filepath)
        self._filename = os.path.basename(self._filepath)
        self.fp.seek(0)
        with open(filepath, 'wb') as fp:
            fp.write(self.fp.read())
        self.fp.close()
        self.fp = open(filepath, 'rb')
        return self._filepath


class FieldStorage:
    """
    Хранилище полей формы
    """

    def __init__(self, name, value):
        self._name = name
        self._value = value

    @property
    def name(self):
        """
        Название поля
        :return: string
        """
        return self._name

    @property
    def value(self):
        """
        Значение формы
        :return: string
        """
        return self._value

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        """Возвращает строку для отображения"""
        return "FieldStorage(%r, %r)" % (self.name, self.value)

    def __enter__(self):
        return self


def parse_multipart_body(content_type, body, encoding='utf-8'):
    fields = {}
    raw_message = (
        "Content-Type: %s\r\nMIME-Version: 1.0\r\n\r\n" % content_type
    ).encode(encoding) + body
    message = email.parser.BytesParser(policy=email.policy.default).parsebytes(raw_message)
    for part in message.iter_parts():
        name = part.get_param('name', header='content-disposition')
        if not name:
            continue
        payload = part.get_payload(decode=True) or b''
        filename = part.get_filename()
        if filename is not None:
            content_type = normalize_mime_type(part.get_content_type())
            value = FileStorage(
                name,
                payload,
                filename=filename,
                mime_type=content_type,
                file_type=content_type,
                bytes_read=len(payload),
            )
        else:
            charset = part.get_content_charset() or encoding
            value = FieldStorage(name, payload.decode(charset))

        if name in fields:
            if not isinstance(fields[name], list):
                fields[name] = [fields[name]]
            fields[name].append(value)
        else:
            fields[name] = value
    return fields


class Request:
    """
    Тело запроса к сервверу
    """

    __charset = 'utf8'
    _before_start = []

    def __init__(self,
                 type: str = None,
                 protocol: str = None,
                 url: str = None,
                 method: tuple = None,
                 server: tuple = None,
                 remote_addr: tuple = None,
                 headers: dict = None,
                 body=None,
                 is_json=False,
                 is_xml=False,
                 is_form=False,
                 is_buffer=False,
                 **kwargs
                 ):
        """
        Конструктор запроса

        :param protocol: Протокол запроса
        :param url: URL запроса
        :param method: Метод запроса GET, POST, PUT, DELETE, ...
        :param server: Сервер
        :param remote_addr: Откуда поступил запрос
        :param headers: Заголовки запроса
        :param body: Тело запроса
        :param kwargs:
        """

        #: Parsed parts of the multipart response body
        self.parts = tuple()

        self.type = type
        self._is_json = is_json
        self._is_xml = is_xml
        self._is_form = is_form
        self._is_buffer = is_buffer

        #: The method the request was made with, such as ``GET``.
        self._method = method.upper() if method is not None else 'None'
        #: The Protocol
        self.protocol = protocol.upper() if protocol is not None else None
        #: The URL
        self.url = url
        #: The address of the server. ``(host, port)``, ``(path, None)``
        #: for unix sockets, or ``None`` if not known.
        self.server = server
        #: The headers received with the request.
        self.headers = headers or {}
        #: The address of the client sending the request.
        self.remote_addr = remote_addr

        if isinstance(body, BaseException):
            self._exception = body
            self._body = None
        else:
            self._body = body
            self._exception = None

        o = urlparse(self.url)
        self.scheme = o.scheme
        self.netloc = o.netloc
        self.path = o.path
        self._query = o.query
        self.fragment = o.fragment
        self.username = o.username
        self.password = o.password
        self.hostname = o.hostname
        self.port = o.port

        self.route = None
        self.actor = None

        """ Запускает обработку событий инициализации запроса Request """
        events = Dependency.resolve(EventsStorageInterface)
        if events is not None and events.get('init_request') is not None:
            for func in events.get('init_request'):
                func(request=self)

    @staticmethod
    @inject(EventsStorageInterface)
    def init_request(evnetStorage: EventsStorageInterface):
        """
        Декоратор, который вешает событие инициализации запроса Request

        :return:
        """

        def decorator(func):
            evnetStorage.add('init_request', func)

        return decorator

    @staticmethod
    @inject(EventsStorageInterface)
    def before_request(evnetStorage: EventsStorageInterface):
        """
        Декоратор, который вешает событие инициализации запроса Request

        :return:
        """

        def decorator(func):
            evnetStorage.add('before_request', func)

        return decorator

    @staticmethod
    @inject(EventsStorageInterface)
    def before_response(evnetStorage: EventsStorageInterface):
        """
        Декоратор, который вешает событие инициализации запроса Request

        :return:
        """

        def decorator(func):
            evnetStorage.add('before_response', func)

        return decorator

    @property
    def origin(self) -> str:
        """
        HTTP Метод
        """
        return self.headers.get('Origin', None)

    @property
    def prefix(self) -> bool:
        """
        Префикс к адресу
        """
        chunks = self.path.split('/')
        return chunks[1] if len(chunks) > 0 and chunks[0] == '' else None

    @property
    def method(self) -> bool:
        """
        HTTP Метод
        """
        return self._method

    @property
    def is_exception(self) -> bool:
        """
        Exception?
        """
        return self._exception is not None or isinstance(self._body, BaseException)

    @property
    def exception(self) -> any:
        """
        Exception?
        """
        if self._exception is not None:
            return self._exception
        elif isinstance(self._body, BaseException):
            return self._body
        else:
            return None

    @exception.setter
    def exception(self, value: BaseException) -> None:
        """
        Exception?
        """
        self._exception = value

    @property
    def is_post(self) -> bool:
        """
        POST?
        """
        return self._method.upper() == 'post'.upper()

    @property
    def is_get(self) -> bool:
        """
        GET?
        """
        return self._method.upper() == 'get'.upper()

    @property
    def is_put(self) -> bool:
        """
        PUT?
        """
        return self._method.upper() == 'put'.upper()

    @property
    def is_delete(self) -> bool:
        """
        DELETE?
        """
        return self._method.upper() == 'delete'.upper()

    @property
    def is_secure(self) -> bool:
        """
        ``True`` Если (HTTPS or WSS).
        """
        return self.scheme in {"https", "wss"}

    @property
    def base_url(self) -> str:
        """
        Получаем разобранный урл запроса
        :return:
        """
        return urlunparse(scheme=self.scheme, hostname=self.hostname, port=self.port, path=self.path)

    @property
    def host_url(self) -> str:
        """
        Получаем хост запроса
        :return:
        """
        return urlunparse(scheme=self.scheme, hostname=self.hostname, port=self.port)

    @property
    def host(self) -> str:
        """
        Получаем хост запроса
        """
        return urlunparse(
            scheme=self.scheme, hostname=self.hostname, port=self.port
        )

    @property
    def query(self) -> dict:
        """
        Получаем часть запроса query в формате ключ/значение
        """
        q = parse_qs(self._query)
        p = {}
        for item_key in q:
            p.update({item_key: q[item_key] if len(q[item_key]) > 1 else q[item_key][0]})
        return p

    @property
    def m_query(self) -> dict:
        """
        Получаем часть запроса query в формате ключ/[значения] или ключ/значение
        """
        vals = urllib.parse.parse_qsl(self._query)
        params = {}
        if vals and isinstance(vals, list):
            for val in vals:
                if val[0] in params and not isinstance(params[val[0]], list):
                    d = [params[val[0]], val[1]]
                    del params[val[0]]
                    params[val[0]] = val[1]
                    params.update({val[0]: d})
                elif val[0] in params and isinstance(params[val[0]], list):
                    params[val[0]].append(val[1])
                else:
                    params.update({val[0]: val[1]})
        return params

    @property
    def raw_query(self) -> list:
        """
        Получаем часть запроса query в RAW формате
        """
        return urllib.parse.parse_qsl(self._query)

    @property
    def cookies(self) -> "ImmutableMultiDict[str, str]":
        """
        Печеньки запроса
        :return:
        """
        if self.headers.get("Cookie"):
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie"))
            return {k: v.value for k, v in cookie.items()}
        else:
            return {}

    @property
    def content_length(self) -> [int, None]:
        """
        Размер запроса
        """
        if self.headers.get("Transfer-Encoding", "") == "chunked":
            return None

        content_length = self.headers.get("Content-Length")
        if content_length is not None:
            try:
                return max(0, int(content_length))
            except (ValueError, TypeError):
                pass

        return None

    @property
    def accept_language(self) -> []:
        """
        Язык запроса
        """
        accept_language = self.headers.get("Accept-Language")

        def normalized(language):
            l = language.lower().split(';q=')
            return l[0], float(l[1]) if len(l) > 1 else float(1)

        if accept_language is not None:
            accept_language = accept_language.lower().split(',')
            try:
                languages = [normalized(language) for language in accept_language]
                languages = sorted(languages, key=itemgetter(1), reverse=True)
                return [language[0] for language in languages]
            except (ValueError, TypeError) as e:
                pass
        return None

    @property
    def accept_encoding(self) -> [str, None]:
        """
        Кодировка запроса
        """
        accept_encoding = self.headers.get("Accept-Encoding")

        def normalized(encoding):
            l = encoding.lower().split(';q=')
            return l[0], float(l[1]) if len(l) > 1 else float(1)

        if accept_encoding is not None:
            accept_encoding = accept_encoding.lower().split(',')
            try:
                encodings = [normalized(encoding) for encoding in accept_encoding]
                encodings = sorted(encodings, key=itemgetter(1), reverse=True)
                return [encoding[0] for encoding in encodings]
            except (ValueError, TypeError) as e:
                pass
        return None

    @property
    def accept(self) -> [str, None]:
        """
        Accept: text/html, application/xhtml+xml, application/xml;q=0.9, */*;q=0.8
        """
        accept = self.headers.get("Accept")

        def normalized(accept):
            l = accept.lower().split(';q=')
            return l[0], float(l[1]) if len(l) > 1 else float(1)

        if accept is not None:
            accept = accept.lower().split(',')
            try:
                accepts = [normalized(acp) for acp in accept]
                accepts = sorted(accepts, key=itemgetter(1), reverse=True)
                return [accept[0] for accept in accepts]
            except (ValueError, TypeError) as e:
                pass
        return None

    @property
    def content_type(self) -> [str, None]:
        """
        Content-Type: text/html; charset=UTF-8 => text/html
        Content-Type: multipart/form-data; boundary=something => multipart/form-data
        """
        content_type = self.headers.get("Content-Type", 'text/html; charset=UTF-8')
        if content_type is not None:
            try:
                content_type = content_type.lower().split("; ")
                return content_type[0]
            except (ValueError, TypeError):
                pass

        return None

    @property
    def boundary(self) -> [str, None]:
        """

        Content-Type: text/html; charset=UTF-8 => text/html
        Content-Type: multipart/form-data; boundary=something => multipart/form-data
        """
        boundary = self.headers.get("Content-Type")
        if boundary is not None:
            try:
                boundary = boundary.split("; ")
                if len(boundary) > 1:
                    boundary = boundary[1].split("=")
                    return boundary[1] if len(boundary) > 1 and boundary[0].lower() == 'boundary' else None
                return None
            except (ValueError, TypeError):
                pass
        return None

    @property
    def user_agent(self) -> [str, None]:
        """
        Браузер пользователя
        """
        user_agent = self.headers.get("User-Agent")
        if user_agent is not None:
            try:
                return user_agent
            except (ValueError, TypeError):
                pass

        return None

    @property
    def content_charset(self) -> [str, None]:
        """
        Content-Type: text/html; charset=UTF-8 => utf-8
        Content-Type: multipart/form-data; boundary=something => None
        """
        content_type = self.headers.get("Content-Type")
        if content_type is not None:
            try:
                content_type = content_type.lower().split("; ")
                if len(content_type) > 1:
                    charset = content_type[1].split("=")
                    return charset[1].lower() if len(charset) > 1 and charset[0] == 'charset' else None
            except (ValueError, TypeError):
                pass

        return None

    @property
    def charset(self) -> [str, None]:
        """
        Кодировка
        :return:
        """
        return self.content_charset if self.content_charset else self.__charset

    @property
    def json(self):
        """
        Разбор тела пост запроса
        :return:
        """
        return self._body if self._is_json else {}

    @property
    def xml(self):
        """
        Разбор тела пост запроса
        :return:
        """
        return self._body if self._is_xml else {}

    @property
    def is_xml(self):
        """
        Разбор тела пост запроса
        :return:
        """
        return self._is_xml

    @property
    def is_json(self):
        """
        Разбор тела пост запроса
        :return:
        """
        return self._is_json

    @property
    def body(self):
        """
        Разбор тела пост запроса
        :return:
        """
        if self._body is None:
            raise AttributeException(reason="request.body is empty")
        return self._body if not self._is_buffer else None

    @property
    def raw(self):
        """
        Разбор тела пост запроса
        :return:
        """
        try:
            return self._body
        except Exception:
            return None

    @property
    def forms(self):
        """
        Разбор формы запроса
        :return:
        """
        """
        Файлы в запросе
        :return:
        """
        if not self._is_form:
            return None
        fields = {}
        for part in self._body:
            if isinstance(self._body[part], FieldStorage):
                fields[part] = self._body[part]
            elif isinstance(self._body[part], list):
                fields[part] = []
                for el_part in self._body[part]:
                    if isinstance(el_part, FieldStorage):
                        fields[part].append(el_part)
        return fields

    @property
    def buffer(self):
        """
        Разбор формы запроса
        :return:
        """
        return self._body if self._is_buffer else None

    @property
    def files(self):
        """
        Файлы в запросе
        :return:
        """
        if not self._is_form:
            return None
        files = {}
        for part in self._body:
            if isinstance(self._body[part], FileStorage):
                files[part] = self._body[part]
        return files

    @property
    def user(self):
        return self.actor


class RequestMaker:
    text_mime_types = [
        'text/html',
        'text/plain',
        'text/calendar',
        'application/xml',
        'application/json',
        'application/ld+json',
        'text/javascript',
        'text/javascript'
    ]

    def __init__(self, scope, receive):
        self.scope = scope
        self.receive = receive

        self.path = normalize_path(scope.get('path') or '/') if 'path' in scope else None
        self.query_string = scope['query_string'].decode('utf-8') if 'query_string' in scope else None
        self.headers = dict((key.decode('utf-8'), value.decode('utf-8')) for key, value in self.scope['headers']) if 'headers' in scope else {}
        self._request_types = {
            'multipart/form-data': 'multipart',
            'application/x-www-form-urlencoded': 'form',
            'text/plain': 'text',
            'text/html': 'html',
            'application/javascript': 'javascript',
            'application/json': 'json',
            'application/xml': 'xml',
        }

        # Получаем тело запроса (асинхронно)
        self.body = None

    async def fetch_body(self):
        """ Асинхронное получение тела запроса """
        try:
            self.body = await self.get_request_body()
        except asyncio.exceptions.InvalidStateError as e:
            self.body = None

    async def get_request_body(self):
        """
        Чтение тела запроса через функцию receive (асинхронно)
        """
        body = b''
        more_body = True

        while more_body:
            message = await self.receive()
            if message['type'] == 'lifespan.startup':
                body += message.get('body', b'')
                more_body = message.get('more_body', False)
            elif message['type'] == 'http.request':
                body += message.get('body', b'')
                more_body = message.get('more_body', False)
        return body

    @property
    def request_type(self):
        """ Определение типа запроса на основе заголовков """
        headers = self.headers
        if 'content-type' not in headers and 'accept' not in headers:
            return None
        for content_type in self._request_types:
            if 'content-type' in headers and content_type in headers['content-type']:
                return self._request_types[content_type]
            elif 'accept' in headers and content_type in headers['accept'].split(","):
                return self._request_types[content_type]
        return None

    @property
    def charset(self):
        """ Получение charset из заголовков """
        charset = 'utf-8'
        try:
            content_type = self.headers.get('content-type', 'text/html; charset=UTF-8')
            content_type = content_type.lower().split("; ")
            if len(content_type) > 1:
                _charset = content_type[1].split("=")
                charset = _charset[1].lower() if len(_charset) > 1 and _charset[0] == 'charset' else 'utf-8'
        except ValueError:
            pass
        return charset

    def make_body_from_form(self):
        """ Парсинг данных из формы (application/x-www-form-urlencoded) """
        fields = {}
        data = urllib.parse.parse_qsl(self.body.decode(self.charset))
        for _data in data:
            if fields.get(_data[0]) and isinstance(fields[_data[0]], list):
                fields[_data[0]].append(_data[1])
            elif fields.get(_data[0]):
                fields[_data[0]] = [fields[_data[0]]]
                fields[_data[0]].append(_data[1])
            else:
                fields[_data[0]] = _data[1]
        return fields

    async def make_body_from_buffer(self):
        if self.body is None:
            await self.fetch_body()
        return self.body

    async def make_body_from_raw(self):
        input = await self.make_body_from_buffer()
        mime_type = self.headers.get('content-type') or detect_mime_from_buffer(input)
        mime_type = normalize_mime_type(mime_type.split(';', 1)[0])
        if mime_type not in self.text_mime_types:
            input = FileStorage(None, input,
                                filename=None,
                                mime_type=mime_type,
                                file_type=mime_type,
                                bytes_read=len(input),
                                )
        return input

    async def make_body_from_json(self):
        input = await self.make_body_from_buffer()
        try:
            if len(input) > 0:
                return json.loads(input.decode(self.charset))
            else:
                return {}
        except json.JSONDecodeError as e:
            raise ApplicationException(reason="JSON DECODE ERROR", body=e)
        except UnicodeDecodeError as e:
            raise ApplicationException(reason="JSON DECODE ERROR", body=e)

    async def make_body_from_form(self):
        input = await self.make_body_from_buffer()
        fields = {}
        data = urllib.parse.parse_qsl(input.decode(self.charset))
        for _data in data:
            if fields.get(_data[0]) and isinstance(fields[_data[0]], list):
                fields[_data[0]].append(FieldStorage(_data[0], _data[1]))
            elif fields.get(_data[0]):
                fields[_data[0]] = [fields[_data[0]]]
                fields[_data[0]].append(FieldStorage(_data[0], _data[1]))
            else:
                fields[_data[0]] = FieldStorage(_data[0], _data[1])
        return fields

    async def make_body_from_multipart(self):
        """
        Разбираем данные multipart/form-data.
        """
        input = await self.make_body_from_buffer()
        return parse_multipart_body(self.headers.get('content-type', ''), input, self.charset)

    def make_headers(self) -> dict:
        """
        офрмирует словарь заголовков запроса

        :return: dict
        """
        headers = {}
        if len(self.headers) > 0:
            headers.update({'Host': self.headers.get('Host', None)})
            headers.update({'Connection': self.headers.get('Connection', None)})
            headers.update({'Pragma': self.headers.get('Pragma', None)})
            headers.update({'Cache-Control': self.headers.get('Cache-Control', None)})
            headers.update({'Accept': self.headers.get('Accept', None)})
            headers.update({'Accept-Language': self.headers.get('Accept-Language', None)})
            headers.update({'Accept-Encoding': self.headers.get('Accept-Encoding', None)})
            headers.update({'Origin': self.headers.get('Origin', None)})
            headers.update({'User-Agent': self.headers.get('User-Agent', None)})
            headers.update({'Content-Length': self.headers.get('Content-Length', '0')})
            headers.update({'Content-Type': self.headers.get('Content-Type', 'text/html; charset=UTF-8')})
            for key in self.headers:
                if 'HTTP_' == key[0:5] or 'http_' == key[0:5]:
                    headers.update({key[5:].title().replace('_', '-'): self.headers[key]})
                elif 'X-' == key[0:2] or 'x-' == key[0:2]:
                    headers.update({key.title(): self.headers[key]})
                else:
                    headers.update({key.title(): self.headers[key]})
        return headers

    async def make(self) -> Request:
        """
        Формируем объект Request

        :return: Request
        """
        scope = self.scope
        if self.request_type and hasattr(self, "make_body_from_%s" % self.request_type):
            try:
                method = getattr(self, "make_body_from_%s" % self.request_type)
                wsgi_input = await method()
            except ApplicationException as ex:
                wsgi_input = ex
        else:
            wsgi_input = await self.make_body_from_raw()
        host = self.headers.get('host', None)
        request = Request(
            type=scope['type'] if 'type' in scope else None,
            method=scope['method'] if 'method' in scope else None,
            protocol=scope['scheme'] if 'scheme' in scope else None,
            url="%s%s%s%s" % (
                "%s://" % scope['scheme'] if host is not None else '',
                host if host is not None else '',
                self.path,
                "?%s" % scope['query_string'].decode('utf-8') if 'query_string' in scope and len(scope['query_string']) > 0 else ''
            ),
            server=(scope['server'][0], scope['server'][1]) if 'server' in scope else None,
            remote_addr=(scope['client'][0], scope['client'][1]) if 'client' in scope else None,
            headers=self.make_headers(),
            body=wsgi_input,
            is_json=self.request_type == 'json',
            is_xml=self.request_type == 'xml',
            is_form=self.request_type == 'multipart' or self.request_type == 'form',
            is_buffer=self.request_type is None
        )
        return request
