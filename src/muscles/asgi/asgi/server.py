import os
import io
import traceback
import inspect
import logging
import json

from muscles.core import NotFoundException, ApplicationException, ErrorException
from muscles.core import AttributeErrorException
from muscles.core import inject, EventsStorageInterface
from muscles.core import BaseResponse as CoreBaseResponse, normalize_response
from .request import RequestMaker
from .response import MakeResponse, BaseResponse, BadResponse, JsonResponse, HtmlResponse
from .routers import routes, itinerary
from urllib.parse import unquote

MAX_LINE = 64 * 1024
MAX_HEADERS = 100
TIMEOUT = 2
MAX_CONNECTIONS = 1000


class Transport:
    """
    Транспорт протокола стратегии
    """

    server = None

    def __init__(self):
        pass

    def init_server(self, server):
        self.server = server

    def make_response(self, response):
        pass

    def make_request(self):
        pass


class AsgiTransport(Transport):
    """
    Транспорт стратегии ASGI
    """

    async def execute(self, *args, **kwargs):
        """
        Исполняем условия транспорта
        :param args:
        :param kwargs[environ]: Окружение запроса
        :param kwargs[start_response]: Метод для ответа
        :return:
        """
        self.scope = kwargs['scope']
        self.receive = kwargs['receive']
        self.send = kwargs['send']
        return await self.handler(self.scope, self.receive, self.send)

    async def handler(self, scope, receive, send):
        """
        Обработчик транспорта

        :param scope: scope
        :param receive: receive
        :param send: Sender
        :return:
        """

        request = await self.make_request(scope, receive, send)

        if request is None:
            raise ApplicationException(status=400, reason='Bad request', body='Malformed request line')
        return await self.server.handler(request)

    @inject(EventsStorageInterface)
    async def make_response(self, response: BaseResponse, evnetStorage: EventsStorageInterface):
        """
        Отправляем ответ
        :param response: объект ответа
        :param evnetStorage: EventsStorageInterface
        :return:
        """
        try:
            if self.scope['type'] == 'lifespan':
                message = response.request.body

                if message is not None and message['type'] == 'lifespan.startup':
                    self.server.logger.debug("ASGI lifespan startup")
                    await self.send({"type": "lifespan.startup.complete"})

                elif message is not None and message['type'] == 'lifespan.shutdown':
                    self.server.logger.debug("ASGI lifespan shutdown")
                    await self.send({"type": "lifespan.shutdown.complete"})
                    return

            elif self.scope['type'] == 'http':
                before_response = evnetStorage.get('before_response')
                if before_response:
                    for handler in before_response:
                        response = handler(response)

                # Обработка HTTP-запроса
                if self.scope['method'] == 'OPTIONS':
                    response = MakeResponse(response=response)
                    self.server.logger.debug("ASGI OPTIONS status=%s", response.status)
                    await self.send({
                        'type': 'http.response.start',
                        'status': 204,  # Нет контента
                        'headers': response.headers,
                    })
                    await self.send({
                        'type': 'http.response.body',
                        'body': b'',
                    })
                else:
                    response = MakeResponse(response=response)
                    self.server.logger.debug("ASGI response status=%s", response.status)
                    await self.send({
                        'type': 'http.response.start',
                        'status': int(response.status),
                        'headers': response.headers
                    })
                    # Отправка тела ответа
                    await self.send({
                        'type': 'http.response.body',
                        'body': response.body,
                    })

            elif self.scope['type'] == 'websocket':
                # Обработка WebSocket-сообщений
                raise Exception('WebSocket not implemented')

        except Exception as ae:
            self.server.logger.exception("ASGI transport response error")
            raise ApplicationException(status=500, reason=ae, body=traceback.format_tb(ae.__traceback__))

    async def make_request(self, scope, receive, send):
        """
        Формируем обхект запроса на основании переменных запроса
        :param scope: scope
        :param receive: receive
        :param send: send
        :return: Request
        """
        try:
            requestMaker = RequestMaker(scope, receive)
            return await requestMaker.make()
        except ApplicationException as ae:
            self.server.logger.exception("ASGI request maker error")
            raise ApplicationException(status=500, reason=ae, body=traceback.format_tb(ae.__traceback__))
        except Exception as ae:
            self.server.logger.exception("ASGI request build error")
            raise ApplicationException(status=500, reason=ae, body=traceback.format_tb(ae.__traceback__))


