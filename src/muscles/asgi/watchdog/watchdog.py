import logging
from watchdog.observers import Observer
from watchdog.events import RegexMatchingEventHandler
from watchdog.events import PatternMatchingEventHandler
import importlib
import importlib.util


class PatternMatchingHandler(PatternMatchingEventHandler):
    """Logs all the events captured."""

    def __init__(self, patterns=None, ignore_patterns=None, ignore_directories=False, case_sensitive=False,
                 command=None):
        super().__init__(patterns=patterns,
                         ignore_patterns=ignore_patterns,
                         ignore_directories=ignore_directories,
                         case_sensitive=case_sensitive)
        self._command = command

    def run_command(self):
        if not self._command or self._command == {}:
            return None
        package = '.'.join(str(self._command.get('handler')).split('.')[:-1])
        handler = '.'.join(str(self._command.get('handler')).split('.')[-1:])
        if importlib.util.find_spec(package) is not None:
            package = importlib.import_module(package, package=None)
            if hasattr(package, handler):
                handler = getattr(package, handler)
                command = handler(**self._command.get('config', {}))
                res = command.execute()
                if res:
                    print("Reload uwsgi")
                else:
                    raise Exception("Failed to restart uwsgi")
            else:
                raise Exception('Пакет %s не найден' % str(self._command.get('handler')))
        else:
            raise Exception('Пакет %s не найден' % str(self._command.get('handler')))

    def on_any_event(self, event):
        pass

    def on_moved(self, event):
        self.run_command()

    def on_created(self, event):
        self.run_command()

    def on_deleted(self, event):
        self.run_command()

    def on_modified(self, event):
        self.run_command()


class Watchdog:

    _instances = {}

    def __new__(cls, *args, config=None, **kwargs):
        """
        Конструктор класса

        :param args:
        :param kwargs:
        """
        if config is None:
            config = {}
        if cls not in cls._instances:
            instance = super().__new__(cls, *args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

    def __init__(self, config=None):
        """
        Инициализируем следопыта

        :param config: конфигурация следопыта
        """
        if config is None:
            config = {}
        if not hasattr(self, 'install') or not self.install:
            self.install = True

            logger = logging.getLogger('watchdog.observers.inotify_buffer')
            logger.disabled = True
            logger = logging.getLogger('watchdog.observers')
            logger.disabled = True
            logger = logging.getLogger('watchdog')
            logger.disabled = True
            self.observer = Observer()
            self.listen(config)

    def listen(self, config=None):
        """
        Запускаем слежку за файлами

        :param config: конфигурация слежки
        :return:
        """
        if config is None:
            config = {}
        package = '.'.join(str(config.get('handler')).split('.')[:-1])
        handler = '.'.join(str(config.get('handler')).split('.')[-1:])
        if importlib.util.find_spec(package) is not None:
            print('-----------importlib.import_module>', package)
            package = importlib.import_module(package, package=None)
            print('-----------package, handler>', package, handler)
            if hasattr(package, handler):
                handler = getattr(package, handler)
                handler_config = config.get('config') or {}
                if not isinstance(handler_config, dict):
                    handler_config = {}
                event_handler = handler(**handler_config)
                self.observer.schedule(event_handler, path=str(config.get('path')), recursive=True)
                self.observer.start()
                # self.observer.join()
            else:
                raise Exception('Пакет %s не найден' % str(config.get('handler')))
        else:
            raise Exception('Пакет %s не найден' % str(config.get('handler')))

    def stop(self):
        """
        Останавливаем слежку

        :return:
        """
        self.observer.stop()

    def start(self):
        """
        Запускаем слежку

        :return:
        """
        self.observer.start()
