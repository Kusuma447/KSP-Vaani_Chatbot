from typing import List
from ..validator import (
    is_non_empty_dict,
    is_non_empty_string_or_number,
    is_non_empty_tuple
)
from ..exceptions import CatalystNoSqlError
from .transfom import NoSqlResponse
from ..types.nosql import (
    NoSqlDeleteItemReq,
    NoSqlFetchItemReq,
    NoSqlInsertItemReq,
    NoSqlItem,
    NoSqlQueryItemReq,
    NoSqlUpdateItemReq
)
from ..types import Component
from .._http_client import AuthorizedHttpClient
from .._constants import RequestMethod, CredentialUser, Components

class TableItem(Component):
    """This class used to perform NoSQL table operations.

    Args:
        Component (ABC): Class used to retrieve the component's name.
    """
    def __init__(self, nosql_instance, table) -> None:
        self._requester: AuthorizedHttpClient = nosql_instance._requester
        if not is_non_empty_string_or_number(table, 'table_identifier'):
            table = table['id']
        self.base_path = f'/nosqltable/{table}'

    def get_component_name(self):
        return Components.NOSQL

    def insert_items(self, *input_data: NoSqlInsertItemReq) -> List[NoSqlItem]:
        """Insert items to the table.

        Args:
            input_data (List[NoSqlInsertItemReq]): List of items to be inserted in to table.

        Returns:
            NoSqlResponse: Returns the response instance.
        """
        is_non_empty_tuple(input_data, 'input_data', CatalystNoSqlError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=self.base_path + '/item',
            json=input_data,
            user=CredentialUser.ADMIN
        )
        res = resp.response_json.get('data')
        res['operation'] = 'create'
        return NoSqlResponse(res)

    def update_items(self, *input_data: NoSqlUpdateItemReq) -> NoSqlResponse:
        """Update the items in the table.

        Args:
            input_data (List[NoSqlUpdateItemReq]):
                List of items to be updated into NoSQL table.

        Returns:
            NoSqlResponse: Returns the response instance.
        """
        is_non_empty_tuple(input_data, 'input_data', CatalystNoSqlError)
        resp = self._requester.request(
            method=RequestMethod.PUT,
            path=self.base_path + '/item',
            json=input_data,
            user=CredentialUser.ADMIN
        )
        res = resp.response_json.get('data')
        res['operation'] = 'update'
        return NoSqlResponse(res)

    def delete_items(self, *input_data: NoSqlDeleteItemReq) -> NoSqlResponse:
        """Delete the items in the table.

        Args:
            input_data (List[NoSqlDeleteItemReq]): Values to be deleted from the NoSQL table.

        Returns:
            NoSqlResponse: Returns the response instance.
        """
        is_non_empty_tuple(input_data, 'input_data', CatalystNoSqlError)
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=self.base_path + '/item',
            json=input_data,
            user=CredentialUser.ADMIN
        )
        res = resp.response_json.get('data')
        res['operation'] = 'delete'
        return NoSqlResponse(res)

    def fetch_item(self, input_data: NoSqlFetchItemReq) -> NoSqlResponse:
        """Fetch the item in the NoSQL table.

        Args:
            input_data (NoSqlFetchItemReq): Values used to fetch items from the table.

        Returns:
            NoSqlResponse: Returns the response instance.
        """
        is_non_empty_dict(input_data, 'input_data', CatalystNoSqlError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=self.base_path + '/item/fetch',
            json=input_data,
            user=CredentialUser.ADMIN
        )
        res = resp.response_json.get('data')
        res['operation'] = 'get'
        return NoSqlResponse(res)

    def query_table(self, input_data: NoSqlQueryItemReq) -> NoSqlResponse:
        """Query the items from the table.
        Args:
            input_data (NoSqlQueryItemReq): Value used to fetch items from the table.

        Returns:
            NoSqlResponse: Returns the response instance.
        """
        is_non_empty_dict(input_data, 'input_data', CatalystNoSqlError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=self.base_path + '/item/query',
            json=input_data,
            user=CredentialUser.ADMIN
        )
        res = resp.response_json.get('data')
        res['operation'] = 'get'
        return NoSqlResponse(res)

    def query_index(self, index_id, input_data: NoSqlQueryItemReq) ->  NoSqlResponse:
        """Query the items from the table index.

        Args:
            index_id (int): Id of the index to used fetch the items from the given index.
            input_data (NoSqlQueryItemReq): Value use to fetch items.

        Returns:
            NoSqlResponse: Returns the response instance.
        """
        is_non_empty_dict(input_data, 'input_data', CatalystNoSqlError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=self.base_path + f'/index/{index_id}/item/query',
            json=input_data,
            user=CredentialUser.ADMIN
        )
        res = resp.response_json.get('data')
        res['operation'] = 'get'
        return NoSqlResponse(res)
