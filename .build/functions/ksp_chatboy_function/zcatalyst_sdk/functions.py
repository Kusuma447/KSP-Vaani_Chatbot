from typing import Dict, Union
from .types import Component
from .exceptions import CatalystFunctionError
from . import validator
from ._http_client import AuthorizedHttpClient
from ._constants import RequestMethod, CredentialUser, Components


class Functions(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.FUNCTION

    def execute(self, func_id: Union[str, int], args: Dict = None):
        validator.is_non_empty_string_or_number(func_id, 'func_id', CatalystFunctionError)
        if args is not None and not isinstance(args, dict):
            raise CatalystFunctionError(
                'INVALID_ARGUMENTS',
                'Function Args must be a instance of dict'
            )

        resp = self._requester.request(
            method=RequestMethod.POST,
            path=f'/function/{func_id}/execute',
            json=args,
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return str(resp_json.get('data') or resp_json.get('output'))
