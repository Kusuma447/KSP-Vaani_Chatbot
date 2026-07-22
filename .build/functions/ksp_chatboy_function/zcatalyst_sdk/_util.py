from .exceptions import CatalystAppError
from ._thread_util import ZCThreadUtil


def parse_headers_from_request(request):
    try:
        if hasattr(request, 'headers'):
            thread_obj = ZCThreadUtil()
            thread_obj.put_value("catalyst_headers", dict(request.headers))
    except Exception as err:
        raise CatalystAppError(
            "Invalid req_obj",
            "Kindly ensure whether the request object is valid"
        ) from err
