import json
from typing import Dict
from .._http_client import HttpClient
from ..exceptions import CatalystConnectorError
from ._connector import Connector
from .._constants import (
    CLIENT_ID,
    CLIENT_SECRET,
    AUTH_URL,
    REFRESH_URL,
    CONNECTOR_NAME
)

CONNECTOR_PARAMS = set([CLIENT_ID, CLIENT_SECRET, AUTH_URL, REFRESH_URL])


class Connection:
    def __init__(self, app, **kwargs) -> None:
        self._app = app
        self._requester = HttpClient(self._app)
        self.connection_json: Dict = self._get_connection_json(kwargs.get('properties'))

    def get_connector(self, connector_name: str) -> Connector:
        connector = self.connection_json.get(connector_name)
        if connector is None:
            raise CatalystConnectorError(
                'Invalid-Connector',
                'Provided connector does not exists.'
                'Kindly initialize connection with proper properties.'
            )

        if not isinstance(connector, dict):
            raise CatalystConnectorError(
                'Invalid Connector details',
                'Connector details must be a dictionary of key-value pairs'
            )

        for key in CONNECTOR_PARAMS:
            if not connector.get(key):
                raise CatalystConnectorError(
                    'Invalid Connector details',
                    (f"Either the key '{key}' is missing or value "
                     f"provided for the {key} is None in {connector_name} dict")
                )
        connector_copy = connector.copy()
        connector_copy[CONNECTOR_NAME] = connector_name
        return Connector(self, connector_copy)

    @staticmethod
    def _get_connection_json(properties):
        if not properties or not isinstance(properties, (str, dict)):
            raise CatalystConnectorError(
                'Invalid-Properties',
                'Connection properties must be passed as dict or string path to json file'
            )
        if isinstance(properties, dict):
            return properties
        try:
            with open(properties, encoding="utf-8") as json_file:
                json_dict = json.load(json_file)
        except:
            raise CatalystConnectorError(
                'Invalid-Properties',
                f'Unable to parse the property json from the file path: {properties}'
            ) from None
        return json_dict
