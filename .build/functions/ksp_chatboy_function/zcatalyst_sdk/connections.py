from zcatalyst_sdk import validator
from zcatalyst_sdk.exceptions import CatalystConnectionError
from .types import (
    Component,
    ICatalystConnectionsResponse
)
from ._http_client import AuthorizedHttpClient
from ._constants import RequestMethod, CredentialUser, Components

class Connections(Component):
    def __init__(self, app) -> None:
        """
        Initialize the Connections component.

        Args:
            app: The Catalyst app instance.
        """
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        """
        Get the name of the component.

        Returns:
            str: The name of the component.
        """
        return Components.CONNECTIONS

    def get_connection_credentials(self, connection_link_name: str) -> ICatalystConnectionsResponse:
        """
        Retrieve credentials for a given connection.

        Args:
            connection_link_name (str): The name of the connection.

        Returns:
            ICatalystConnectionsResponse: The connection credentials data.
        """
        validator.is_non_empty_string(
            connection_link_name, 'connection_link_name', CatalystConnectionError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/connection-details',
            params={'connection-link-name': connection_link_name},
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')
