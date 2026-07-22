from abc import ABC
from typing import Union
from ..exceptions import CatalystDatastoreError
from ..types import (
    CatalystBucketObject,
    Component,
    ICatalystBulkJob,
    ICatalystBulkCallback,
    ICatalystBulkReadQuery,
    ICatalystBulkWriteInput
)
from .._constants import (
    RequestMethod,
    CredentialUser,
    Components
)
from .. import validator
from .._http_client import AuthorizedHttpClient


class BulkJob(Component, ABC):
    def __init__(self, table_instance, operation: str):
        self._requester: AuthorizedHttpClient = table_instance._requester
        self._identifier = table_instance._identifier
        self._operation = operation

    def get_component_name(self):
        return Components.DATA_STORE

    def get_status(self, job_id: Union[str, int]) -> ICatalystBulkJob:
        validator.is_non_empty_string_or_number(job_id, 'job_id', CatalystDatastoreError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/bulk/{self._operation}/{job_id}',
            user=CredentialUser.ADMIN
        )
        return resp.response_json.get('data')

    def get_result(self, job_id: Union[str, int]):
        validator.is_non_empty_string_or_number(job_id, 'job_id', CatalystDatastoreError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/bulk/{self._operation}/{job_id}/download',
            user=CredentialUser.ADMIN,
            stream=True
        )
        return resp.response


class BulkRead(BulkJob):
    def __init__(self, table_instance):
        super().__init__(table_instance, 'read')

    def create_job(
        self,
        query: ICatalystBulkReadQuery = None,
        callback: ICatalystBulkCallback = None
    ) -> ICatalystBulkJob:
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/bulk/read',
            json={
                'table_identifier': self._identifier,
                'query': query,
                'callback': callback
            },
            user=CredentialUser.ADMIN
        )
        return resp.response_json.get('data')


class BulkWrite(BulkJob):
    def __init__(self, table_instance):
        super().__init__(table_instance, 'write')

    def create_job(
        self,
        file_details: Union[CatalystBucketObject, str],
        options: ICatalystBulkWriteInput = None,
        callback: ICatalystBulkCallback = None
    ) -> ICatalystBulkJob:
        if options:
            validator.is_non_empty_dict(
                options, 'options', CatalystDatastoreError
            )
        req_json = {
            'table_identifier': self._identifier,
            'callback': callback
        }
        if validator.is_non_empty_string(file_details, 'file_id'):
            req_json['file_id']=file_details
        else:
            validator.is_non_empty_dict(file_details, 'object_details', CatalystDatastoreError)
            req_json['object_details']=file_details
        req_json.update(options)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/bulk/write',
            json=req_json,
            user=CredentialUser.ADMIN
        )
        return resp.response_json.get('data')
