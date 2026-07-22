from typing import Any, Dict, List, Literal, TypedDict, Union
from ..exceptions import CatalystDatastoreError
from ..types import (
    ICatalystColumn,
    ICatalystRow,
    ICatalystRows,
    ParsableComponent
)
from .._constants import (
    RequestMethod,
    CredentialUser,
    Components
)
from .. import validator
from .._http_client import AuthorizedHttpClient
from ._bulk_job import BulkRead, BulkWrite

ICatalystRowInput = TypedDict('ICatalystRowInput', {'ROWID': str})
BulkOperation = Literal['read', 'write']


class Table(ParsableComponent):
    def __init__(self, datastore_instance, table_details: Dict):
        validator.is_non_empty_dict(table_details, 'table_details', CatalystDatastoreError)
        self._requester: AuthorizedHttpClient = datastore_instance._requester
        self._identifier = table_details.get('table_id') or table_details.get('table_name')
        self._table_details = table_details

    def __repr__(self) -> str:
        return str(self._table_details)

    def get_component_name(self):
        return Components.DATA_STORE

    def get_all_columns(self) -> List[ICatalystColumn]:
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/table/{self._identifier}/column',
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def get_column_details(self, col_id: Union[str, int]) -> ICatalystColumn:
        validator.is_non_empty_string_or_number(col_id, 'column_id', CatalystDatastoreError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/table/{self._identifier}/column/{col_id}',
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def insert_row(self, row: Dict[str, Any]) -> ICatalystRow:
        validator.is_non_empty_dict(row, 'row', CatalystDatastoreError)
        resp = self.insert_rows([row])
        return resp[0]

    def insert_rows(self, row_list: List[Dict]) -> List[ICatalystRow]:
        validator.is_non_empty_list(row_list, 'row_list', CatalystDatastoreError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=f'/table/{self._identifier}/row',
            json=row_list,
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def get_paged_rows(
        self,
        next_token: str = None,
        max_rows: int = None
    ) -> ICatalystRows:
        req_params = {
            'next_token': next_token,
            'max_rows': max_rows
        }

        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/table/{self._identifier}/row',
            params=req_params,
            user=CredentialUser.USER
        )

        resp_json = resp.response_json
        return resp_json

    def get_iterable_rows(self):
        next_token: str = None
        while True:
            rows_output = self.get_paged_rows(next_token)
            yield from rows_output.get('data')
            next_token = rows_output.get('next_token')
            if next_token is None:
                break

    def get_row(self, row_id: Union[str, int]) -> ICatalystRow:
        validator.is_non_empty_string_or_number(row_id, 'row_id', CatalystDatastoreError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/table/{self._identifier}/row/{row_id}',
            user=CredentialUser.USER
        )

        resp_json = resp.response_json
        return resp_json.get('data')

    def delete_row(self, row_id: Union[str, int]) -> bool:
        validator.is_non_empty_string_or_number(row_id, 'row_id', CatalystDatastoreError)
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=f'/table/{self._identifier}/row/{row_id}',
            user=CredentialUser.USER
        )

        resp_json = resp.response_json
        return bool(resp_json.get('data'))

    def delete_rows(self, ids: List[Union[str, int]]) -> bool:
        validator.is_non_empty_list(ids, 'row_ids', CatalystDatastoreError)

        ids = list(map(str, ids))
        req_param = {
            'ids': ','.join(ids)
        }

        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=f'/table/{self._identifier}/row',
            params=req_param,
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return bool(resp_json.get('data'))

    def update_row(self, row: ICatalystRowInput) -> ICatalystRow:
        validator.is_non_empty_dict(row, 'row', CatalystDatastoreError)
        resp = self.update_rows([row])
        return resp[0] if len(resp) > 0 else resp

    def update_rows(self, row_list: List[ICatalystRowInput]) -> List[ICatalystRow]:
        validator.is_non_empty_list(row_list, 'row_list', CatalystDatastoreError)
        resp = self._requester.request(
            method=RequestMethod.PATCH,
            path=f'/table/{self._identifier}/row',
            json=row_list,
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def bulk_read(self):
        return BulkRead(self)

    def bulk_write(self):
        return BulkWrite(self)

    def to_dict(self):
        return self._table_details

    def to_string(self):
        return repr(self)
