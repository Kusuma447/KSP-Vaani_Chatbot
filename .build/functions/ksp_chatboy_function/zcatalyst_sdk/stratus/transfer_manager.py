from io import BufferedReader
import asyncio
from typing import Union

from requests import RequestException

from . import validator
from ..stratus.bucket import Bucket
from ..logger import get_logger
from ..types.stratus import MultipartUploadSummaryRes, PutObjectAsPartsOptions
from ..exceptions import CatalystStratusError
from ..types import Component
from .._http_client import AuthorizedHttpClient
from .._constants import Components

logger = get_logger()

class MultipartUpload():
    def __init__(self, bucket_instance, key, upload_id):
        self._requester: AuthorizedHttpClient = bucket_instance._requester
        self.bucket: Bucket = bucket_instance
        self.key = key
        self.upload_id = upload_id

    def upload_part(self,
            body: Union[BufferedReader, bytes],
            part_number: Union[str, int],
            overwrite: Union[str, bool] = False
    ) -> bool:
        """Upload the individual parts of the file, with a distinct part number.

        Args:
            body (Union[BufferedReader, bytes]): Body of the object.
            part_number (Union[str, int]): Number to ordering the object parts.
            overwrite (Union[str, bool], optional): Whether to overwrite existing parts.
                Defaults to 'false'.

        Access: admin

        Returns:
            bool:'True' if upload part operation is completed successfully.
        """
        resp = self.bucket.upload_part(self.key, self.upload_id, body, part_number, overwrite)
        return resp

    def complete_upload(self, overwrite: bool) -> bool:
        """Completes the multipart upload.

        Args:
            overwrite (bool): Whether to overwrite an existing object with the same key.

        Returns:
            bool: 'True' if the multipart upload is completed successfully.
        """
        resp = self.bucket.complete_multipart_upload(self.key, self.upload_id, overwrite)
        return resp

    def get_upload_summary(self) -> MultipartUploadSummaryRes:
        """Get a summary of the uploaded parts.

        Access: admin

        Returns:
           MultipartUploadSummaryRes: Details of the multipart upload.
        """
        resp = self.bucket.get_multipart_upload_summary(self.key, self.upload_id)
        return resp


