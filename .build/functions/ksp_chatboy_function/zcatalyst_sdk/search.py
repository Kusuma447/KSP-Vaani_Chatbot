from typing import Dict, List, Any
from .types import Component, ICatalystSearchQuery
from . import validator
from ._http_client import AuthorizedHttpClient
from ._constants import RequestMethod, CredentialUser, Components
from .exceptions import CatalystSearchError


class Search(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.SEARCH

    def execute_search_query(
        self,
        query: ICatalystSearchQuery
    ) -> Dict[str, List[Dict[str, Any]]]:
        validator.is_non_empty_dict(query, 'query_object', CatalystSearchError)
        for key in ['search', 'search_table_columns']:
            if not query.get(key):
                raise CatalystSearchError(
                    'Invalid query object',
                    f"Either the key '{key}' is missing or the value provided for the key is empty"
                )
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/search',
            json=query,
            user=CredentialUser.USER
        )
        return resp.response_json.get('data')
