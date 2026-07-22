from typing import List, Union
from ..types import Component, ICatalystSegment, ICatalystProject
from ..exceptions import CatalystCacheError
from .. import validator
from .._http_client import AuthorizedHttpClient
from .._constants import (
    RequestMethod,
    CredentialUser,
    Components
)
from ._segment import Segment


class ICatalystSegmentDetails(ICatalystSegment):
    project_details: ICatalystProject


class Cache(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.CACHE

    def get_all_segment(self):
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/segment',
            user=CredentialUser.ADMIN
        )
        data: List = resp.response_json.get('data')
        segments: List[Segment] = []
        for segment in data:
            segments.append(Segment(self, segment))
        return segments

    def get_segment_details(self, seg_id: Union[str, int]) -> ICatalystSegmentDetails:
        validator.is_non_empty_string_or_number(seg_id, 'segment_id', CatalystCacheError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/segment/{seg_id}',
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def segment(self, seg_id: Union[str, int] = None):
        if seg_id is None:
            return Segment(self, None)
        validator.is_non_empty_string_or_number(seg_id, 'segment_id', CatalystCacheError)
        return Segment(self, {'id': seg_id})
