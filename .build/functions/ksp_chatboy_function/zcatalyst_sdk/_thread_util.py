import threading
from typing import Any


class ZCThreadUtil:
    def __init__(self) -> None:
        try:
            self.__zclocal = getattr(threading.current_thread(), '__zc_local')
        except AttributeError:
            setattr(threading.current_thread(), '__zc_local', {})
            self.__zclocal = getattr(threading.current_thread(), '__zc_local')

    def get_value(self, key: str):
        return self.__zclocal.get(key)

    def put_value(self, key: str, val: Any):
        self.__zclocal[key] = val


def get_attr(obj: dict, key: str):
    if obj.get(key):
        return obj.get(key)
    fallback_obj = dict((k.lower(), v) for k, v in obj.items())
    return fallback_obj.get(key.lower())
