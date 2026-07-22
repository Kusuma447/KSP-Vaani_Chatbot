from typing import Dict, Optional
from ..exceptions import CatalystCacheError
from ..types import (
    ICatalystCache,
    ICatalystProject,
    ICatalystSegment,
    ParsableComponent
)
from .._constants import (
    RequestMethod,
    CredentialUser,
    Components
)
from .._http_client import AuthorizedHttpClient
from .. import validator


class ICatalystCacheResp(ICatalystCache):
    project_details: Optional[ICatalystProject]


class Segment(ParsableComponent):
    def __init__(self, cache_instance, segment_details: Dict):
        if segment_details:
            validator.is_non_empty_dict(segment_details, 'segment_details', CatalystCacheError)
        self._requester: AuthorizedHttpClient = cache_instance._requester
        self._id = segment_details.get('id') if segment_details else None
        self._segment_details = segment_details

    def __repr__(self) -> str:
        return str(self.to_dict())

    def get_component_name(self):
        return Components.CACHE

    def put(
        self,
        key: str,
        value: str,
        expiry: int = None
    ) -> ICatalystCacheResp:
        validator.is_non_empty_string(key, 'cache_key', CatalystCacheError)
        api_path = f'/segment/{self._id}/cache' if self._id else '/cache'
        req_json = {
            'cache_name': key,
            'cache_value': value,
            'expiry_in_hours': expiry
        }
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=api_path,
            json=req_json,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def update(
        self,
        key: str,
        value: str,
        expiry: int = None
    ) -> ICatalystCacheResp:
        validator.is_non_empty_string(key, 'cache_key', CatalystCacheError)
        api_path = f'/segment/{self._id}/cache' if self._id else '/cache'
        req_json = {
            'cache_name': key,
            'cache_value': value,
            'expiry_in_hours': expiry
        }
        resp = self._requester.request(
            method=RequestMethod.PUT,
            path=api_path,
            json=req_json,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def get(
        self,
        key: str
    ) -> ICatalystCacheResp:
        validator.is_non_empty_string(key, 'cache_key', CatalystCacheError)
        api_path = f'/segment/{self._id}/cache' if self._id else '/cache'
        query_params = {
            'cacheKey': key
        }
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=api_path,
            params=query_params,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def get_value(self, key: str) -> str:
        cache_obj = self.get(key)
        return cache_obj.get('cache_value')

    def delete(self, key: str) -> bool:
        validator.is_non_empty_string(key, 'cache_key', CatalystCacheError)
        api_path = f'/segment/{self._id}/cache' if self._id else '/cache'
        query_params = {
            'cacheKey': key
        }
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=api_path,
            params=query_params,
            user=CredentialUser.ADMIN
        )
        return bool(resp)

    def to_dict(self) -> ICatalystSegment:
        return self._segment_details

    def to_string(self):
        return repr(self)
