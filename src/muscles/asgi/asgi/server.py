import os
import io
import traceback
import logging
import inspect
from dataclasses import is_dataclass
from inspect import iscoroutinefunction
from collections import OrderedDict

from muscles.core import NotFoundException, ApplicationException, ErrorException
from muscles.core import AttributeErrorException
from muscles.core import Dependency, inject, EventsStorageInterface
from muscles.core import BaseResponse as CoreBaseResponse
from muscles.core import normalize_problem_payload
from .request import RequestMaker
from .response import MakeResponse, BaseResponse, BadResponse, Response
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
        self.__controller_cache = OrderedDict()
        self.__controller_cache_size = 128

        self.__transport = self.__transport_class()
        self.__transport.init_server(self)

    @staticmethod
    def __is_stateful_controller(handler):
        controller = getattr(handler, 'controller', None)
        if controller is None:
            return False
        return bool(getattr(handler, 'stateful_controller', False) or getattr(controller, 'stateful_controller', False))

    def __get_controller_instance(self, handler):
        if not hasattr(handler, 'controller'):
            return None

        controller_class = handler.controller

        if self.__is_stateful_controller(handler):
            return controller_class()

        controller = self.__controller_cache.get(controller_class)
        if controller is not None:
            self.__controller_cache.move_to_end(controller_class)
            return controller

        controller = controller_class()
        self.__controller_cache[controller_class] = controller
        self.__controller_cache.move_to_end(controller_class)
        if len(self.__controller_cache) > self.__controller_cache_size:
            self.__controller_cache.popitem(last=False)

        return controller

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
        if isinstance(response, BaseResponse):
            return response

        if isinstance(response, ApplicationException):
            return BaseResponse(
                status=response.status,
                body=response.body or {"error": str(response.reason)},
                request=request,
                content_type="application/problem+json",
            )
        if isinstance(response, BaseException) and hasattr(response, "status"):
            return BaseResponse(
                status=getattr(response, "status"),
                body=normalize_problem_payload(response, request=request, include_trace=self.debug),
                request=request,
                content_type="application/problem+json",
            )

        if isinstance(response, str):
            return BaseResponse(status=200, body=response, request=request)
        if isinstance(response, bytes):
            return BaseResponse(status=200, body=response, request=request)
        if isinstance(response, dict):
            return BaseResponse(
                status=200,
                body=BaseResponse(body=response, request=request).make_body(),
                request=request,
                content_type='application/json; charset=utf-8',
            )
        if isinstance(response, list):
            return BaseResponse(
                status=200,
                body=BaseResponse(body=response, request=request).make_body(),
                request=request,
                content_type='application/json; charset=utf-8',
            )
        if isinstance(response, CoreBaseResponse):
            if response.redirect:
                return BaseResponse.redirect(response.redirect, status=response.status)
            headers = [(k, v) for k, v in (response.headers or {}).items()]
            return BaseResponse(
                status=response.status,
                body=response.body,
                headers=headers,
                request=request,
                content_type=response.content_type,
            )

        # Legacy path: keep transport-native serialization behavior.
        if isinstance(response, tuple):
            kwargs = {}
            status = 200
            if len(response) >= 1:
                if isinstance(response[0], dict):
                    kwargs["body"] = BaseResponse(body=response[0], request=request).make_body()
                    kwargs["content_type"] = 'application/json; charset=utf-8'
                elif isinstance(response[0], list):
                    kwargs["body"] = BaseResponse(body=response[0], request=request).make_body()
                    kwargs["content_type"] = 'application/json; charset=utf-8'
                else:
                    kwargs["body"] = response[0]
            if len(response) >= 2:
                status = response[1]
            if len(response) >= 3:
                kwargs["headers"] = response[2]
            return BaseResponse(status=status, request=request, **kwargs)
        return BaseResponse(status=200, body=response, request=request)

    async def handler(self, request):
        """
        Обработчик сервера
        :param request: Запрос к серверу
        :return:
        """
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
        dictionary = {}
        try:
            pre_route_resp = self._pre_route_checks(request, evnetStorage)
            if pre_route_resp is not None:
                return await self._make_response(pre_route_resp)

            dictionary = self._resolve_route(request)

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
                return await self._make_response(BaseResponse.redirect(request.route['redirect']))
            else:
                try:
                    guard_response = await self._run_guards(request)
                    if guard_response is not None:
                        return await self._make_response(self._convert_response(guard_response, request=request))
                    await self._run_security(request)
                    handler_response = await self._call_route_handler(request, dictionary)
                    response = self._convert_response(handler_response, request=request)
                    return await self._make_response(response)
                except ApplicationException as ae:
                    self.logger.exception("ASGI application exception")
                    ae = ApplicationException(status=ae.status, reason=ae.reason, body=ae.body, traceback=traceback.format_tb(ae.__traceback__))
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
                    if self._has_exception_mapping(ae, request):
                        return await self.send_error(ae, request)
                    ae = AttributeErrorException(status=500, reason="KeyError[%s]" % ae, body=None, traceback=traceback.format_tb(ae.__traceback__))
                    return await self.send_error(ae, request)
                except Exception as ae:
                    self.logger.exception("ASGI handler unexpected exception")
                    if self._has_exception_mapping(ae, request):
                        return await self.send_error(ae, request)
                    ae = ApplicationException(status=500, reason=ae, body=None, traceback=traceback.format_tb(ae.__traceback__))
                    return await self.send_error(ae, request)
        if self._has_matching_path(request.path):
            return await self._make_response(BaseResponse(status=404, body={}, request=request))
        return await self.send_error(NotFoundException(status=404, reason="Not Found"), request)

    def _has_matching_path(self, path: str) -> bool:
        for _, instance in itinerary.instance_list():
            route_node, _ = instance.match_with_params(path)
            if route_node is not None:
                return True
        return False

    async def _make_response(self, response):
        """
        Единая отправка ответа в транспорт.
        :param response: Ответ в формате BaseResponse
        :return:
        """
        return await self.__transport.make_response(response)

    def _pre_route_checks(self, request, evnetStorage: EventsStorageInterface):
        """
        Быстрые проверки до маршрутизации.
        :param request: Запрос
        :param evnetStorage: Контейнер событий
        :return: Подготовленный ответ или None
        """
        if request.type == 'lifespan' or request.type is None:
            return BaseResponse(status=200, body=None, request=request)

        cors_response = self._cors_preflight_response(request)
        if cors_response is not None:
            return self._to_protocol_response(cors_response, request=request)

        before_request = evnetStorage.get('before_request')
        if before_request:
            for handler in before_request:
                resp = handler(request)
                if resp:
                    if isinstance(resp, str):
                        return BaseResponse(status=200, body=resp, request=request)
                    return resp
        return None

    def _matching_path_instances(self, path: str):
        matched = []
        for _, instance in itinerary.instance_list():
            route_node, _ = instance.match_with_params(path)
            if route_node is not None:
                matched.append(instance)
        return matched

    def _cors_preflight_response(self, request):
        if (request.method or "").upper() != "OPTIONS":
            return None
        for instance in self._matching_path_instances(request.path):
            for middleware in getattr(instance, "get_middlewares", lambda: [])():
                if getattr(middleware, "is_cors_middleware", False):
                    return middleware.preflight_response(request)
        return None

    def _resolve_route(self, request):
        """
        Разрешение маршрута по кэшу/реестру.
        :param request: Запрос
        :return: Параметры найденного маршрута.
        """
        route_key = (
            request.path,
            request.method.lower() if request.method else "",
            (request.content_type or "").lower(),
        )
        dictionary = {}
        cached_route = self._route_cache.get(route_key)
        if cached_route is not None:
            cached_instance, cached_call, dictionary = cached_route
            if cached_call:
                request.route = cached_call
                request.itinerary = cached_instance
            return dictionary
        if request.route is None:
            for _, instance in itinerary.instance_list():
                call, dictionary = instance.get_current_route(request)
                if call:
                    request.route = call
                    request.itinerary = instance
                    self._route_cache[route_key] = (instance, call, dictionary)
                    break
            if request.route is None:
                self._route_cache[route_key] = (None, None, {})
        if request.route and 'instance' in request.route.keys():
            for func in request.route['instance'].get_event('before_request'):
                func(request)
        return dictionary

    async def _maybe_await(self, value):
        if inspect.isawaitable(value):
            return await value
        return value

    def _header_lookup(self, headers, name):
        wanted = name.replace("_", "-").lower()
        for key, value in (headers or {}).items():
            if key.replace("_", "-").lower() == wanted:
                return value
        return None

    def _coerce_value(self, annotation, value):
        if annotation is inspect._empty or value is None:
            return value
        try:
            if annotation in (str, int, float, bool):
                return annotation(value)
        except Exception as exc:
            raise ApplicationException(status=422, reason=f"Invalid value for {annotation}", body=str(exc))
        return value

    def _coerce_body(self, annotation, payload):
        if annotation is inspect._empty:
            return payload
        if annotation in (dict, list, str, int, float, bool):
            return payload
        try:
            if hasattr(annotation, "model_validate"):
                return annotation.model_validate(payload)
            if hasattr(annotation, "parse_obj"):
                return annotation.parse_obj(payload)
            if is_dataclass(annotation):
                return annotation(**(payload or {}))
            if inspect.isclass(annotation) and isinstance(payload, dict):
                return annotation(**payload)
        except Exception as exc:
            raise ApplicationException(status=422, reason="Request body validation failed", body=str(exc))
        return payload

    def _resolve_dependency(self, annotation):
        if annotation is inspect._empty:
            return None
        try:
            return Dependency.resolve(annotation)
        except Exception:
            return None

    def _build_handler_kwargs(self, handler, request, dictionary):
        signature = inspect.signature(handler)
        kwargs = {}
        for name, param in signature.parameters.items():
            if name == "self":
                continue
            if name == "request":
                kwargs[name] = request
                continue
            if name in dictionary:
                kwargs[name] = self._coerce_value(param.annotation, dictionary[name])
                continue

            dependency = self._resolve_dependency(param.annotation)
            if dependency is not None:
                kwargs[name] = dependency
                continue

            if name == "body":
                kwargs[name] = self._coerce_body(param.annotation, getattr(request, "json", None))
                continue

            query = getattr(request, "query", {}) or {}
            if name in query:
                kwargs[name] = self._coerce_value(param.annotation, query[name])
                continue

            header_value = self._header_lookup(getattr(request, "headers", {}) or {}, name)
            if header_value is not None:
                kwargs[name] = self._coerce_value(param.annotation, header_value)
                continue

            cookies = getattr(request, "cookies", {}) or {}
            if name in cookies:
                kwargs[name] = self._coerce_value(param.annotation, cookies[name])
                continue

            if param.default is inspect._empty:
                raise ApplicationException(status=422, reason=f"Missing required handler argument `{name}`")
        return kwargs

    async def _run_guards(self, request):
        if not getattr(request, "itinerary", None) or not hasattr(request.itinerary, "get_guards"):
            return None
        for guard in request.itinerary.get_guards(request):
            response = await self._maybe_await(guard(request))
            if response is not None:
                return response
        return None

    def _has_exception_mapping(self, error, request):
        current_itinerary = getattr(request, "itinerary", None)
        finder = getattr(current_itinerary, "_find_exception_error_mapping", None)
        if finder is None:
            return False
        status, handler = finder(error)
        return status is not None or handler is not None

    def _prepare_error(self, err, request=None):
        current_itinerary = getattr(request, "itinerary", None)
        if current_itinerary is None:
            return err, None
        call = current_itinerary.get_current_error_handler(err)
        if call and call.get("handler"):
            return err, call
        return err, None

    async def _run_security(self, request):
        is_auth_disabled = getattr(getattr(request, "itinerary", None), "is_auth_disabled", None)
        if is_auth_disabled and is_auth_disabled(request.route):
            return
        handler = request.route["handler"]
        for security in getattr(handler, "security", []) or []:
            if not hasattr(security, "authenticate_header"):
                continue
            result = security.authenticate_header(self._header_lookup(request.headers, "Authorization"))
            if result is None:
                raise ApplicationException(status=401, reason="Unauthorized")
            request.actor = result.get("user")

    async def _call_route_handler(self, request, dictionary):
        middlewares = []
        if getattr(request, "itinerary", None) and hasattr(request.itinerary, "get_middlewares"):
            middlewares = request.itinerary.get_middlewares()

        async def call_next(req):
            return await self._call_handler(req, dictionary)

        next_call = call_next
        for middleware in reversed(middlewares):
            current_next = next_call

            async def wrapped(req, middleware=middleware, current_next=current_next):
                if getattr(middleware, "is_cors_middleware", False):
                    response = await current_next(req)
                    return middleware.apply(response, req)
                return await self._maybe_await(middleware(req, current_next))

            next_call = wrapped
        return await next_call(request)

    async def _call_handler(self, request, dictionary):
        """
        Вызов бизнес-обработчика маршрута.
        :param request: Запрос
        :param dictionary: Параметры маршрута
        :return: Результат обработчика
        """
        handler = request.route['handler']
        kwargs = self._build_handler_kwargs(handler, request, dictionary)
        if hasattr(handler, 'controller'):
            handler_controller = self.__get_controller_instance(handler)
            if iscoroutinefunction(handler):
                return await handler(handler_controller, **kwargs)
            return handler(handler_controller, **kwargs)

        if iscoroutinefunction(handler):
            return await handler(**kwargs)
        return handler(**kwargs)

    def _convert_response(self, response, request):
        """
        Нормализация ответа в протокольный формат.
        :param response: Результат бизнес-обработчика
        :param request: Запрос
        :return: BaseResponse
        """
        response = self._to_protocol_response(response, request=request)
        if hasattr(request.itinerary, 'modify_response'):
            response = request.itinerary.modify_response(response)
        return response

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
        err, mapped_call = self._prepare_error(err, request=request)
        payload = normalize_problem_payload(err, request=request, include_trace=self.debug)
        status = payload.get("status", 500)
        title = payload.get("title")
        self.logger.error("ASGI error status=%s reason=%s", status, title)

        if self.debug:
            trace = payload.get("trace")
            self.logger.debug("%s", "\n".join(trace) if isinstance(trace, list) else trace)

        response: Response | BaseResponse
        if issubclass(self.__error_handler, Exception):
            err_response = self.__error_handler().handler(
                status=status,
                reason=title,
                body=payload,
                trace=payload.get("trace"),
                request=request,
            )
            if isinstance(err_response, BaseResponse):
                response = err_response
            elif isinstance(err_response, dict):
                response = Response(
                    status=status,
                    body=err_response,
                    headers=[("Content-Type", "application/problem+json")],
                    request=request,
                    content_type='application/problem+json',
                )
            else:
                response = Response(
                    status=status,
                    body=payload,
                    headers=[("Content-Type", "application/problem+json")],
                    request=request,
                    content_type='application/problem+json',
                )
        else:
            response = Response(
                status=status,
                body=payload,
                headers=[("Content-Type", "application/problem+json")],
                request=request,
                content_type='application/problem+json',
            )
        # traceback.print_exc(file=sys.stdout)
        # call = routes.get_current_error_handler(resp)

        if mapped_call:
            response.body = mapped_call['handler'](response, request)
        else:
            for _, instance in itinerary.instance_list():
                call = instance.get_current_error_handler(response)
                if call:
                    response.body = call['handler'](response, request)
                    break

        return await self.__transport.make_response(response)
