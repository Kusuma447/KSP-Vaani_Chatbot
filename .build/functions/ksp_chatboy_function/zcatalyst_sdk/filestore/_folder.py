from io import BufferedReader
from typing import Dict, Optional, Union
from ..exceptions import CatalystFilestoreError
from .._http_client import AuthorizedHttpClient
from .. import validator
from .._constants import (
    RequestMethod,
    CredentialUser,
    Components
)
from ..types import (
    ParsableComponent,
    ICatalystFile,
    ICatalystFolder,
    ICatalystGResponse,
    ICatalystProject,
    ICatalystSysUser
)


class ICatalystFolderDetails(ICatalystFolder):
    created_time: Optional[str]
    created_by: Optional[ICatalystSysUser]
    project_details: Optional[ICatalystProject]


class ICatalystFileDetails(ICatalystFile, ICatalystGResponse):
    pass


class Folder(ParsableComponent):
    def __init__(self, filestore_instance, folder_details: Dict):
        validator.is_non_empty_dict(folder_details, 'folder_details', CatalystFilestoreError)
        self._requester: AuthorizedHttpClient = filestore_instance._requester
        self._folder_details = folder_details
        self._id = folder_details.get('id')

    def __repr__(self) -> str:
        return str(self._folder_details)

    def get_component_name(self):
        return Components.FILE_STORE

    def update(self, name: str) -> ICatalystFolderDetails:
        validator.is_non_empty_string(name, 'folder_name', CatalystFilestoreError)
        resp = self._requester.request(
            method=RequestMethod.PUT,
            path=f'/folder/{self._id}',
            json={
                'folder_name': name
            },
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def delete(self):
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=f'/folder/{self._id}',
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return bool(resp_json.get('data'))

    def get_file_details(self, file_id: Union[int, str]) -> ICatalystFileDetails:
        validator.is_non_empty_string_or_number(file_id, 'file_id', CatalystFilestoreError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/folder/{self._id}/file/{file_id}',
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def delete_file(self, file_id: Union[int, str]) -> bool:
        validator.is_non_empty_string_or_number(file_id, 'file_id', CatalystFilestoreError)
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=f'/folder/{self._id}/file/{file_id}',
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return bool(resp_json.get('data'))

    def upload_file(
            self,
            name: str,
            file: BufferedReader
    ) -> ICatalystFileDetails:
        Folder._validate_file_details(name, file)
        # data = [
        #     ('code',('',file_details['code'],'application/octet-stream')),
        #     ('file_name',(None,file_details['name']))
        # ]
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=f'/folder/{self._id}/file',
            files={
                'code': ('', file, 'application/octet-stream')
            },
            data={
                'file_name': name
            },
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def download_file(self, file_id: Union[int, str]):
        resp = self.get_file_stream(file_id)
        return resp.content

    def get_file_stream(self, file_id: Union[int, str]):
        validator.is_non_empty_string_or_number(file_id, 'file_id', CatalystFilestoreError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/folder/{self._id}/file/{file_id}/download',
            user=CredentialUser.USER,
            stream=True
        )
        return resp.response

    @staticmethod
    def _validate_file_details(name, file):
        if not isinstance(file, BufferedReader):
            raise CatalystFilestoreError(
                'INVALID_FILE_DETAILS',
                'Code must be an instance of BufferReader and cannot be empty'
            )
        validator.is_non_empty_string(name, 'file_name', CatalystFilestoreError)

    def to_string(self):
        return repr(self)

    def to_dict(self) -> ICatalystFolderDetails:
        return self._folder_details
