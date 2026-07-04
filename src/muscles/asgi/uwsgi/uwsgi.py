

import importlib
from typing import Any, cast


class UwsgiReload:
    """
    Команда перезагрузки UWSGI
    """

    def __init__(self, config={}):
        self.config = config

    def execute(self):
        print('Reloaded UWSGI')
        uwsgi = cast(Any, importlib.import_module("uwsgi"))
        return uwsgi.reload()
