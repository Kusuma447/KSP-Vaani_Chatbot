from typing import Dict, Union
from .types import Component
from .exceptions import CatalystCircuitError
from . import validator
from ._http_client import AuthorizedHttpClient
from ._constants import RequestMethod, CredentialUser, Components


class Circuit(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.CIRCUIT

    def execute(
        self,
        circuit_id: Union[int, str],
        name: str,
        inputs: Dict[str, str] = None
    ):
        validator.is_non_empty_string_or_number(circuit_id, 'circuit_id', CatalystCircuitError)
        validator.is_non_empty_string(name, 'execution_name', CatalystCircuitError)
        req_json = {
            'name': name,
            'input': inputs or {}
        }
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=f'/circuit/{circuit_id}/execute',
            json=req_json,
            user=CredentialUser.ADMIN
        )
        return resp.response_json.get('data')

    def status(
        self,
        circuit_id: Union[int, str],
        exec_id: Union[int, str]
    ):
        validator.is_non_empty_string_or_number(circuit_id, 'circuit_id', CatalystCircuitError)
        validator.is_non_empty_string_or_number(exec_id, 'execution_id', CatalystCircuitError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/circuit/{circuit_id}/execution/{exec_id}',
            user=CredentialUser.ADMIN
        )
        return resp.response_json.get('data')

    def abort(
        self,
        circuit_id: Union[int, str],
        exec_id: Union[int, str]
    ):
        validator.is_non_empty_string_or_number(circuit_id, 'circuit_id', CatalystCircuitError)
        validator.is_non_empty_string_or_number(exec_id, 'execution_id', CatalystCircuitError)
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=f'/circuit/{circuit_id}/execution/{exec_id}',
            user=CredentialUser.ADMIN
        )
        return resp.response_json.get('data')
