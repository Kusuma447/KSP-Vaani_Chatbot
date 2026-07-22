from typing import List, Union
from .._http_client import AuthorizedHttpClient
from .. import validator
from ..exceptions import CatalystSmartBrowzError
from .._constants import RequestMethod, CredentialUser, Components, CatalystService
from ._types import BrowserGridDetails, BrowserGridNode


class BrowserGrid:
    def __init__(self, dataverse_instance):
        self._requester: AuthorizedHttpClient = dataverse_instance._requester

    def get_component_name(self):
        return Components.SMART_BROWZ

    def get_all_grid(self) -> List[BrowserGridDetails]:
        """
        Get a list of all Browser Grids present

        Returns:
            List[BrowserGridDetails]: List of Browser Grid details
        """
        resp = self._requester.request(
            method=RequestMethod.GET,
            path="/browser-grid",
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
        data = resp.response_json.get("data")
        return data

    def get_grid(self, grid_id: Union[str, int]) -> BrowserGridDetails:
        """
        Get a Browser Grid details with Grid Name or Grid Id

        Args:
            grid_id: Name or Id of the Browser Grid

        Returns:
            BrowserGridDetails: Browser Grids details

        Raises:
            CatalystSmartBrowzError: If the grid_id is invalid
        """
        validator.is_non_empty_string_or_number(
            grid_id, "grid_id", CatalystSmartBrowzError
        )
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f"/browser-grid/{grid_id}",
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
        data = resp.response_json.get("data")
        return data

    def get_grid_nodes(self, grid_id: Union[str, int]) -> BrowserGridNode:
        """
        Get the data on Nodes in a Browser Grid

        Args:
            grid_id: Name or Id of the Browser Grid

        Returns:
            BrowserGridNode: Data on the Nodes of the Browser Grid

        Raises:
            CatalystSmartBrowzError: If the grid_id is invalid
        """
        validator.is_non_empty_string_or_number(
            grid_id, "grid_id", CatalystSmartBrowzError
        )
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f"/browser-grid/{grid_id}/stats?data_to_fetch=live_stats",
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
        data = resp.response_json.get("data")
        return data

    def stop_grid(self, grid_id: Union[str, int]) -> None:
        """
        Stop the Nodes in a Browser Grid

        Args:
            grid_id: Name or Id of the Browser Grid

        Returns:
            None

        Raises:
            CatalystSmartBrowzError: If the grid_id is invalid
        """
        validator.is_non_empty_string_or_number(
            grid_id, "grid_id", CatalystSmartBrowzError
        )
        self._requester.request(
            method=RequestMethod.POST,
            path=f"/browser-grid/{grid_id}/stop",
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
