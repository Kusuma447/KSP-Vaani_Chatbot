from typing import List
from ..exceptions import CatalystNoSqlError
from ..validator import (
    is_non_empty_string_or_number
)
from ..types.nosql import NoSqlTableResourceRes, NoSqlTableResponse
from ..types import Component
from .._http_client import AuthorizedHttpClient
from .._constants import RequestMethod, CredentialUser, Components
from ._table_items import TableItem

class NoSql(Component):
    """This class used to peform NoSQL operations.

    Args:
        Component (ABC): Class used to retrieve the component's name.
    """
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.NOSQL

    def get_all_tables(self) -> List[TableItem]:
        """ Get all the NoSQL tables in the project.

        Returns:
            List[NoSqlTableResponse]: Returns the list of tables.
        """
        resp = self._requester.request(
            method=RequestMethod.GET,
            path= '/nosqltable',
            user=CredentialUser.ADMIN
        )
        res = resp.response_json.get('data')
        tables: List[TableItem] = []
        for table in res:
            tables.append(TableItem(self, table))
        return tables

    def get_table_resources(self, table_name) -> NoSqlTableResourceRes:
        """Get a NoSQL table with table Name or table Name (or) Id.

        Args:
            table_name (str): table_name Id or Name of the NoSQL Table

        Returns:
            NoSqlTableResourceRes: NoSQL Table object
        """
        is_non_empty_string_or_number(table_name, 'table_name', CatalystNoSqlError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path= f'/nosqltable/{table_name}',
            user=CredentialUser.ADMIN
        )
        res = resp.response_json.get('data')
        return res

    def get_table(self, table_id):
        """Get table instance to perform table operations.

        Args:
            table_id (str, int): Id (or) Name of the table.

        Returns:
            TableItem: Returns the table instance.
        """
        is_non_empty_string_or_number(table_id, 'table_id', CatalystNoSqlError)
        try:
            return TableItem(self, int(table_id))
        except ValueError:
            return TableItem(self, str(table_id))
