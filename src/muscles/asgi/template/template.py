import json
from jinja2 import Environment
from jinja2.environment import Template as JinjaTemplate
from jinja2.loaders import FileSystemLoader, PackageLoader, BaseLoader
from jinja2.loaders import FunctionLoader, PrefixLoader
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import internalcode
import typing as t
from functools import wraps
from ..assets import asset


if t.TYPE_CHECKING:
    import typing_extensions as te
    from jinja2.bccache import BytecodeCache
    from jinja2.ext import Extension
    from jinja2.loaders import BaseLoader


class TemplateLoader(BaseLoader):
    """
    Загрузчик, которому передается функция, выполняющая загрузку. функция получает имя шаблона и должна вернуть либо
    строка с источником шаблона, кортеж в виде ``(источник, имя файла, uptodatefunc)`` или `Нет`, если шаблон
    не существует.

    >>> def load_template(name):
    ...     if name == 'index.html':
    ...         return '...'
    ...
    >>> loader = FunctionLoader(load_template)

    `uptodatefunc` — это функция, которая вызывается, если включена автоперезагрузка. и должен вернуть True, если
    шаблон все еще актуален. Для большего подробности смотрите в :meth:`BaseLoader.get_source`, который имеет то
    же самое возвращаемое значение.
    """

    def __init__(
            self,
            config,
            package_paths: list = [],
            encoding: str = "utf-8",
            delimiter: str = "/",
            **kwargs
    ) -> None:
        """
        Конструктор загрузчика jinja template loader

        :param load_config: Конфигурация
        :param package_paths: Пути к шаблонам
        :param encoding: Кодировка
        :param delimiter: Разделитель
        :param kwargs:
        """
        self.load_config = config
        self.mapping = {}
        self.delimiter = delimiter
        self.encoding = encoding
        self.templates = {}

        for key in kwargs:
            if not isinstance(kwargs[key], Template) and isinstance(kwargs[key], object):
                for prop, obj in vars(kwargs[key]).items():
                    if isinstance(obj, Template):
                        self.templates[key] = obj
            elif isinstance(kwargs[key], Template):
                self.templates[key] = kwargs[key]

        for key, obj in self.templates.items():
            if hasattr(obj, 'loader'):
                self.add_loader_to_mappers(getattr(obj, 'loader'), key)

        if self.load_config.items():
            for key, template in dict(self.load_config).items():
                self.mapping[key] = FileSystemLoader(template)

        self.packages = []

        if isinstance(package_paths, list):
            for path in package_paths:
                if self.load_config.items():
                    for module in self.load_config.get('.'.join([path])):
                        package = self.load_config.get('.'.join([path, module, 'package'])).value()
                        self.mapping[package] = PackageLoader(package, self.load_config.get(
                            '.'.join([path, module, 'templates']), 'templates').value())
        elif isinstance(package_paths, dict):
            for item in package_paths:
                if self.load_config.get('.'.join([package_paths[item]])).items():
                    for module in self.load_config.get('.'.join([package_paths[item]])):
                        package = self.load_config.get('.'.join([package_paths[item], module, 'package'])).value()
                        self.mapping[package] = PackageLoader(package, self.load_config.get(
                            '.'.join([package_paths[item], module, 'templates']), 'templates').value())

    def add_loader_to_mappers(self, loader, prefix=None):
        _mappers = {}
        if not hasattr(loader, 'mapping'):
            return

        for item in loader.mapping:
            name = '.'.join([prefix, item]) if prefix is not None else item
            self.mapping[name] = loader.mapping[item]

    def get_path(self, template: str) -> t.Tuple[t.Any, str, str]:
        try:
            prefix, name = template.split(self.delimiter, 1)
            searchpath = self.templates[prefix]
        except (ValueError, KeyError) as e:
            raise TemplateNotFound(template) from e
        return searchpath, name, prefix

    def get_loader(self, template: str) -> t.Tuple[BaseLoader, str]:
        try:
            prefix, name = template.split(self.delimiter, 1)
            loader = self.mapping[prefix]
        except (ValueError, KeyError) as e:
            raise TemplateNotFound(template) from e
        return loader, name

    def get_source(
            self, environment: "Environment", template: str
    ) -> t.Tuple[str, t.Optional[str], t.Optional[t.Callable[[], bool]]]:
        loader, name = self.get_loader(template)
        try:
            return loader.get_source(environment, name)
        except TemplateNotFound as e:
            # re-raise the exception with the correct filename here.
            # (the one that includes the prefix)
            raise TemplateNotFound(template) from e

    @internalcode
    def load(
            self,
            environment: "Environment",
            name: str,
            globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> JinjaTemplate:
        loader, local_name = self.get_loader(name)
        try:
            return loader.load(environment, local_name, globals)
        except TemplateNotFound as e:
            # re-raise the exception with the correct filename here.
            # (the one that includes the prefix)
            raise TemplateNotFound(name) from e

    def list_templates(self) -> t.List[str]:
        result = []
        for prefix, loader in self.mapping.items():
            for template in loader.list_templates():
                result.append(prefix + self.delimiter + template)
        return result


class Filters:
    """
    Фильтры шаблона
    """

    @staticmethod
    def upperstring(value):
        """
        Фильтр строки: Все символы прописные

        :param value: входящая строка
        :return:
        """
        return value.upper()

    @staticmethod
    def to_json(value):
        """
        Фильтр строки: Словарь в json

        :param value: входящая строка
        :return:
        """
        return json.dumps(value)


class Template:
    """
    `block_start_string`
        Строка, обозначающая начало блока. По умолчанию ``'{%'``.

    `блок_конец_строки`
        Строка, обозначающая конец блока. По умолчанию ``'%}'``.

    `variable_start_string`
        Строка, обозначающая начало оператора печати.
        По умолчанию ``'{{'``.

    `variable_end_string`
        Строка, обозначающая конец оператора печати. По умолчанию
        ``'}}'``.

    `comment_start_string`
        Строка, обозначающая начало комментария. По умолчанию ``'{#'``.

    `comment_end_string`
        Строка, обозначающая конец комментария. По умолчанию ``'#}'``.

    `line_statement_prefix`
        Если указано и строка, это будет использоваться в качестве префикса для строки на основе
        заявления. См. также :ref:`line-statements`.

    `line_comment_prefix`
        Если указано и строка, это будет использоваться в качестве префикса для строки на основе
        Комментарии. См. также :ref:`line-statements`.

        .. версия добавлена:: 2.2

    `обрезка_блоков`
        Если установлено значение ``True``, первая новая строка после блока
        удален (блок, а не переменный тег!). По умолчанию «Ложь».

    `lstrip_blocks`
        Если для этого параметра установлено значение «True», начальные пробелы и табуляции удаляются.
        от начала строки до блока. По умолчанию «Ложь».

    `newline_sequence`
        Последовательность, с которой начинается новая строка. Должен быть одним из ``'\r'``,
        ``'\n'`` или ``'\r\n'``. По умолчанию используется ``'\n'``, что является
        полезное значение по умолчанию для систем Linux и OS X, а также для Интернета
        Приложения.

    `keep_trailing_newline`
        Сохраняйте завершающую новую строку при отображении шаблонов.
        По умолчанию установлено «False», что приводит к одиночной новой строке,
        если они есть, их нужно снять с конца шаблона.

        .. версия добавлена:: 2.7

    `расширения`
        Список расширений Jinja для использования. Это могут быть пути импорта
        как строки или классы расширения. Для получения дополнительной информации есть
        посмотрите :ref:`документацию по расширениям <jinja-extensions>`.

    `оптимизировано`
        должен быть включен оптимизатор? По умолчанию установлено значение «Истина».

    `не определено`
        :class:`Undefined` или его подкласс, который используется для представления
        неопределенные значения в шаблоне.

    `завершить`
        Вызываемый объект, который можно использовать для обработки результата переменной
        выражение до его вывода. Например, можно преобразовать
        ``None`` здесь неявно превращается в пустую строку.

    `автоэкранирование`
        Если установлено значение «True», функция автоматического экранирования XML/HTML включается
        дефолт. Дополнительные сведения об автоматическом экранировании см.
        :class:`~markupsafe.Разметка`. Начиная с Jinja 2.4 это также может
        быть вызываемым объектом, которому передается имя шаблона и который должен
        return ``True`` или ``False`` в зависимости от автоэкранирования должен быть
        включено по умолчанию.

        ..версия изменена::2.4
           `autoescape` теперь может быть функцией

    `загрузчик`
        Загрузчик шаблонов для этой среды.

    `кэш_размер`
        Размер кэша. По умолчанию это ``400``, что означает
        что если загружено более 400 шаблонов загрузчик очистит
        из наименее недавно использованного шаблона. Если размер кэша установлен на
        ``0`` шаблоны перекомпилируются все время, если размер кеша
        ``-1`` кэш не будет очищен.

        ..версия изменена::2.8
           Размер кеша был увеличен с 50 до 400.

    `auto_reload`
        Некоторые загрузчики загружают шаблоны из мест, где шаблон
        источники могут измениться (например, файловая система или база данных). Если
        ``auto_reload`` устанавливается в ``True`` (по умолчанию) каждый раз, когда шаблон
        запрошенный загрузчик проверяет, изменился ли исходный код, и если да, то он
        перезагрузит шаблон. Для повышения производительности можно
        отключить это.

    `bytecode_cache`
        Если задан объект кэша байт-кода, этот объект предоставит
        кэш для внутреннего байт-кода Jinja, чтобы шаблоны не
        должны быть проанализированы, если они не были изменены.

        См. :ref:`bytecode-cache` для получения дополнительной информации.

    `включить_асинхронность`
        Если установлено значение true, это включает выполнение асинхронного шаблона, который
        позволяет использовать асинхронные функции и генераторы.
    """

    blocks = {}

    instance = None
    name = None

    def __set_name__(self, owner, name):
        self.name = name
        self.instance = owner

    def __init__(self,
                 templates=None,
                 layouts=None,
                 blocks=None,
                 config=None,
                 block_start_string: str = "{%",
                 block_end_string: str = "%}",
                 variable_start_string: str = "{{",
                 variable_end_string: str = "}}",
                 comment_start_string: str = "{#",
                 comment_end_string: str = "#}",
                 line_statement_prefix: t.Optional[str] = None,
                 line_comment_prefix: t.Optional[str] = None,
                 trim_blocks: bool = False,
                 lstrip_blocks: bool = False,
                 newline_sequence: "te.Literal['\\n', '\\r\\n', '\\r']" = "\n",
                 keep_trailing_newline: bool = False,
                 extensions: t.Sequence[t.Union[str, t.Type["Extension"]]] = (),
                 optimized: bool = True,
                 finalize: t.Optional[t.Callable[..., t.Any]] = None,
                 autoescape: t.Union[bool, t.Callable[[t.Optional[str]], bool]] = False,
                 loader: t.Optional["BaseLoader"] = None,
                 cache_size: int = 400,
                 auto_reload: bool = True,
                 bytecode_cache: t.Optional["BytecodeCache"] = None,
                 enable_async: bool = False,
                 ):

        params = {}
        if layouts is not None or templates is not None:
            loaders = {}
            if layouts is not None:
                loaders['layouts'] = FileSystemLoader(layouts)
            if templates is not None:
                loaders['templates'] = FileSystemLoader(templates)
            if blocks is not None:
                loaders['blocks'] = FileSystemLoader(blocks)
            params['loader'] = PrefixLoader(loaders)
        else:
            params['loader'] = loader

        params['block_start_string'] = block_start_string
        params['block_end_string'] = block_end_string
        params['variable_start_string'] = variable_start_string
        params['variable_end_string'] = variable_end_string
        params['comment_start_string'] = comment_start_string
        params['comment_end_string'] = comment_end_string
        params['line_statement_prefix'] = line_statement_prefix
        params['line_comment_prefix'] = line_comment_prefix
        params['trim_blocks'] = trim_blocks
        params['lstrip_blocks'] = lstrip_blocks
        params['newline_sequence'] = newline_sequence
        params['keep_trailing_newline'] = keep_trailing_newline
        params['extensions'] = extensions
        params['optimized'] = optimized
        params['finalize'] = finalize
        params['autoescape'] = autoescape
        params['cache_size'] = cache_size
        params['auto_reload'] = auto_reload
        params['bytecode_cache'] = bytecode_cache
        params['enable_async'] = enable_async

        self.loader = params['loader']
        self.tpl = Environment(**params)

        self.tpl.filters['upperstring'] = Filters.upperstring
        self.tpl.filters['to_json'] = Filters.to_json

        self.tpl.globals['asset'] = asset

    def render(self, template, **params):
        tmpl = self.tpl.get_template(template)
        return tmpl.render(**params)

    def string(self, string):
        return self.tpl.from_string(string)

    def template(self, template, **params):
        return self.tpl.get_template(template, **params)

    def add_block(self, block, handler=None):
        self.blocks[block] = {
            "block": block,
            'handler': handler,
        }

    def block(self, block):
        def decorator(func):
            self.add_block(block, handler=func)

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def block_config(self, block):
        def decorator(func):
            self.add_block(block, handler=func)

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def landing(self, title: str = '', link: str = '', copyright: str = '', blocks: list = [],
                before_handler=None, handler=None):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                _templates = []
                _blocks = []
                for _block in blocks:
                    key = _block[0] or str(_block)
                    if key not in self.blocks:
                        continue
                    config = _block[1] or {}
                    block = self.blocks[key]

                    if 'key' not in config:
                        config['key'] = key
                    if 'anchor' not in config:
                        config['anchor'] = key
                    if 'title' not in config:
                        config['title'] = str(key).title()

                    _handler = block['handler']
                    del block['handler']

                    block['key'] = config['key']
                    block['title'] = config['title']
                    block['anchor'] = config['anchor']
                    block['request'] = kwargs['request']
                    block['handler'] = handler or _handler
                    block['config'] = config
                    block['render'] = block['handler'](request=block['request'], config=block['config'])

                    _blocks.append(block)

                _kwargs = {}
                _kwargs['title'] = title
                _kwargs['link'] = link
                _kwargs['copyright'] = copyright
                _kwargs['request'] = kwargs['request']
                _kwargs['blocks'] = _blocks
                return func(*args, **_kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper

        return decorator

    def __call__(self, template, **params):
        return self.render(template, **params)
