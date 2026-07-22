from time import time
import json
import math
from typing import Dict
from .. import validator
from .._http_client import HttpClient
from ..exceptions import CatalystConnectorError
from .._constants import (
    CLIENT_ID,
    CLIENT_SECRET,
    AUTH_URL,
    REFRESH_IN,
    REFRESH_URL,
    CONNECTOR_NAME,
    REFRESH_TOKEN,
    EXPIRES_IN,
    REDIRECT_URL,
    GRANT_TYPE,
    CODE,
    RequestMethod,
    ACCESS_TOKEN,
)


class Connector:
    __connector_name: str
    _refresh_token: str
    _client_id: str
    _client_secret: str
    _auth_url: str
    _refresh_url: str
    _redirect_url: str

    def __init__(self, connection_instance, connector_details: Dict[str, str]) -> None:
        self._app = connection_instance._app
        self._requester: HttpClient = connection_instance._requester
        self.connector_name = connector_details.get(CONNECTOR_NAME)
        self.__connector_name = None
        # Use setters to properly initialize hash-related properties
        self.auth_url = connector_details.get(AUTH_URL)
        self.refresh_url = connector_details.get(REFRESH_URL)
        self.refresh_token = connector_details.get(REFRESH_TOKEN)
        self.client_id = connector_details.get(CLIENT_ID)
        self.client_secret = connector_details.get(CLIENT_SECRET)
        self.redirect_url = connector_details.get(REDIRECT_URL)
        self.expires_in = (
            int(connector_details.get(EXPIRES_IN))
            if connector_details.get(EXPIRES_IN)
            else None
        )
        self.refresh_in = (
            int(connector_details.get(REFRESH_IN))
            if connector_details.get(REFRESH_IN)
            else None
        )
        self.access_token = None
        self._expires_at = None

    @property
    def expires_at(self):
        return self._expires_at or None

    @property
    def refresh_token(self):
        return self._refresh_token

    @refresh_token.setter
    def refresh_token(self, value: str):
        self._refresh_token = value
        # Invalidate the cached connector name to ensure a new cache key is generated
        self.__connector_name = None

    @property
    def client_id(self):
        return self._client_id

    @client_id.setter
    def client_id(self, value: str):
        self._client_id = value
        self.__connector_name = None

    @property
    def client_secret(self):
        return self._client_secret

    @client_secret.setter
    def client_secret(self, value: str):
        self._client_secret = value
        self.__connector_name = None

    @property
    def auth_url(self):
        return self._auth_url

    @auth_url.setter
    def auth_url(self, value: str):
        self._auth_url = value
        self.__connector_name = None

    @property
    def refresh_url(self):
        return self._refresh_url

    @refresh_url.setter
    def refresh_url(self, value: str):
        self._refresh_url = value
        self.__connector_name = None

    @property
    def redirect_url(self):
        return self._redirect_url

    @redirect_url.setter
    def redirect_url(self, value: str):
        self._redirect_url = value
        self.__connector_name = None

    @property
    def _connector_name(self):
        if not self.__connector_name:
            self.__connector_name = (
                f"ZC_CONN_{self.connector_name}:{self._get_connector_hash()}"
            )
        return self.__connector_name

    def generate_access_token(self, code: str) -> str:
        validator.is_non_empty_string(code, "grant_token", CatalystConnectorError)
        validator.is_non_empty_string(
            self.redirect_url, REDIRECT_URL, CatalystConnectorError
        )
        resp = self._requester.request(
            method=RequestMethod().POST,
            url=self.auth_url,
            data={
                GRANT_TYPE: "authorization_code",
                CODE: code,
                CLIENT_ID: self.client_id,
                CLIENT_SECRET: self.client_secret,
                REDIRECT_URL: self.redirect_url,
            },
        )
        return self._process_token_response(
            resp.response_json, update_refresh_token=True
        )

    def get_access_token(self) -> str:
        if (
            self.access_token
            and self._expires_at
            and self._expires_at > self._get_current_time_ms()
        ):
            return self.access_token
        cached_token = self._app.cache().segment().get(self._connector_name)
        value = cached_token["cache_value"]

        if value and self.is_valid_json(value):
            json_str = json.loads(value)
            self.access_token = json_str["access_token"]
            self._expires_at = json_str["expires_at"]
            if self._get_current_time_ms() < self._expires_at:
                return self.access_token

        validator.is_non_empty_string(
            self.refresh_token, "refresh_token", CatalystConnectorError
        )

        resp = self._requester.request(
            method=RequestMethod.POST,
            url=self.refresh_url,
            data={
                GRANT_TYPE: "refresh_token",
                CLIENT_ID: self.client_id,
                CLIENT_SECRET: self.client_secret,
                REFRESH_TOKEN: self.refresh_token,
            },
        )
        return self._process_token_response(
            resp.response_json, update_refresh_token=False
        )

    def _process_token_response(
        self, token_obj: dict, update_refresh_token: bool = False
    ) -> str:
        """Process token response and update instance variables."""
        try:
            self.access_token = token_obj[ACCESS_TOKEN]
            if update_refresh_token:
                self.refresh_token = token_obj[REFRESH_TOKEN]
            self.expires_in = int(token_obj[EXPIRES_IN])
            self._expires_at = self._calculate_expires_at()
        except KeyError as err:
            raise CatalystConnectorError(
                "Invalid Auth Response",
                f"{str(err)} is missing in the response json",
                token_obj,
            ) from None
        self._persist_token_in_cache()
        return self.access_token

    def _calculate_expires_at(self) -> int:
        """Calculate token expiration timestamp in milliseconds."""
        current_time_ms = self._get_current_time_ms()
        if self.refresh_in:
            return self.refresh_in * 1000 + current_time_ms
        return current_time_ms + ((self.expires_in * 1000) - 900000)

    @staticmethod
    def _get_current_time_ms() -> int:
        """Get current time in milliseconds."""
        return round(time() * 1000)

    def _persist_token_in_cache(self):
        token_obj = {
            "access_token": self.access_token,
            "expires_in": self.expires_in,
            "expires_at": self._expires_at,
        }
        return (
            self._app.cache()
            .segment()
            .put(self._connector_name, token_obj, math.ceil(self.expires_in / 3600))
        )

    def is_valid_json(self, value: str) -> bool:
        try:
            json.loads(value)
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    def _get_connector_hash(self) -> str:
        """
        Calculates a hash based on connector configuration.
        This ensures that any change in configuration results in a new cache key.
        Uses polynomial rolling hash (base 31) to generate a deterministic hash converted to
        a 5-digit hexadecimal string. This provides a good balance between uniqueness and
         brevity for cache keys.
        """
        # Build config string from non-empty values
        config_values = [
            self.refresh_token,
            self.client_id,
            self.client_secret,
            self.auth_url,
            self.refresh_url,
            self.redirect_url,
        ]
        config_str = ":".join(str(val) for val in config_values if val)

        str_hash = 0
        for char in config_str:
            # convert to 32-bit signed integer
            str_hash = self._to_int32(str_hash * 31 + ord(char))

        hash_value = self._to_int32(31 + str_hash)
        # Mask to 20 bits (5 hex digits) using unsigned 32-bit conversion
        masked = self._to_uint32(hash_value) & 0xFFFFF
        return format(masked, "05x").lower()

    @staticmethod
    def _to_int32(value: int) -> int:
        """Converts a value to a 32-bit signed integer"""
        value = value & 0xFFFFFFFF
        if value >= 0x80000000:
            value -= 0x100000000
        return value

    @staticmethod
    def _to_uint32(value: int) -> int:
        """Converts a value to a 32-bit unsigned integer"""
        return value & 0xFFFFFFFF
