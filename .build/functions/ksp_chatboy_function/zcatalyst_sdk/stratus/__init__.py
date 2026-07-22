from typing import List

from ..types import Component
from ..exceptions import CatalystAPIError, CatalystStratusError
from .._http_client import AuthorizedHttpClient
from .bucket import Bucket
from .. import validator
from .._constants import (
    RequestMethod,
    CredentialUser,
    Components
)


class Stratus(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.STRATUS

    def list_buckets(self) -> List[Bucket]:
        """List all buckets and it's meta in a project.

        Access: admin

        Returns:
            List[Bucket]: List of buckets in the project.
        """

        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/bucket',
            user=CredentialUser.ADMIN
        )
        data: List = resp.response_json.get('data')
        buckets: List[Bucket] = []
        for bucket in data:
            buckets.append(Bucket(self, bucket))
        return buckets

    def head_bucket(self, bucket_name: str, throw_err = False) -> bool:
        """Checks if a bucket exists and if the user has permission to access it.

        Args:
            bucket_name (str): Name of the bucket
            throw_err(boolean, optional):
                Set to 'True' to throw an error if the bucket is not found;
                otherwise, it returns a boolean indicating the result. Defaults to 'False.'

        Raises:
            CatalystStratusError: If the bucket name is empty.
            CatalystAPIError: If the bucket is not found and `throw_err` is True.

        Access: admin

        Returns:
            bool: Returns 'True' if the bucket exist else return 'False'
        """
        try:
            validator.is_non_empty_string(bucket_name, 'bucket_name', CatalystStratusError)
            resp = self._requester.request(
                method=RequestMethod.HEAD,
                params={'bucket_name':bucket_name},
                path='/bucket',
                user=CredentialUser.ADMIN
            )
            return resp.status_code == 200
        except CatalystAPIError as err:
            if not throw_err:
                if err.http_status_code in (404, 403, 400):
                    return False
            raise err

    def bucket(self, bucket_name: str) -> Bucket:
        """Get the bucket Instance.

        Args:
            bucket_name (str): Name of the bucket

        Access: admin

        Returns:
            Bucket: Bucket instance.
        """
        validator.is_non_empty_string(bucket_name, 'bucket_name', CatalystStratusError)
        return Bucket(self, {'bucket_name': bucket_name})
