from typing import Union, List
from ..types import Component, ICatalystFolder
from ..exceptions import CatalystFilestoreError
from .._http_client import AuthorizedHttpClient
from .._constants import RequestMethod, CredentialUser, Components
from ._folder import Folder
from .. import validator


class Filestore(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.FILE_STORE

    def create_folder(self, name: str):
        validator.is_non_empty_string(name, 'folder_name', CatalystFilestoreError)
        req_json = {
            'folder_name': name
        }

        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/folder',
            json=req_json,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        data = resp_json.get('data')
        return Folder(self, data)

    def get_all_folders(self):
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/folder',
            user=CredentialUser.USER
        )
        data: List = resp.response_json.get('data')
        folders: List[Folder] = []
        for folder in data:
            folders.append(Folder(self, folder))
        return folders

    def get_folder_details(self, folder_id: Union[int, str]) -> ICatalystFolder:
        validator.is_non_empty_string_or_number(folder_id, 'folder_id', CatalystFilestoreError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/folder/{folder_id}',
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        data = resp_json.get('data')
        return data

    def folder(self, folder_id: Union[int, str]):
        validator.is_non_empty_string_or_number(folder_id, 'folder_id', CatalystFilestoreError)
        return Folder(self, {'id': folder_id})
