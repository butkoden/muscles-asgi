from .schema import Schema
from typing import Any


class BaseModel(Schema):
    __prefix__ = ""
    __collection__ = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "columns"):
            self.columns = []

    @property
    def has_errors(self) -> bool:
        """ Вернет True если в полях присутствуют ошибки """
        errors = []
        for child in self.columns:
            if self.columns[child].has_error:
                errors.append({self.columns[child].column_name: self.columns[child].error})
        return True if len(errors) > 0 else False

    def errors(self) -> dict:
        """ Возвращает ошибки в полях """
        errors = {}
        for child in self.columns:
            if self.columns[child].has_error:
                errors[self.columns[child].column_name] = self.columns[child].error
        return errors

    def dump(self) -> dict:
        # results = super().dump()
        results = {}
        results_ = {}
        for child in self.columns:
            if callable(self.columns[child]):
                self.columns[child] = self.columns[child]()
            results_.update(self.columns[child].dump())
        results.update({
            self.__class__.__name__: {
                "type": "object",
                "properties": results_
            }
        })
        return results

    def to_json(self) -> dict:
        results = {}
        results_ = {}
        for child in self.columns:
            if callable(self.columns[child]):
                self.columns[child] = self.columns[child]()
            results_.update(self.columns[child].to_json())
        results.update(results_)
        return results


class Model(BaseModel):

    __metaclass__ = BaseModel
    __prefix__ = ""
    __collection__ = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection = "{prefix}{collection}".format(
            collection=self.__collection__ if self.__collection__ else self.__class__.__name__.lower(),
            prefix="%s_" % self.__prefix__ if self.__prefix__ else ''
        )
        if len(kwargs) > 0 and hasattr(self, 'columns'):
            for column in self.columns:
                self.columns[column].value = kwargs.get(column) or self.columns[column].default or None
                self.columns[column].validate()
                # print(column, kwargs.get(column), self.columns[column])

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__()
        ms = ModelStorage()
        ms[cls.__name__] = cls


class ModelStorage:

    _instances = {}

    def __call__(self, *args, name: str | None = None, **kwargs):
        """
        Данная реализация не учитывает возможное изменение передаваемых
        аргументов в `__init__`.

        :param name:
        :param args:
        :param kwargs:
        :return:
        """
        key = '-'.join([str(type(self)), str(name)])
        if key not in self._instances:
            self._instances[key] = self
        return self._instances[key]

    def __init__(self, *args, **kwargs) -> None:
        """
        Конструктор класса для работы с хранилизами
        """
        if not hasattr(self, '_models'):
            self._models = {}

    @property
    def models(self) -> dict:
        """
        Вернет текущее хранилище
        """
        return self._models

    def __setitem__(self, key, value):
        """
        Провайдер для установки класса объекта в хранилище

        :param key: Ключ
        :param value: Класс
        :return:
        """
        self._models[key] = value

    def __getitem__(self, key) -> Model:
        """
        Провайдер который достает и конструирует объект из класса в хранилище

        :param key: Ключ
        :return: Model
        """
        return self._models[key]

    def __contains__(self, key):
        """
        Провайдер для проверки наличия класса в хранилище

        :param key:
        :return:
        """
        return key in self._models

    def add(self, key, value):
        """
        Заносит класс объекта в хранилище с дополнительными проверками.
        Рекомендуется к использованию вместо обращения os[key] = class

        :param key: Ключ
        :param value: Класс
        :param args: Аргументы для передачи конструктору
        :param instance: Клас для проверки принадлежности
        :param kwargs: словарь для передачи конструктору объекта
        :return:
        """
        if key in self._models:
            raise Exception('ObjectStorage.add(%s, %s) -> Key already added' % (key, value))
        self._models[key] = value

    def get(self, key) -> Model | None:
        """
        Вернет класс объекта из хранилища.
        Рекомендуется к использованию вместо обращения os[key]

        :param key:
        :return: Model
        """
        return self._models.get(key, None)
