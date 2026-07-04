import hashlib
from ..asgi.routers import routes
import os
import muscles.core


class Asset:

    _installed = {}
    _instances = {}
    _initialized = False

    def __call__(self, *args, **kwargs):
        """
        Данная реализация не учитывает возможное изменение передаваемых
        аргументов в `__init__`

        :param args:
        :param kwargs:
        :return:
        """
        return self

    def __init__(self):
        if self.__class__._initialized:
            return
        path = os.path.dirname(os.path.abspath(muscles.core.__file__))
        routes.add_static('/'.join([path, 'assets']), prefix='/mus', full_path=True)
        self.__class__._initialized = True

    def add(self, tag=None, file=None, body=None, id=None, dependency=None):
        hash = hashlib.sha256()
        if id is not None:
            pass
        elif id is None and file is not None:
            hash.update(file.encode('utf8'))
            id = hash.hexdigest()
        elif id is None and body is not None:
            hash.update(body.encode('utf8'))
            id = hash.hexdigest()

        if tag not in self._installed:
            self._installed[tag] = {}

        if id not in self._installed[tag]:
            self._installed[tag][id] = {
                'id': id,
                'tag': tag,
                'file': file,
                'body': body,
                'installed': False,
            }

    def compile(self, tag=None):
        if tag is None:
            raise ValueError('Tag not set for compile options')
        if tag == 'js':
            return self.js_compile()
        elif tag == 'style':
            return self.style_compile()

    def js_compile(self):
        _list = []
        if 'js' in self._installed:
            for id in self._installed['js']:
                self._installed['js'][id]['installed'] = True
                block = self._installed['js'][id]
                _list.append('<script src="' + block['file'] + '"></script>')
        return "\n".join(_list)

    def style_compile(self):
        _list = []
        if 'style' in self._installed:
            for id in self._installed['style']:
                self._installed['style'][id]['installed'] = True
                block = self._installed['style'][id]
                _list.append('<link href="' + block['file'] + '" rel="stylesheet">')
        return "\n".join(_list)


asset = Asset()