class AsgiServer:
    """
    Объект сервера ASGI
    """

    __transport_class = AsgiTransport
    __transport = AsgiTransport
    __host = 'localhost'
    __port = 80

    def __init__(self, host, port, error_handler, logger=None, debug=False):
        self.__host = host
        self.__port = port
        self.__error_handler = error_handler
        self.logger = logger or logging.getLogger("muscles.asgi")
        self.debug = debug
        self._route_cache = {}

        self.__transport = self.__transport_class()
        self.__transport.init_server(self)

    def init_transport(self, transport):
        """
        Инициализируем транспортный протокол
        :param transport: Транспорт
        :return:
        """
        if (
            self.__transport is not None
            and self.__transport_class is transport
            and isinstance(self.__transport, transport)
        ):
            return
        self.__transport_class = transport
        self.__transport = transport()
        self.__transport.init_server(self)

    def execute(self, *args, **kwargs):
        """
        Метод исполнения протокола сервера
        :param args:
        :param kwargs:
        :return:
        """
        try:
            return self.__transport.execute(*args, **kwargs)
        except Exception as ex:
            self.logger.exception("ASGI execute error")
            return self.send_error(ex)

    def _to_protocol_response(self, response, request=None):
        def _headers_without_content(core_headers):
            prepared = []
            for key, value in (core_headers or {}).items():
                if str(key).lower() in {"content-type", "content-length"}:
                    continue
                prepared.append((key, value))
            return prepared

        def _from_core(core_response: CoreBaseResponse):
            content_type = (core_response.content_type or "").lower()
            headers = _headers_without_content(core_response.headers)
            body = core_response.body

            if "application/json" in content_type:
                if isinstance(body, bytes):
                    try:
                        body = json.loads(body.decode("utf-8"))
                    except Exception:
                        body = body.decode("utf-8")
                return JsonResponse(body=body, status=core_response.status, headers=headers, request=request)

            if "text/html" in content_type:
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                return HtmlResponse(body=body, status=core_response.status, headers=headers, request=request)

            return BaseResponse(status=core_response.status, body=body, headers=headers, request=request)

        if isinstance(response, BaseResponse):
            return response
        if isinstance(response, CoreBaseResponse):
            if response.redirect:
                return BaseResponse.redirect(response.redirect, status=response.status)
            return _from_core(response)
        core_response = normalize_response(response, request=request)
        if core_response.redirect:
            return BaseResponse.redirect(core_response.redirect, status=core_response.status)
        return _from_core(core_response)

    async def handler(self, request):
        """
        Обработчик сервера
        :param request: Запрос к серверу
        :return:
        """
        headers = []
        if request.is_exception:
            return await self.send_error(request.exception, request)
        static = routes.get_current_static(request)
        if static:
            return await self.handle_static(static, request)
        else:
            return await self.handle_request(request)

    @inject(EventsStorageInterface)
    async def handle_request(self, request, evnetStorage: EventsStorageInterface):
        """
        Обработчик запроса к серверу
        :param request: Объект запроса
        :return:
        """
        try:
            if request.type == 'lifespan' or request.type is None:
                resp = BaseResponse(status=200, body=None, request=request)
                return await self.__transport.make_response(resp)

            before_request = evnetStorage.get('before_request')
            if before_request:
                for handler in before_request:
                    resp = handler(request)
                    if resp:
                        if isinstance(resp, str):
                            resp = BaseResponse(status=200, body=resp, request=request)
                        return await self.__transport.make_response(resp)

            route_key = (
                request.path,
                request.method.lower() if request.method else "",
                (request.content_type or "").lower(),
            )
            cached_instance = self._route_cache.get(route_key)
            if cached_instance is not None:
                call, dictionary = cached_instance.get_current_route(request)
                if call:
                    request.route = call
                    request.itinerary = cached_instance
            if request.route is None:
                for _, instance in itinerary.instance_list():
                    call, dictionary = instance.get_current_route(request)
                    if call:
                        request.route = call
                        request.itinerary = instance
                        self._route_cache[route_key] = instance
                        break
            if request.route and 'instance' in request.route.keys():
                for func in request.route['instance'].get_event('before_request'):
                    func(request)

        except ErrorException as ae:
            self.logger.exception("ASGI route resolution error")
            ae.body = traceback.format_tb(ae.__traceback__)
            return await self.send_error(ae, request)
        except ImportError as ae:
            self.logger.exception("ASGI import error")
            ae = ApplicationException(status=500, reason=ae, body=traceback.format_tb(ae.__traceback__))
            return await self.send_error(ae, request)
        except KeyError as ae:
            self.logger.exception("ASGI key error")
            ae = ApplicationException(status=500, reason=ae, body=traceback.format_tb(ae.__traceback__))
            return await self.send_error(ae, request)
        except Exception as ae:
            self.logger.exception("ASGI unexpected route error")
            ae = ApplicationException(status=500, reason=ae, body=traceback.format_tb(ae.__traceback__))
            return await self.send_error(ae, request)

        if request.route:
            if request.route['redirect'] and request.route['redirect'] is not None:
                resp = BaseResponse.redirect(request.route['redirect'])
            else:
                try:
                    if hasattr(request.route['handler'], 'controller'):
                        resp = request.route['handler'](request.route['handler'].controller(), request=request,
                                                        **dictionary)
                    else:
                        resp = request.route['handler'](request=request, **dictionary)
                    if inspect.isawaitable(resp):
                        resp = await resp
                    resp = self._to_protocol_response(resp, request=request)

                    if hasattr(request.itinerary, 'modify_response'):
                        resp = request.itinerary.modify_response(resp)

                    headers = []
                    for header in resp.headers:
                        headers.append('%s: %s' % (header[0], header[1]))

                    return await self.__transport.make_response(resp)
                except ApplicationException as ae:
                    self.logger.exception("ASGI application exception")
                    ae = ApplicationException(status=400, reason=ae, body=None, traceback=traceback.format_tb(ae.__traceback__))
                    return await self.send_error(ae, request)
                except ErrorException as ae:
                    self.logger.exception("ASGI error exception")
                    ae = ApplicationException(status=500, reason=ae, body=None, traceback=traceback.format_tb(ae.__traceback__))
                    return await self.send_error(ae, request)
                except ImportError as ae:
                    self.logger.exception("ASGI import exception")
                    ae = ApplicationException(status=500, reason=ae, body=None, traceback=traceback.format_tb(ae.__traceback__))
                    return await self.send_error(ae, request)
                except KeyError as ae:
                    self.logger.exception("ASGI handler key error")
                    ae = AttributeErrorException(status=500, reason="KeyError[%s]" % ae, body=None, traceback=traceback.format_tb(ae.__traceback__))
                    return await self.send_error(ae, request)
                except Exception as ae:
                    self.logger.exception("ASGI handler unexpected exception")
                    ae = ApplicationException(status=500, reason=ae, body=None, traceback=traceback.format_tb(ae.__traceback__))
                    return await self.send_error(ae, request)
        return await self.send_error(NotFoundException(status=404, reason="Not Found"), request)

    async def handle_static(self, static, request):
        """
        Обработчик статических файлов
        :param static: Путь к диреткории с файлами
        :param request: Объект запроса
        :return:
        """
        path = request.path.replace(static['prefix'] + '/', '', 1)
        resp_file = os.path.join(static['directory'], unquote(path))

        if not os.path.isfile(resp_file):
            raise NotFoundException(status=404, reason='Not found')
        try:
            with io.open(resp_file, "rb") as f:
                body = f.read()

            resp = BaseResponse(status=200, file=resp_file, body=body, request=request)

            if static['handler'] is not None:
                resp = static['handler'](resp)

            return await self.__transport.make_response(resp)
        except Exception:
            raise NotFoundException(status=404, reason='Not found')

    async def send_error(self, err, request=None):
        """
        Отправляет ответ ошибки
        :param err: Объект ошибки или текст ошибки
        :param request: Объект запроса
        :return:
        """
        try:
            status = err.status if hasattr(err, 'status') else 500
            reason = err.reason if hasattr(err, 'reason') else str(err)
            body = err.body if hasattr(err, 'body') else str(err)
            trace = err.traceback if hasattr(err, 'traceback') else None
        except Exception as e:
            self.logger.exception("ASGI error serialization failure")
            status = 500
            reason = b'Internal Server Error'
            body = b'Internal Server Error'
            trace = err.traceback if hasattr(err, 'traceback') else None
        self.logger.error("ASGI error status=%s reason=%s", status, reason)
        if self.debug:
            self.logger.debug("%s", "\n".join(body) if isinstance(body, list) else body)
            self.logger.debug("%s", "\n".join(trace) if isinstance(trace, list) else trace)

        if issubclass(self.__error_handler, Exception):
            resp = self.__error_handler().handler(status=status, reason=reason, body=body, trace=trace, request=request)
        else:
            resp = BadResponse(status=status, reason=reason, body=body, trace=trace, request=request)
        # traceback.print_exc(file=sys.stdout)
        # call = routes.get_current_error_handler(resp)

        for _, instance in itinerary.instance_list():
            call = instance.get_current_error_handler(resp)
            if call:
                resp.body = call['handler'](resp, request)
                break

        headers = []
        for header in resp.headers:
            headers.append('%s: %s' % (header[0], header[1]))
        return await self.__transport.make_response(resp)
