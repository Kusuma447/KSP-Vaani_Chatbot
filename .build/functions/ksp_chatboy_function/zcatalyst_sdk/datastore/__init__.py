from typing import Union, List
from ..types import Component, ICatalystTable
from ..exceptions import CatalystDatastoreError
from .._http_client import AuthorizedHttpClient
from ._table import Table
from .. import validator
from .._constants import (
    RequestMethod,
    CredentialUser,
    Components
)


class Datastore(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.DATA_STORE

    def get_all_tables(self):
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/table',
            user=CredentialUser.USER
        )
        data: List = resp.response_json.get('data')
        tables: List[Table] = []
        for table in data:
            tables.append(Table(self, table))
        return tables

    def get_table_details(self, table_id: Union[str, int]) -> ICatalystTable:
        validator.is_non_empty_string_or_number(table_id, 'table_id', CatalystDatastoreError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/table/{table_id}',
            user=CredentialUser.USER
        )
        data = resp.response_json.get('data')
        return data

    def table(self, table_id: Union[str, int]):
        validator.is_non_empty_string_or_number(table_id, 'table_id', CatalystDatastoreError)
        try:
            return Table(self, {'table_id': int(table_id)})
        except ValueError:
            return Table(self, {'table_name': str(table_id)})
