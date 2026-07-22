from io import BufferedReader
from typing import List, Dict, Literal, Union
import mimetypes
import urllib.parse

from .. import validator
from ..exceptions import CatalystAPIError, CatalystStratusError
from ..types import ParsableComponent
from ..types.stratus import (
    StratusInitiateUploadOptions, StratusObjectsRes, StratusBucket, CopyObjectResponse,
    BucketCorsResponse, DeleteObjectOptions, InitiateMultipartUploadResponse, RenameObjectResponse,
    MultipartUploadSummaryRes,StratusDownloadOptions, StratusPutObjectRes, StratusUploadOptions,
    UnzipObjectResponse, DeleteObjectPathResponse
)
from .object import StratusObject
from .._http_client import AuthorizedHttpClient
from .._constants import (
    STRATUS_SUFFIX, ENVIRONMENT, RequestMethod, CredentialUser,
    CatalystService,Components
)
from ._auth_util import AuthUtil

class Bucket(ParsableComponent):
    def __init__(self, stratus_instance, bucket_details: Dict):
        validator.is_non_empty_dict(bucket_details, 'bucket_details', CatalystStratusError)
        self._requester: AuthorizedHttpClient = stratus_instance._requester
        self._bucket_name = bucket_details.get('bucket_name')
        self.bucket_details = bucket_details
        self._auth_util = AuthUtil(self._bucket_name, self._requester)
        if self._requester._app.config.get(ENVIRONMENT) == 'Development':
            self.bucket_domain = f'https://{self._bucket_name}-development{STRATUS_SUFFIX}'
        else:
            self.bucket_domain = f'https://{self._bucket_name}{STRATUS_SUFFIX}'

    def __repr__(self) -> str:
        return str(self.bucket_details)

    def get_component_name(self):
        return Components.STRATUS

    def get_name(self):
        return self._bucket_name

    def get_details(self) -> StratusBucket:
        """
        Retrieve the details of the bucket.

        Access: admin

        Returns:
            StratusBucket: The details of the bucket.
        """
        resp = self._requester.request(
            method=RequestMethod.GET,
            params={'bucket_name': self._bucket_name},
            path='/bucket',
            user=CredentialUser.ADMIN
        )
        data: StratusBucket = resp.response_json.get('data')[0]
        return data

    def list_paged_objects(
        self,
        max_keys = None,
        prefix = None,
        next_token = None,
        folder_listing = False,
        order_by : Literal['asc', 'desc'] = None
    ) -> StratusObjectsRes:
        """
            List objects in the bucket using pagination.

            Args:
                max_keys (int, optional): The maximum number of objects to return in one response.
                    Defaults to 1000 if not specified.
                prefix (str, optional): Return only objects whose keys start with this prefix.
                next_token (str, optional): The continuation token for paginated results.
                    Use this to fetch the next set of objects when the previous response
                    is truncated.
                folder_listing (bool, optional): If True, lists objects in a folder-like structure.
                    Defaults to False.
                order_by (Literal['asc', 'desc'], optional):
                    Specifies the order in which objects are listed.
                    Use `"asc"` for ascending order or `"desc"`
                    for descending order. Defaults to `"asc"`.

            Access: admin

            Returns:
                StratusObjectsRes: An object containing the list of bucket contents and metadata.

            Example:
                ```python
                response = bucket.list_paged_objects(
                    max_keys=100, prefix='folder/subfolder/', next_token='abc123',
                    folder_listing=True, order_by='desc'
                )
                print(response.contents)  # List of objects
                ```
            """
        req_params = {
            'bucket_name': self._bucket_name,
            'max_keys':  max_keys,
            'prefix': prefix,
            'continuation_token': next_token,
            'folder_listing': folder_listing,
            'order_by': order_by
        }
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/bucket/objects',
            params= req_params,
            user=CredentialUser.ADMIN
        )
        data: StratusObjectsRes = resp.response_json.get('data')
        objects: List[StratusObject] = []
        for key in data['contents']:
            objects.append(StratusObject(self, key))
        data['contents'] = objects
        return data

    def list_iterable_objects(
        self,
        prefix = None,
        max_keys = None,
        next_token = None,
        folder_listing = False,
        order_by : Literal['asc', 'desc'] = None
    ):
        """
        List objects in the bucket using pagination, returning an iterable objects.

        Args:
            prefix (str, optional): Filters results to include only objects whose keys
                start with this prefix. Defaults to None.
            max_keys (int, optional): The maximum number of objects returned in a single
                response. Defaults to 1000.

        Access: admin

        Yields:
            List[Objects]: A stream of objects in the bucket, page by page.

        Example:
            ```python
            for obj in bucket.list_iterable_objects(prefix="folder/", max_keys=100):
                print(obj)
            ```
        """
        next_token: str = None
        while True:
            objects = self.list_paged_objects(
                max_keys, prefix, next_token, folder_listing, order_by
            )
            yield from objects['contents']
            if not objects['truncated']:
                break
            next_token = objects['next_continuation_token']

    # def get_multiple_objects(
    #     self,
    #     objects: Union[List[str], str],
    #     prefix: List[str] = None,
    #     next_token = None
    # ):
    #     """Download one or more objects in the bucket as zip.

    #     Args:
    #         objects (Union[List[str], str]): List of object names or '*' or 'Top'
    #         prefix (List[str], optional): List of prefix. Defaults to [].
    #         next_token (str, optional): Token to continue next iteration . Defaults to None.

    #     Returns:
    #         stream: Downloaded content as stream
    #     """
    #     if isinstance(objects, list):
    #         objects = [{'key': key} for key in objects]

    #     req_json = {
    #         'objects': objects,
    #         'prefix': prefix
    #     }
    #     resp = self._requester.request(
    #         method=RequestMethod.POST,
    #         json= req_json,
    #         params= {'continuationToken': next_token},
    #         url=self.bucket_domain + '/?zip',
    #         external = True,
    #         catalyst_service=CatalystService.STRATUS,
    #         user=CredentialUser.USER
    #     )
    #     data = resp.response.content
    #     response = {
    #         'data' : data,
    #         'continuation_token' : resp.headers.get('Continuation-Token')
    #     }
    #     return response

    def put_object(
        self,
        key: str,
        body: Union[BufferedReader, str, bytes],
        options: StratusUploadOptions = None
    ) -> Union[bool, StratusPutObjectRes]:
        """
        Upload an object to the bucket.

        Args:
            key (str): The name of the object.
            body (Union[BufferedReader, str, bytes]): The content of the object to upload. This can
                be a file stream, a string, or binary data.
            options (StratusUploadOptions, optional): Optional configuration options for the upload,
                such as metadata, compression, and expiration settings.

        Access: admin, user

    Returns:
        Union[bool, StratusPutObjectRes]:
            - Returns `True` if the upload was successful and no extraction is required.
            - Returns `StratusPutObjectRes` when `extractUpload` is set to `True`.
                This response contains a `task_id` that can be used to track the extraction
                status using the `unzip_object_status` operation.

        Example:
            ```python
            bucket.put_object(
                key="example.txt",
                body="Hello, World!",
                options={ meta_data:{ "author": "John"}}
            )
            ```
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        self._validate_object_body(body)

        content_type, _other = mimetypes.guess_type(key)
        auth_sign = self._auth_util.get_bucket_signature()
        url = self.bucket_domain + ('/_signed' if auth_sign else '')
        header, param = {}, {}
        if options:
            header['overwrite'] = options.get('overwrite')
            header['expires-after'] =  options.get('ttl')
            header['compress']= options.get('compress')
            param['extractAndUpload'] = options.get('extract_upload')
            content_type = options.get('content_type') or content_type
            meta_data = options.get('meta_data')
            meta_data =  ";".join([f"{key}={value}" for key, value in meta_data.items()]) + ";" \
                if meta_data else None
            header['x-user-meta'] =  meta_data
        header['Content-Type'] = content_type
        header['compress'] = header.get('compress') or 'false'
        resp = self._requester.request(
            method=RequestMethod.PUT,
            url=url + f'/{urllib.parse.quote(key)}',
            data=body,
            params={**auth_sign, **param} if auth_sign else param,
            stream=True,
            headers=header,
            external = True,
            auth=not auth_sign,
            catalyst_service=CatalystService.STRATUS,
            user=CredentialUser.USER,
            token_only=True,
        )
        return resp.status_code == 200 or resp.response_json

    def truncate(self) -> Dict[str,str]:
        """
        Delete all objects in the bucket, effectively emptying it.

        Access: admin

        Returns:
            Dict[str, str]: A message indicating the initiation of the truncation process.

        Example:
            ```python
            result = bucket.truncate()
            print(result)  # Output: {"message": "Bucket truncate has been scheduled."}
            ```
        """
        param = { 'bucket_name': self._bucket_name }
        resp = self._requester.request(
			method= RequestMethod.DELETE,
			path= '/bucket/truncate',
			params=param,
			user= CredentialUser.ADMIN
        )
        return resp.response_json.get('data')

    def get_object(self, key: str, options: StratusDownloadOptions = None):
        """
        Download an object from the bucket.

        Args:
            key (str): The name of the object.
            options (StratusDownloadOptions, optional): Options to configure the download,
                such as range and version.

        Access: admin, user

        Returns:
            stream: The content of the object as a stream.

        Example:
            ```python
            content = bucket.get_object("example.txt")
            with open("example.txt", "wb") as file:
                file.write(content)
            ```
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        sign = self._auth_util.get_bucket_signature() or {}
        params = {**sign}
        headers = {}
        if options:
            headers['Range'] = 'bytes=' + options.get('range') if options.get('range') else None
            params['versionId'] =  options.get('version_id')
        url = self.bucket_domain + ('/_signed' if sign else '')
        resp = self._requester.request(
            method=RequestMethod.GET,
            url= url + f'/{urllib.parse.quote(key)}',
            params=params,
            stream=True,
            catalyst_service=CatalystService.STRATUS,
            headers=headers,
            external=True,
            auth=not sign,
            user=CredentialUser.USER,
            token_only= True,
        )
        data = resp.response.content
        return data

    def delete_object(self,
        key: str,
        version_id: str = None,
        ttl: Union[str, int] = None
    ) -> Dict[str, str]:
        """
        Delete an object in the bucket.

        Args:
            key (str): The name of the object key.
            version_id (str, optional): The unique identifier for a specific version of the object.
            ttl (Union[str, int], optional): Time delay (in seconds) before the object is deleted.

        Access: admin, user

        Returns:
            Dict[str, str]: The result of the deletion operation.

        Example:
            ```python
            result = bucket.delete_object(key="example.txt", ttl=3600)
            print(result)  # Output: {"message": "Object Deletion successful."}
            ```
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        if (self._auth_util.get_user_type() == 'admin' or \
            self._auth_util.get_user_scope() == 'admin'):
            objects = [{
                'key': key,
                'version_id': version_id
            }]
            return self.delete_objects(objects, ttl)
        options = {
            'versionId': version_id,
            'deleteAllVersions': 'false' if version_id else 'true',
            'ttl': ttl
        }
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            url=f'{self.bucket_domain}/{urllib.parse.quote(key)}',
            params={ **options },
            external=True,
            catalyst_service=CatalystService.STRATUS,
            user=CredentialUser.USER,
            token_only= True
        )
        data = { 'message': 'Object Deletion successful' }
        if resp.status_code == 202:
            data = resp.response_json
        return data

    def delete_objects(
        self,
        objects: List[DeleteObjectOptions],
        ttl: Union[str, int] = None
    ) -> Dict[str, str]:
        """
        Delete multiple objects in the bucket.

        Args:
            objects (List[DeleteObjectOptions]): A list of objects to delete,
                    including version IDs if applicable.
            ttl (Union[str, int], optional): Time delay (in seconds) before the objects are deleted.

        Access: admin

        Returns:
            Dict[str, str]: Result of the deletion operation.

        Example:
            ```python
            objects_to_delete = [
                {"key": "example1.txt"},
                {"key": "example2.txt", "version_id": "v1"}
            ]
            result = bucket.delete_objects(objects=objects_to_delete)
            print(result)  # Output: {"message": "Object deletion scheduled"}
            ```
        """
        validator.is_non_empty_list(objects, 'objects_list', CatalystStratusError)
        req_body = {
            'objects': objects,
            'ttl_in_seconds': ttl
        }
        resp = self._requester.request(
            method=RequestMethod.PUT,
            path='/bucket/object',
            params={'bucket_name':self._bucket_name},
            json=req_body,
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def get_cors(self) -> List[BucketCorsResponse]:
        """
        Retrieve the CORS (Cross-Origin Resource Sharing) details of the bucket.

        Access: admin

        Returns:
            List[BucketCorsResponse]: A list of CORS configurations for the bucket.

        Example:
            ```python
            cors_rules = bucket.get_cors()
            for rule in cors_rules:
                print(rule)
            ```
        """
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/bucket/cors',
            params={'bucket_name':self._bucket_name},
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def purge_cache(self, items: List[str] = None) -> Dict[str,str]:
        """
        Clear the cached objects in the bucket.

        Args:
            items (List[str], optional): A list of object names or paths to clear from the cache.
                If not provided, all cached items will be cleared.

        Access: admin

        Returns:
            Dict[str, str]: The result of the purge cache operation.

        Example:
            ```python
            result = bucket.purge_cache(items=["example.txt", "folder/"])
            print(result)  # Output: {"message": "Bucket cache purged successfully"}
            ```
        """
        resp = self._requester.request(
            method=RequestMethod.PUT,
            path='/bucket/purge-cache',
            params={'bucket_name':self._bucket_name},
            json=items or [],
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def unzip_object(self, key: str, dest_path: str) -> UnzipObjectResponse:
        """
        Extract the contents of a ZIP object and upload each file as an individual
            object to the same bucket.

        Args:
            key (str): The name of the object key (ZIP file).
            dest_path (str): The destination path where the extracted files will be uploaded.

        Access: admin

        Returns:
            UnzipObjectResponse: The result of the unzip operation.

        Example:
            ```python
            response = bucket.unzip_object(key="sam/archive.zip", dest_path="extracted/")
            print(response)
            ```
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_non_empty_string_or_number(dest_path, 'dest_path', CatalystStratusError)
        req_json = {
            'bucket_name': self._bucket_name,
            'object_key': key,
            'destination': dest_path
        }
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/bucket/object/zip-extract',
            params=req_json,
            user=CredentialUser.ADMIN
        )
        data = self._serialize_res(resp.response_json.get('data'))
        return data

    def get_unzip_status(self, key: str, task_id: Union[str, int]) -> Dict[str, str]:
        """
        Get the status of an unzip operation.

        Args:
            key (str): The name of the object(zip object).
            task_id (Union[str, int]): The task ID returned when the unzip operation was initiated.

        Access: admin

        Returns:
            Dict[str, str]: The status of the unzip operation.

        Example:
            ```python
            status = bucket.get_unzip_status(key="sam/archive.zip", task_id="12345")
            print(status)
            ```
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_non_empty_string_or_number(task_id, 'task_id', CatalystStratusError)
        req_json = {
            'bucket_name': self._bucket_name,
            'object_key': key,
            'task_id': task_id
        }
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/bucket/object/zip-extract/status',
            params=req_json,
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def generate_presigned_url(
        self,
        key: str,
        url_action: Literal['PUT', 'GET'],
        expiry_in_sec: str = None,
        active_from: str = None,
        version_id: str = None
    ) -> Dict[str,str]:
        """
        Generate a pre-signed URL for a specific object in the bucket.
        This URL can be used to perform operations like uploading (`PUT`)
            or downloading (`GET`) the object.

        Args:
            key (str): Name of the object for which the URL is generated.
            url_action (Literal['PUT', 'GET']): The action to be performed using the URL.
                - 'PUT' for uploading the object.
                - 'GET' for downloading the object.
            expiry_in_sec (str, optional): The expiration time of the URL in seconds.
                Defaults 3600s.
            active_from (str, optional): The time (in milliseconds) when the URL becomes active.
                Defaults to None, meaning the URL is active immediately.
            version_id (str, optional): The version ID of the object for which the URL is generated.
                Only relevant for `GET` actions.

        Access: admin

        Returns:
            Dict[str, str]: A dictionary containing the generated pre-signed URL.

        Example:
            ```python

            # Generate a URL to upload a file named 'document.txt' that expires in 3600 seconds
            upload_url = bucket.generate_presigned_url(
                key='fx/document.txt',
                url_action='PUT',
                expiry_in_sec='3600'
            )
            print("Upload URL:", upload_url)
            ```
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_non_empty_string(url_action, 'url_action', CatalystStratusError)
        req_param = {
            'bucket_name': self._bucket_name,
            'object_key': key,
            'expiry_in_seconds': expiry_in_sec,
            'active_from': active_from,
            'version_id': version_id
        }
        resp = self._requester.request(
            method= url_action,
            path='/bucket/object/signed-url',
            params = req_param,
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.SERVERLESS
        )
        data = resp.response_json.get('data')
        return data

    def delete_path(self, path) -> DeleteObjectPathResponse:
        """
        Delete a path and it's objects inside the path from the bucket.

        Args:
            path (str): The path or prefix in the bucket to be deleted.

        Access: admin

        Returns:
            DeleteObjectPathResponse: A response object with details about the deletion operation.

        Example:
            ```python
            # Delete a folder and its contents
            response = bucket.delete_path(path='folder/subfolder')
            print("Delete Path Response:", response)
            ```
        """
        validator.is_non_empty_string(path, 'path', CatalystStratusError)
        req_json = {
            'bucket_name': self._bucket_name,
            'prefix': path
        }
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path='/bucket/object/prefix',
            params=req_json,
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def head_object(self, key, version_id = None, throw_err = None) -> bool:
        """
        Check whether an object exists in the bucket and whether the user has access to it.

        Args:
            key (str): Name of the object to check.
            version_id (str, optional): Version ID of the object, for checking specific versions.
            throw_err (bool, optional):
                - If True, raises an error if the object is not found.
                - If False, returns False if the object is not found. Defaults to False.

        Raises:
            CatalystStratusError: If the key is empty.
            CatalystAPIError: If the object is not found and `throw_err` is True.

        Access: admin, user

        Returns:
            bool: True if the object exists, False otherwise.

        Example:
            ```python
            # Check if the object exists
            object_exists = bucket.head_object(key='file.txt')
            print("Object Exists:", object_exists)
            ```
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        try:
            if (self._auth_util.get_user_type() == 'admin' or \
                self._auth_util.get_user_scope() == 'admin'):
                param = {
                    'bucket_name': self._bucket_name,
                    'object_key': key,
                    'version_id': version_id
                }
                resp = self._requester.request(
                    method=RequestMethod.HEAD,
                    path='/bucket/object',
                    params = param,
                    catalyst_service=CatalystService.SERVERLESS,
                    user=CredentialUser.ADMIN
                )
                return resp.status_code == 200
            param = { 'versionId': version_id }
            resp = self._requester.request(
                    method=RequestMethod.HEAD,
                    url=self.bucket_domain + f'/{urllib.parse.quote(key)}',
                    params=param,
                    external=True,
                    catalyst_service=CatalystService.STRATUS,
                    user=CredentialUser.USER,
                    token_only=True
            )
            return resp.status_code == 200
        except CatalystAPIError as err:
            if not throw_err:
                if err.http_status_code in (404, 403, 400):
                    return False
            raise err

    def copy_object(self, source_key, dest_key) -> CopyObjectResponse:
        """
        Copy an object from a source key to a destination key in the bucket.

        Args:
            source_key (str): The object to copy from.
            dest_key (str): The object to copy to.

        Raises:
            CatalystStratusError: If either the source or destination key is empty.

        Access: admin

        Returns:
            CopyObjectResponse: Details of the copy operation.

        Example:
            ```python
            # Copy an object
            response = bucket.copy_object(
                source_key='source/file.txt',
                dest_key='dest/file_copy.txt'
            )
            print("Copy Object Response:", response)
            ```
        """
        req_json = {
            'bucket_name': self._bucket_name,
            'object_key': source_key,
            'destination': dest_key
        }
        validator.is_non_empty_string(source_key, 'source_key', CatalystStratusError)
        validator.is_non_empty_string(dest_key, 'dest_key', CatalystStratusError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/bucket/object/copy',
            params=req_json,
            user=CredentialUser.ADMIN
        )
        data = self._serialize_res(resp.response_json.get('data'))
        return data

    def rename_object(self, source_key, dest_key) -> RenameObjectResponse:
        """
        Rename an object in the bucket.

        Args:
            source_key (str): The current name of the object.
            dest_key (str): The new name for the object.

        Access: admin

        Returns:
            RenameObjectResponse: Details of the renamed object.

        Example:
            ```python
            # Rename an object
            response = bucket.rename_object(
                source_key='old_name.txt',
                dest_key='new_name.txt'
            )
            print("Rename Object Response:", response)
            ```
        """
        validator.is_non_empty_string(source_key, 'source_key', CatalystStratusError)
        validator.is_non_empty_string(dest_key, 'dest_key', CatalystStratusError)
        req_json = {
            'bucket_name': self._bucket_name,
            'current_key':source_key,
            'rename_to': dest_key
        }
        resp = self._requester.request(
            method=RequestMethod.PATCH,
            path='/bucket/object',
            params=req_json,
            user=CredentialUser.ADMIN
        )
        data = resp.response_json.get('data')
        return data

    def initiate_multipart_upload(
        self,
        key: str,
        options: StratusInitiateUploadOptions = None,
    ) -> InitiateMultipartUploadResponse:
        """
        Initiate a multipart upload for large files.

        Args:
            key (str): The name of the object to upload.
            compress (str, optional): Whether to compress the file during upload.
                Defaults to 'false'.
            options (StratusInitiateUploadOptions, optional): Optional configuration options
                for the multipart upload, such as overwrite and compress settings.

        Access: admin, user

        Returns:
            InitiateMultipartUploadResponse: Details about the initiated multipart upload.
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        content_type, _other = mimetypes.guess_type(key)
        sign = self._auth_util.get_bucket_signature()
        url = self.bucket_domain + ('/_signed' if sign else '')
        auth = not bool(sign)
        compress_val = overwrite_val = 'false'
        if isinstance(options, dict):
            compress_val = options.get('compress', 'false')
            overwrite_val = options.get('overwrite', 'false')
        resp = self._requester.request(
            method=RequestMethod.PUT,
            url=url +f'/{urllib.parse.quote(key)}?multipart',
            headers={
                'compress': compress_val,
                'Content-Type': content_type if content_type else 'application/octet-stream',
                'overwrite': overwrite_val
            },
            params=sign,
            catalyst_service=CatalystService.STRATUS,
            auth= auth,
            external=True,
            user=CredentialUser.USER,
            token_only= True,
        )
        return resp.response_json

    def upload_part(self,
        key: str,
        upload_id: str,
        body: Union[BufferedReader, bytes],
        part_number: Union[str, int],
        overwrite: Union[str, bool] = False
    ) -> bool:
        """
        Upload the individual parts of the file, with a distinct part number.

        Args:
            key (str): Name of the object.
            upload_id (str): Unique identifier for the multipart upload.
            body (Union[BufferedReader, bytes]): Body of the object.
            part_number (Union[str, int]): A unique number for the part to be uploaded.
                This determines the position of the part when reassembling the multipart object.
            overwrite (Union[str, bool], optional): Whether to overwrite existing parts.
                Defaults to 'false'.

        Access: admin, user

        Returns:
            bool: 'True' if the upload part operation was completed successfully.
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_non_empty_string(upload_id, 'upload_id', CatalystStratusError)
        if not validator.is_buffered_reader(body) and not isinstance(body, bytes):
            raise CatalystStratusError(
                'Invalid-Argument',
                'Object part must be an instance of BufferedReader.', type(body)
            )
        sign = self._auth_util.get_bucket_signature() or {}
        url = self.bucket_domain + ('/_signed' if sign else '')
        params = {
            'uploadId': upload_id,
            'partNumber': part_number,
            **sign
        }
        resp = self._requester.request(
            method=RequestMethod.PUT,
            url= url +f'/{urllib.parse.quote(key)}',
            headers = {
                'overwrite': str(overwrite),
            },
            data=body,
            params=params,
            stream=True,
            catalyst_service=CatalystService.STRATUS,
            auth=not bool(sign),
            external=True,
            user=CredentialUser.USER,
            token_only= True
        )
        return resp.status_code == 200

    def complete_multipart_upload(self, key: str, upload_id: str, overwrite: bool = False) -> bool:
        """
        Complete the multipart upload by assembling the uploaded parts.

        Args:
            key (str): Name of the object.
            upload_id (str): Unique identifier for the multipart upload.
            overwrite (bool, optional): Whether to overwrite the existing object. Defaults to False.

        Access: admin, user

        Returns:
            bool: 'True' if the multipart upload was completed successfully.
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_non_empty_string(upload_id, 'upload_id', CatalystStratusError)
        sign = self._auth_util.get_bucket_signature() or {}
        url = self.bucket_domain + ('/_signed' if sign else '')
        resp = self._requester.request(
            method=RequestMethod.PUT,
            url= url +f'/{urllib.parse.quote(key)}?completeMultipart',
            params={
                'uploadId': upload_id,
                **sign
            },
            headers={
                'overwrite': str(overwrite)
            },
            catalyst_service=CatalystService.STRATUS,
            auth=not bool(sign),
            external = True,
            user=CredentialUser.USER,
            token_only= True
        )
        data = resp.status_code
        return data == 202

    def get_multipart_upload_summary(
        self,
        key: str,
        upload_id: str
    ) -> MultipartUploadSummaryRes:
        """
        Get a summary of the uploaded parts for a multipart upload.

        Args:
            key (str): Name of the object.
            upload_id (str): Unique identifier for the multipart upload.
            overwrite (bool, optional): Whether to overwrite an existing object with the same key
                when completing the multipart upload. Defaults to False.

        Access: admin, user

        Returns:
            MultipartUploadSummaryRes: Details of the multipart upload object,
                including part information.
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_non_empty_string(upload_id, 'upload_id', CatalystStratusError)
        sign = self._auth_util.get_bucket_signature() or {}
        url = self.bucket_domain + ('/_signed' if sign else '')
        resp = self._requester.request(
            method=RequestMethod.GET,
            url=url +f'/{urllib.parse.quote(key)}?multipartSummary',
            params={
                **sign,
                'uploadId': upload_id
            },
            catalyst_service=CatalystService.STRATUS,
            auth = not bool(sign),
            external = True,
            user=CredentialUser.USER,
            token_only= True
        )
        return resp.response_json


    def object(self, key) -> StratusObject:
        """Get the object instance.

        Args:
            key (str): Name of the object.

        Access: admin, user

        Returns:
            StratusObject: object instance.
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        return StratusObject(self, {'key': key })

    def _validate_object_body(self, object_body):
        if not isinstance(object_body, (BufferedReader, bytes, memoryview, bytearray)) \
            and not validator.is_non_empty_string(object_body):
            raise CatalystStratusError(
                'invalid_object_body',
                'Object must be an instance of BufferReader or string and cannot be empty'
            )

    def _serialize_res(self, obj) -> Dict[str, str]:
        if 'object_key' in obj:
            obj['key'] = obj['object_key']
            del obj['object_key']
        return obj

    def to_dict(self):
        return self.bucket_details

    def to_string(self):
        return repr(self)
