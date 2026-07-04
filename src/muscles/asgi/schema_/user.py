from .column import Column
from .field import Json, Numeric, String, UUID4
from .model import Model
import uuid as uuid_gen


class BaseUser(Model):
    _instances = {}

    uuid = Column(UUID4, example='00ae43ec-ed17-4fcd-aebc-76c90a348439')
    name = Column(String, example='Jon')
    token = Column(String, example='00ae43eced174fcdaebc76c90a348439')
    status = Column(Numeric, example=40)
    rules = Column(Json, example="{}")

    def __init__(self, uuid=None, token=None, status=None, name=None, rules=None, **kwargs):
        if uuid is None:
            uuid = uuid_gen.uuid4()
        kwargs['uuid'] = uuid
        kwargs['token'] = token
        kwargs['status'] = status
        kwargs['name'] = name
        kwargs['rules'] = rules
        super().__init__(**kwargs)

    def is_system(self) -> bool:
        return False

    def is_robot(self) -> bool:
        return False

    def is_user(self) -> bool:
        return False

    def is_guest(self) -> bool:
        return False


class User(BaseUser):

    def is_user(self) -> bool:
        return True


class SystemUser(BaseUser):

    def is_system(self) -> bool:
        return True


class RobotUser(BaseUser):

    def is_robot(self) -> bool:
        return True


class GuestUser(BaseUser):

    def is_guest(self) -> bool:
        return True