class TransferManager(Component):
    def __init__(self, bucket_instance):
        self._requester: AuthorizedHttpClient = bucket_instance._requester
        self.bucket: Bucket = bucket_instance
        self.bucket_domain = bucket_instance.bucket_domain

    def get_component_name(self):
        return Components.STRATUS

    def create_multipart_instance(self,
        key: str,
        upload_id: str = None,
        overwrite: bool = False
    ) -> MultipartUpload:
        """Initializing the multipart upload to create the multipart instance.

        Args:
            key (str): Name of the object.
            upload_id(str, optional): Upload Id if the the upload is already initiated.

        Access: admin, user

        Returns:
            MultipartUpload: MultipartUpload Instance.
        """
        if not upload_id:
            initiate_upload = self.bucket.initiate_multipart_upload(key,{ 'overwrite': overwrite })
            upload_id = initiate_upload['upload_id']
        return MultipartUpload(self.bucket, key, upload_id)

    def _get_object_part(
        self,
        key: str,
        start: int,
        end: int,
        version_id: str = None,
        retry = 3
    ):
        """Get part of the object in the bucket.

        Args:
            key (str): Name of the object.
            start (int): starting byte or the lower bound of the byte range.
            end (int): ending byte or the upper bound of the byte range.
            version_id (str, optional): A unique identifier for the specific version of the object.
            retry (int, optional): Retry the request when failed. Defaults to 3.

        Access: admin, user

        Raises:
            CatalystStratusError: Raised if the key, start, or end values are empty.

        Returns:
            stream: part of the object as stream.
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_parsable_number(start, 'start_value', CatalystStratusError)
        validator.is_parsable_number(end, 'end_value', CatalystStratusError)
        try:
            data = self.bucket.get_object(
                key, { 'version_id': version_id, 'range':f'{start}-{end}'})
        except RequestException as err:
            if retry < 0:
                raise CatalystStratusError(
                    'STRATUS ERROR',
                    'Error while downloading the object',
                    key
                    ) from err
            retry-=1
            self._get_object_part(key, start, end, version_id, retry)
        return data

    def get_iterable_object(self, key: str, part_size: int, version_id: str = None):
        """Get an object as iterable multipart streams.

        Args:
            key (str): Name of the object.
            part_size (str): Size of the individual object part.
            version_id (str, optional): A unique identifier for the specific version of the object.

        Access: admin

        Yields:
            stream: Part of the object as stream.
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_parsable_number(part_size, 'part_size', CatalystStratusError)
        part_size = part_size * (1024 * 1024)
        file_size = self.bucket.object(key).get_details(version_id)['size']
        start=0
        while start < file_size:
            end_range = min(start + part_size, file_size) - 1
            res = self._get_object_part(key, start, end_range, version_id)
            yield res
            start = end_range + 1

    async def _upload_part(
        self,
        part_ins: MultipartUpload,
        chunk: BufferedReader,
        part_number: int
    ):
        res = part_ins.upload_part(chunk, str(part_number) + '')
        if res:
            logger.info(f'Part {str(part_number)} Uploaded')
        else:
            raise CatalystStratusError('STRATUS ERROR',
                f'Error while uploading the object {part_ins.key}')
        return res

    def generate_part_downloaders(self, key: str, part_size: int, version_id = None):
        """Get the object as a list of downloadable parts.

        Args:
            key (str): Name of the object.
            part_size (int): Size of the individual object part.
            version_id (str, optional): A unique identifier for the specific version of the object.

        Access: admin

        Returns:
            List[Function]: List of downloadable object parts.
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_parsable_number(part_size, 'part_size', CatalystStratusError)
        part_size = part_size * (1024 * 1024)
        file_size = self.bucket.object(key).get_details(version_id)['size']
        parts = []
        start = 0
        while start < file_size:
            end_range = min(start + part_size, file_size) - 1
            parts.append(
                lambda start=start,
                        end_range=end_range,
                        key=key,
                        version_id=version_id:
                self._get_object_part(key, start, end_range, version_id)
            )
            start = end_range + 1
        return parts

    def put_object_as_parts(
        self,
        key: str,
        body: BufferedReader,
        part_size: int,
        options: PutObjectAsPartsOptions = None
    ) -> MultipartUploadSummaryRes:
        """Upload the object as multiple parts and combine these parts into single object.

        Args:
            key (str): Name of the object.
            file (BufferedReader): Body of the object.
            part_size (int): Size of the individual object part.
            options (PutObjectAsPartsOptions, optional): Optional configuration options
                for the multipart upload, such as overwrite settings. Defaults to None.

        Access: admin, user

        Returns:
            MultipartUploadSummaryRes: Details of the multipart upload.
        """
        validator.is_non_empty_string(key, 'key', CatalystStratusError)
        validator.is_parsable_number(part_size, 'part_size', CatalystStratusError)
        return asyncio.run(self._put_object(key, body, part_size, options))

    async def _put_object(self,
        key: str,
        file: BufferedReader,
        part_size: int,
        options: PutObjectAsPartsOptions
    ):
        part_size = part_size * (1024 * 1024)
        overwrite = options.get('overwrite', None) if options else None
        initiate_res = self.create_multipart_instance(key, None, overwrite)
        logger.info('Multipart upload started')
        part_number = 1
        tasks = []
        try:
            while True:
                chunk = file.read(part_size)
                if not chunk:
                    break
                tasks.append(self._upload_part(initiate_res, chunk, part_number))
                part_number += 1
                if part_number > 1000:
                    raise CatalystStratusError(
                        'invalid-partsize',
                        'Part number exceeded the limit 1000. Please increase the part size.',
                        key
                    )
        except Exception as err:
            raise CatalystStratusError('STRATUS_ERROR', str(err), key) from None

        uploaded_parts = await asyncio.gather(*tasks)

        if uploaded_parts:
            complete_res = initiate_res.complete_upload(overwrite)
            if complete_res:
                logger.info('Upload Completed')
            else:
                raise CatalystStratusError(
                    'STRATUS_ERROR',
                    'Error while completing multipart upload',
                    key
                ) from None

        return initiate_res.get_upload_summary()
