from .schema import Schema
from .exception import ValidationColumnException
from typing import Any


class BaseColumn(Schema):
    column_name: str
    field_type: Any
    value: Any

    def __set_name__(self, owner, name):
        self.column_name = name
        if not hasattr(owner, 'columns'):
            setattr(owner, 'columns', dict())
        owner.columns[name] = self

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error = None
        if len(args) > 1:
            self.column_name = args[0]
            self.field_type = args[1] if not callable(args[1]) else args[1]()
        elif len(args) == 1:
            self.field_type = args[0] if not callable(args[0]) else args[0]()

    def __set__(self, instance, value):
        try:
            self.value = value
        except ValidationColumnException as vce:
            self.error = vce.message

    def __get__(self, instance, owner):
        return self.value

    @property
    def has_error(self):
        return True if self.error is not None else False

    def dump(self) -> dict:
        return {
            self.column_name: self.field_type.dump()
        }

    def to_json(self) -> dict:
        return {
            self.column_name: self.field_type.getstate(self.value)
        }


class Column(BaseColumn):

    def __init__(self, *args, index=False, unique=False, primary_key=False, nullable=True, default=None,
                 required=False, title=None, description=None, example=None, min_length=None, max_length=None,
                 **kwargs):

        kwargs['index'] = index
        kwargs['unique'] = unique
        kwargs['primary_key'] = primary_key
        kwargs['nullable'] = nullable
        kwargs['default'] = default
        kwargs['required'] = required
        kwargs['title'] = title
        kwargs['description'] = description
        kwargs['example'] = example
        kwargs['min_length'] = min_length
        kwargs['max_length'] = max_length
        super().__init__(*args, **kwargs)
        if len(args) > 1:
            self.column_name = args[0]
            self.field_type = args[1] if not callable(args[1]) else args[1]()
        elif len(args) == 1:
            self.field_type = args[0] if not callable(args[0]) else args[0]()

        self.index = index
        self.unique = unique
        self.default = default
        self.required = required
        self.title = title
        self.description = description
        self.nullable = nullable
        self.value = self.default
        self.primary_key = primary_key
        self.example = example
        self.min_length = min_length
        self.max_length = max_length
        self.error = None

    def validate(self):
        try:
            if not self.nullable and self.value is None:
                raise ValidationColumnException(self.column_name,
                                                'The value %s does not match the field format.' % str(self.value))
            if self.required and self.value is not None:
                raise ValidationColumnException(self.column_name, 'Field must have a value')
            if self.value is not None:
                self.field_type.validate(self.value, field=self.column_name)
            if self.value is not None and self.min_length is not None and len(str(self.value)) < self.min_length:
                raise ValidationColumnException(self.column_name, 'The length of the value %s is less than %s' % (
                                                    str(self.value), str(self.min_length)
                                                ))
            if self.value is not None and self.max_length is not None and len(str(self.value)) > self.max_length:
                raise ValidationColumnException(self.column_name,
                                                'The length of the value %s is greater than %s' % (
                                                    str(self.value), str(self.max_length)
                                                ))
        except ValidationColumnException as vce:
            self.error = vce.message

    def __set__(self, instance, value):
        self.value = value
        self.validate()

    def __get__(self, instance, owner):
        if not self.has_error:
            return self.value or self.default
        else:
            return None

    @property
    def has_error(self):
        return True if self.error is not None else False

    def dump(self) -> dict:
        results = super().dump()
        results[self.column_name].update({
            "index": self.index,
            "unique": self.unique,
            "default": self.default,
            "required": self.required,
            "title": self.title,
            "description": self.description,
            "nullable": self.nullable,
            "value": self.value or self.default,
            "primary_key": self.primary_key,
            "example": self.example,
            "error": self.error,
        })
        return results
