

from typing import Dict
from ..types.stratus import (
    StratusObjectDetails,
    ObjectVersionsRes,
    StratusObjectsRes
)
from .. import validator
from ..exceptions import CatalystStratusError
from ..types import ParsableComponent
from .._http_client import AuthorizedHttpClient
from .._constants import (
    RequestMethod,
    CredentialUser,
    Components
)

class StratusObject(ParsableComponent):
    def __init__(self, bucket_instance, object_details: Dict):
        validator.is_non_empty_dict(object_details, 'object_details', CatalystStratusError)
        self._requester: AuthorizedHttpClient = bucket_instance._requester
        self._key = object_details.get('key')
        self.object_details = object_details
        self.req_params = {
            'bucket_name': bucket_instance.get_name(),
            'object_key': self._key
        }

    def __repr__(self) -> str:
        return str(self.object_details)

    def get_component_name(self):
        return Components.STRATUS

    def get_details(self, version_id = None) -> StratusObjectDetails:
        """
        Get the details of an object.

        Args:
            version_id (str, optional): The ID of a specific version of the object to retrive
                details for. If not provided, details for the latest version are returned.

        Access: admin

        Returns:
            StratusObjectDetails: The details of the object or its specified version.

        Example:
            ```python
            # Get details of a specific version of an object
            object_details = object.get_details(version_id="version-id-123")
            print("Object Details for Version:", object_details)
            ```
        """
        params = {
            **self.req_params,
            'version_id': version_id
        }
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/bucket/object',
            params = params,
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def list_paged_versions(
        self,
        max_versions = None,
        next_token = None
    ) -> StratusObjectsRes:
        """
        Retrieve a paginated list of versions for a given object.

        Args:
            max_versions (str, optional): The maximum number of versions to return in the response.
                Defaults to 1000.
            next_token (str, optional): The token to retrieve the next set of versions
                if they exist. Defaults to None.

        Access: admin

        Returns:
            StratusObjectsRes: The list of object versions and their details.

        Example:
            ```python
            # Get the first 10 versions of an object
            versions = object.list_paged_versions(max_versions=10)
            print("Object Versions:", versions)
            ```
        """
        req_params = {
            **self.req_params,
            'max_versions':  max_versions,
            'continuation_token': next_token
        }
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/bucket/object/versions',
            params = req_params,
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def list_iterable_versions(self, max_versions = None):
        """
        Retrieve a paginated list of object versions as an iterable.

        Args:
            max_versions (str, optional): The maximum number of versions to return in each response.
                Defaults to 1000.

        Access: admin

        Yields:
            dict: A dictionary containing details of each version.

        Example:
            ```python
            # Iterate through versions of an object
            for version in object.list_iterable_versions(max_versions=5):
                print("Version:", version)
            ```
        """
        next_token: str = None
        while True:
            data: ObjectVersionsRes = self.list_paged_versions(max_versions, next_token)
            yield from data['version']
            if not data['is_truncated']:
                break
            next_token = data['next_token']

    def put_meta(self,meta_details: Dict[str, str]) -> Dict[str, str]:
        """
        Add metadata for an object. It replaces the existing metadata details.

        Args:
            meta_details (Dict[str, str]):
                A dictionary of metadata key-value pairs to be added to the object.

        Access: admin

        Returns:
            Dict[str, str]: The response data from the metadata operation.

        Example:
            ```python
            # Add metadata to an object
            meta_data = {'author': 'John Doe', 'project': 'My Project'}
            response = object.put_meta(meta_details=meta_data)
            print("Metadata Update Response:", response)
            ```
        """
        meta_data = {
            'meta_data': meta_details
        }
        resp = self._requester.request(
            method=RequestMethod.PUT,
            path='/bucket/object/metadata',
            params = self.req_params,
            json=meta_data,
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def generate_cache_signed_url(self, url, expires=None) -> Dict[str,str]:
        """
        Generate a signed URL for caching in a caching-enabled bucket.

        Args:
            url (str): The cached URL of the object.
            expires (str, optional): The expiration time in seconds for the signed URL.
                Defaults to 3600s.

        Access: admin

        Returns:
            Dict[str, str]: The response containing the generated signed URL.

        Example:
            ```python
            # Generate a signed URL for an object with a 3000 seconds expiration
            signed_url = object.generate_cache_signed_url(
                url='http://example.com/cached-object-url',
                expires=3000
            )
            print("Generated Signed URL:", signed_url)
            ```
        """
        req_param = {
            'url': url,
            'expiry_in_seconds': expires
        }
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/auth/signed-url',
            params = req_param,
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def to_dict(self):
        return self.object_details

    def to_string(self):
        return repr(self)
