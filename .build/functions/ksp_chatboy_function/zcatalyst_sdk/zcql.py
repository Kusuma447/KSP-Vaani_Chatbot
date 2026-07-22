from typing import Dict, List, TypedDict
from .types import Component
from .exceptions import CatalystZCQLError
from ._http_client import AuthorizedHttpClient
from ._constants import RequestMethod, CredentialUser, Components, AcceptHeader

ZcqlQueryOutput = TypedDict("ZcqlQueryOutput", {"table_name": Dict})


class Zcql(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.ZCQL

    def execute_query(self, query: str) -> List[ZcqlQueryOutput]:
        """Execute a ZCQL query on the Catalyst Data Store.

        Args:
            query (str): The ZCQL query string to execute. Must be a non-empty string."
        Returns:
            List[ZcqlQueryOutput]: A list of dictionaries containing the query results.
                                   Each dictionary maps table names to their respective data.
        Raises:
            CatalystZCQLError: If the query is None, empty, or not a string.

        Example:
            >>> zcql = app.zcql()
            >>> results = zcql.execute_query("SELECT * FROM Users WHERE Age > 25")
        """
        if not query or not isinstance(query, str):
            raise CatalystZCQLError("INVALID_QUERY", "Query must be a non empty string")
        req_json = {"query": query}
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/query",
            json=req_json,
            user=CredentialUser.USER,
            headers={AcceptHeader.KEY: AcceptHeader.ZCQL},
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def execute_olap_query(self, query: str) -> List[ZcqlQueryOutput]:
        """Execute a ZCQL OLAP (Online Analytical Processing) query on the Catalyst Data Store.

        Args:
            query (str): The ZCQL query string to execute in OLAP mode. Must be a non-empty string.
        Returns:
            List[ZcqlQueryOutput]: A list of dictionaries containing the query results.
                                   Each dictionary maps table names to their respective aggregated
                                   data. The structure is similar to execute_query but optimized
                                   for analytical result sets.
        Raises:
            CatalystZCQLError: If the query is None, empty, or not a string.

        Example:
            >>> zcql = app.zcql()
            >>> results = zcql.execute_olap_query(
            ...     "SELECT * FROM Test"
            ... )
        """
        if not query or not isinstance(query, str):
            raise CatalystZCQLError("INVALID_QUERY", "Query must be a non empty string")
        req_json = {"query": query, "OLAP": True}
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/query",
            json=req_json,
            user=CredentialUser.USER,
            headers={AcceptHeader.KEY: AcceptHeader.ZCQL},
        )
        resp_json = resp.response_json
        return resp_json.get("data")
